from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.polarization_topics import PhaseAberration, parse_phase_aberration_text

HEADER = (
    '偏振相位像差数据\n\n'
    '文件 : C:\\work\\lens.zos\n'
    '题目: A SIMPLE COOKE TRIPLET.\n'
    '日期 : 2026/11/8\n\n\n'
    '波长  :  0.5500\n'
    '视场Pos : 0.00 (度)\n'
    'Jx          :\t 0.0000\n'
    'Jy          :\t 1.0000\n'
    'X-相位     :    0.00\n'
    'Y-相位     :    0.00\n\n'
)
COLUMNS = '                 弧矢                子午\n     P     X 相位      Y 相位     X 相位      Y 相位\n'


def rows(spec=None):
    """Native rows are five tab separated columns: P, sagittal X/Y, tangential X/Y."""
    spec = spec or [(-1.0, 0.0, -0.011767056, 0.0, -0.011626575),
                    (-0.5, 0.0, -0.002863256, 0.0, -0.002829614),
                    (0.0, 0.0, 0.0, 0.0, 0.0),
                    (0.5, 0.0, -0.002863256, 0.0, -0.002829614),
                    (1.0, 0.0, -0.011767056, 0.0, -0.011626575)]
    return ''.join('\t'.join(f'{value:.3f}' if index == 0 else f'{value:.9f}' for index, value in enumerate(row)) + '\n'
                   for row in spec)


def text(spec=None, columns=COLUMNS, header=HEADER):
    return header + columns + rows(spec)


def test_default_request_preserves_native_selection():
    request = RunAnalysis(request=dict(kind='phase_aberration')).request
    assert request.method == 'auto' and request.field is None and request.wavelength is None
    assert request.kind == 'phase_aberration'


@pytest.mark.parametrize('patch', [dict(field=0), dict(wavelength=True), dict(surface=1), dict(jx=1), dict(sampling=5)])
def test_request_rejects_selector_parameters(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='phase_aberration', **patch))


def test_parses_real_chinese_dual_section_header():
    data = parse_phase_aberration_text(text())
    assert data['input_header']['wavelength_um'] == 0.55
    assert data['input_header']['field_position']['y'] == 0.0
    assert data['input_header']['jones'] == dict(jx=0.0, jy=1.0, x_phase_deg=0.0, y_phase_deg=0.0)
    assert data['section_order'] == ['sagittal', 'tangential']
    assert len(data['rows']) == 5
    assert [row['pupil'] for row in data['rows']] == [-1.0, -0.5, 0.0, 0.5, 1.0]
    assert data['rows'][0]['sagittal']['y_phase'] == pytest.approx(-0.011767056, abs=1e-12)
    assert data['rows'][0]['tangential']['y_phase'] == pytest.approx(-0.011626575, abs=1e-12)
    assert data['rows'][2]['sagittal']['y_phase'] == 0.0
    assert 'two rays on either side' in data['phase_reference']


def test_chinese_section_header_order_is_mapped_explicitly():
    swapped = '                 子午                弧矢\n     P     X 相位      Y 相位     X 相位      Y 相位\n'
    data = parse_phase_aberration_text(text(spec=[(-1.0, 1.0, 2.0, 3.0, 4.0),
                                                  (0.0, 5.0, 6.0, 7.0, 8.0),
                                                  (1.0, 9.0, 10.0, 11.0, 12.0)], columns=swapped))
    assert data['section_order'] == ['tangential', 'sagittal']
    first = data['rows'][0]
    assert (first['tangential']['x_phase'], first['tangential']['y_phase']) == (1.0, 2.0)
    assert (first['sagittal']['x_phase'], first['sagittal']['y_phase']) == (3.0, 4.0)


def test_series_follow_existing_contract():
    data = parse_phase_aberration_text(text())
    assert [item['series'] for item in data['series']] == [0, 1, 2, 3]
    for item in data['series']:
        assert len(item['labels']) == 1
        assert item['x_unit'] == 'normalized pupil' and item['y_unit'] == 'waves'
        assert item['value_units'] == ['waves']
        assert len(item['x']) == len(item['y']) == 5
        assert all(len(row) == 1 for row in item['y'])
        assert item['invalid_count'] == 0
    # plotting.py indexes data['x'] against [row[i] for row in data['y']]
    for item in data['series']:
        for index, _label in enumerate(item['labels']):
            assert len([row[index] for row in item['y']]) == len(item['x'])


def test_series_render_to_an_image(tmp_path):
    from zemax_mcp.plotting import export_image
    data = parse_phase_aberration_text(text())
    path = tmp_path / 'phase.png'
    result = export_image({**data}, N(item=0, source='plot', width=320, height=240), path)
    assert path.is_file() and path.stat().st_size > 0
    assert result['plotting_settings']['data_kind'] == 'series'


def test_rows_page_through_the_shared_task_result_path():
    data = parse_phase_aberration_text(text())
    request = N(series=None, grid=None, start=1, count=2)
    page = Backend._page_task_result(None, data, request)
    assert [row['pupil'] for row in page['rows']] == [-0.5, 0.0]
    assert page['total'] == 5 and page['next_start'] == 3
    tail = Backend._page_task_result(None, data, N(series=None, grid=None, start=3, count=5))
    assert tail['next_start'] is None and len(tail['rows']) == 2


def test_unit_metadata_keeps_declared_and_unverified_state():
    data = parse_phase_aberration_text(text())
    assert data['phase_unit'] == 'waves'
    assert data['phase_unit_verified'] is False
    assert 'manual' in data['phase_unit_source']
    assert data['units']['field_position'] == 'degrees'
    assert data['input_header']['field_position']['unit_source'] == 'native report header parentheses'
    assert data['structured_data_available'] is True


def test_field_unit_falls_back_to_system_field_type():
    header = HEADER.replace('视场Pos : 0.00 (度)', '视场Pos : 0.00')
    data = parse_phase_aberration_text(text(header=header), dict(system_settings=dict(field_type='ObjectHeight')))
    assert data['units']['field_position'] == 'object height in system lens units'
    assert data['input_header']['field_position']['unit_source'].startswith('system field_type ObjectHeight')
    unknown = parse_phase_aberration_text(text(header=header))
    assert unknown['units']['field_position'] is None
    assert unknown['input_header']['field_position']['unit_source'].startswith('unknown')


def test_full_width_colon_header_is_accepted():
    header = HEADER.replace('波长  :  0.5500', '波长  ：  0.5500').replace('视场Pos : 0.00 (度)', '视场Pos：0.00 (度)')
    data = parse_phase_aberration_text(text(header=header))
    assert data['input_header']['wavelength_um'] == 0.55


@pytest.mark.parametrize('mutation,code', [
    (lambda body: body.replace('波长  :  0.5500\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.split('     P     X 相位')[0], 'INVALID_RESULT_DATA'),
    (lambda body: body.replace(COLUMNS, COLUMNS).replace('\t-0.002863256\t', '\t\t', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('-0.500\t', '0.500\t', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('1.000\t', '2.000\t', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('-0.011767056', 'nan', 1), 'INVALID_RESULT_DATA'),
])
def test_malformed_reports_raise_specific_codes(mutation, code):
    with pytest.raises(ZemaxError) as caught:
        parse_phase_aberration_text(mutation(text()))
    assert caught.value.code == code


def test_empty_table_reports_no_data():
    with pytest.raises(ZemaxError) as caught:
        parse_phase_aberration_text(HEADER + COLUMNS)
    assert caught.value.code == 'NO_RESULT_DATA'


def test_single_row_table_is_rejected_as_insufficient():
    with pytest.raises(ZemaxError) as caught:
        parse_phase_aberration_text(text(spec=[(0.0, 0.0, 0.0, 0.0, 0.0)]))
    assert caught.value.code == 'INVALID_RESULT_DATA'
    assert caught.value.details['point_count'] == 1
