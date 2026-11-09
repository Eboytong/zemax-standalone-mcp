"""Selection from native report lines, separate from native settings."""
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from zemax_mcp.analysis_models import AnalysisRequest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.native_text_reports import report_payload, DOCUMENTED_PRESCRIPTION_SECTIONS

SAMPLE = Path(__file__).parents[1] / 'support/native_samples/prescription_data_20261108_native.txt'


def payload(tmp_path, sections, text=None):
    path = tmp_path / 'native.txt'
    path.write_bytes(SAMPLE.read_bytes() if text is None else text.encode('utf-16'))
    return report_payload(dict(artifacts=[dict(kind='native_text', path=str(path))],
                               native_messages=['message']), 'prescription_data', sections)


@pytest.mark.parametrize('sections', [[], ['index_data', 'index_data'], ['unknown'], 'index_data', [1]])
def test_invalid_selection(sections):
    with pytest.raises(ValidationError):
        TypeAdapter(AnalysisRequest).validate_python(dict(kind='prescription_data', sections=sections))


def test_selected_sections_exact_lines_order_and_identity(tmp_path):
    result = payload(tmp_path, ['files_used', 'general_data', 'index_data'])
    assert result['selected_section_ids'] == ['general_data', 'index_data', 'files_used']
    assert result['selection']['requested'] == ['files_used', 'general_data', 'index_data']
    assert result['selection']['native_settings_modified'] is False
    assert result['selection_scope']['status'] == 'blocked'
    source = Path(result['native_text']).read_bytes().decode('utf-16').splitlines(keepends=True)
    expected = ''.join(source[row['line'] - 1] for row in result['rows'])
    with Path(result['selected_text']).open(encoding='utf-8', newline='') as stream:
        assert stream.read() == expected
    assert result['line_count'] == 217
    assert result['section_count'] == 14
    assert result['row_count'] == len(result['rows'])
    assert {row['section_id'] for row in result['rows']} == {None, 'general_data', 'index_data', 'files_used'}
    assert all(row['text'] == result['lines'][row['line'] - 1]['text'] for row in result['rows'])
    assert 'selected_text' in [artifact['kind'] for artifact in result['artifacts']]


def test_all_available_sections_reconstruct_full_report(tmp_path):
    sections = [section for section in DOCUMENTED_PRESCRIPTION_SECTIONS if section != 'multi_config_data']
    result = payload(tmp_path, sections)
    assert [row['text'] for row in result['rows']] == [row['text'] for row in result['lines']]


@pytest.mark.parametrize('name', DOCUMENTED_PRESCRIPTION_SECTIONS)
def test_each_documented_english_section(name, tmp_path):
    from zemax_mcp.native_text_reports import PRESCRIPTION_SECTIONS
    title = next(title for title, value in PRESCRIPTION_SECTIONS.items() if value == name and title.isascii())
    text = f'Prescription Data\r\nFile: C:\\test.zos\r\n\r\n{title}:\r\n  body\r\n'
    result = payload(tmp_path, [name], text)
    with Path(result['selected_text']).open(encoding='utf-8', newline='') as stream:
        assert stream.read() == text


def test_absent_selected_section_returns_original_report_context(tmp_path):
    with pytest.raises(ZemaxError) as info:
        payload(tmp_path, ['multi_config_data'])
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['missing_sections'] == ['multi_config_data']
    assert info.value.details['native_messages'] == ['message']
    assert Path(info.value.details['native_text']).is_file()
    assert not (tmp_path / 'native.selected.txt').exists()


def test_duplicate_section_is_ambiguous(tmp_path):
    with pytest.raises(ZemaxError) as info:
        payload(tmp_path, ['general_data'], 'Prescription Data\nGeneral Data:\na\nGeneral Data:\nb\n')
    assert info.value.details['ambiguous_sections'] == ['general_data']


def test_output_error_is_attributed_and_original_kept(tmp_path):
    (tmp_path / 'native.selected.txt').mkdir()
    with pytest.raises(ZemaxError) as info:
        payload(tmp_path, ['index_data'])
    assert info.value.code == 'EXPORT_FAILED'
    assert info.value.details['source'] == 'native_report_section_selection'
    assert Path(info.value.details['native_text']).is_file()


def test_default_report_is_unchanged(tmp_path):
    result = payload(tmp_path, None)
    assert result['acceptance_scope'] == 'default_report_only'
    assert 'rows' not in result and 'selected_text' not in result
