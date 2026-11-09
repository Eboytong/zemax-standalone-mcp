"""Typed native text reports: real-sample regression, error layering and strict requests.

The two sample files under ``tests/support/native_samples`` are byte-for-byte copies of
real OpticStudio 24.2.0 native report exports (UTF-16 LE with BOM), taken from the main
project evidence folders:

* ``prescription_data_20261108_native.txt`` - task ``68ace1bed8d14c1cb569d97dbc5bfb09``
* ``surface_data_20261108_native.txt``      - task ``80c79fad920a4e9e9f337b10a6b9aa9f``
* ``surface_data_20261107_native.txt``      - task ``48596bf64aa34056a25e744999a48f20``

No native session is created here: the parsers are exercised against those samples and
against synthetic text for the cases the samples do not cover (English titles, empty,
truncated, undecodable).
"""
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from zemax_mcp.analysis_models import AnalysisRequest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.native_text_reports import (
    DOCUMENTED_PRESCRIPTION_SECTIONS,
    REPORT_ANALYSES,
    PrescriptionDataReport,
    SurfaceDataReport,
    decode_native_text,
    parse_prescription_report,
    parse_report,
    parse_surface_data_report,
    report_payload,
)

SAMPLES = Path(__file__).resolve().parents[1] / 'support' / 'native_samples'
PRESCRIPTION = SAMPLES / 'prescription_data_20261108_native.txt'
SURFACE_20261108 = SAMPLES / 'surface_data_20261108_native.txt'
SURFACE_20261107 = SAMPLES / 'surface_data_20261107_native.txt'


def sample_text(path):
    return decode_native_text(path.read_bytes())


# --- real-sample regression -------------------------------------------------

def test_prescription_sample_sections():
    report = parse_prescription_report(sample_text(PRESCRIPTION))
    assert report['kind'] == 'prescription_data'
    assert report['report_title'] == '系统/详细数据'
    assert report['section_count'] == 14
    assert report['section_ids'] == [
        'general_data', 'surface_data', 'surface_detail', 'edge_thickness', 'solves_variables',
        'index_data', 'thermal_expansion_data', 'global_vertex', 'center_of_curvature',
        'element_volume', 'f_numbers', 'cardinal_points', 'pop_settings', 'files_used']
    # A single-configuration report legitimately omits the multi-configuration section.
    assert report['missing_documented_sections'] == ['multi_config_data']
    assert report['duplicate_sections'] == []
    assert set(report['section_ids']) <= set(DOCUMENTED_PRESCRIPTION_SECTIONS)


def test_prescription_sample_document_and_lines():
    text = sample_text(PRESCRIPTION)
    report = parse_prescription_report(text)
    assert report['line_count'] == 217
    assert len(report['lines']) == 217
    assert report['lines'][0]['text'].strip() == '系统/详细数据'
    assert report['document']['日期'] == '2026/11/8'
    assert report['document']['文件'].endswith('working_80aa97b0.zos')
    assert report['raw_text_retained'] is True
    # Section bodies carry their own original lines and line ranges.
    general = report['sections'][0]
    assert general['section_id'] == 'general_data'
    assert general['start_line'] == 8 and general['end_line'] > general['start_line']
    assert any('有效焦距' in line for line in general['lines'])


def test_prescription_unknown_title_is_preserved_not_dropped():
    report = parse_prescription_report(sample_text(PRESCRIPTION))
    titles = [candidate['title'] for candidate in report['candidate_titles']]
    assert '预测坐标 ABCD 矩阵' in titles
    # The candidate is still present verbatim in the retained lines.
    assert any('预测坐标 ABCD 矩阵' in row['text'] for row in report['lines'])


@pytest.mark.parametrize('path', [SURFACE_20261108, SURFACE_20261107])
def test_surface_sample_identity_units_and_fields(path):
    report = parse_surface_data_report(sample_text(path))
    assert report['kind'] == 'surface_data'
    assert report['surface'] == 1
    assert report['surface_source'] == 'report title'
    assert report['unit'] == '毫米'
    assert report['glass'] == ''
    assert report['fields']['厚度']['value_text'] == '0'
    assert report['fields']['直径']['value_text'] == '0'
    assert report['fields']['Y 边缘厚度']['value_text'] == '0'
    assert report['fields']['X 边缘厚度']['value_text'] == '0'
    assert report['index_rows'] == [dict(number=1, wavelength_um=0.55, index=1.0,
                                         wavelength_text='0.55000', index_text='1.0000000000')]
    assert report['surface_power']['power_in_situ']['surface'] == 1
    assert report['surface_power']['power_in_air']['surface'] == 1
    assert report['surface_power']['power_in_air']['value'] == 0.0
    assert report['identity_check'] == dict(
        title_surface=1, power_surfaces=[1, 1], consistent=True,
        basis='title surface number versus the surface numbers of the power blocks')
    assert [section['section_id'] for section in report['sections']] == [
        'edge_thickness', 'index', 'power_in_situ', 'power_in_air']


def test_surface_sample_units_and_numbers_are_not_reinterpreted():
    report = parse_surface_data_report(sample_text(SURFACE_20261108))
    # Original display precision is kept verbatim next to the parsed value.
    row = report['index_rows'][0]
    assert row['wavelength_text'] == '0.55000' and row['index_text'] == '1.0000000000'
    assert report['fields']['厚度']['value_text'] == '0'
    assert report['unit'] == '毫米'


# --- decoding ---------------------------------------------------------------

def test_decode_utf16_bom_and_utf8():
    assert decode_native_text('表面 1 数据概要'.encode('utf-16')) == '表面 1 数据概要'
    assert decode_native_text('表面 1 数据概要'.encode('utf-8')) == '表面 1 数据概要'
    assert decode_native_text('abc'.encode('utf-16-le')) == 'abc'


def test_decode_empty_is_no_result_data():
    with pytest.raises(ZemaxError) as info:
        decode_native_text(b'')
    assert info.value.code == 'NO_RESULT_DATA'


def test_decode_undecodable_keeps_byte_prefix():
    with pytest.raises(ZemaxError) as info:
        decode_native_text(b'\xff\xfe' + b'\x00\xd8' * 4)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['native_prefix']


# --- failure layering -------------------------------------------------------

@pytest.mark.parametrize('text', ['', '   \n\n \n'])
def test_empty_report_is_no_result_data(text):
    with pytest.raises(ZemaxError) as info:
        parse_prescription_report(text)
    assert info.value.code == 'NO_RESULT_DATA'
    with pytest.raises(ZemaxError) as info:
        parse_surface_data_report(text)
    assert info.value.code == 'NO_RESULT_DATA'


def test_prescription_without_sections_is_invalid_and_keeps_text():
    text = '系统/详细数据\n文件 : C:\\x.zos\n\n完全无法识别的正文\n'
    with pytest.raises(ZemaxError) as info:
        parse_prescription_report(text)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['native_lines'] == 4
    assert any('完全无法识别' in line for line in info.value.details['native_preamble'])


def test_surface_without_title_is_invalid_and_keeps_text():
    text = '边缘厚度:\nY 边缘厚度: 0\n'
    with pytest.raises(ZemaxError) as info:
        parse_surface_data_report(text)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert any('边缘厚度' in line for line in info.value.details['native_preamble'])


def test_truncated_prescription_keeps_partial_sections():
    """A truncated export still parses the sections it contains; nothing is invented."""
    text = '系统/详细数据\n\n常用透镜数据:\n面                      : \t               2\n折射率数据:\n'
    report = parse_prescription_report(text)
    assert report['section_ids'] == ['general_data', 'index_data']
    assert report['section_count'] == 2
    assert report['missing_documented_sections']
    assert report['line_count'] == 5


def test_invalid_number_in_surface_report_is_rejected():
    text = '表面 1 数据概要\n\n表面光焦 (在空气中):\n面   1    :   不是数字\n'
    with pytest.raises(ZemaxError) as info:
        parse_surface_data_report(text)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['field'] == 'power_in_air'


# --- documented English titles ---------------------------------------------

def test_english_documented_titles_are_recognised():
    text = ('System/Detail Data\nFile : C:\\x.zos\n\n'
            'General Data:\nF/# : 10\n\n'
            'Surface Data:\n  Surface\tType\n\n'
            'Index Data:\n 1 \t 0.55000 \t 1.0\n\n'
            'Files Used:\n  C:\\x.zos\n')
    report = parse_prescription_report(text)
    assert report['section_ids'] == ['general_data', 'surface_data', 'index_data', 'files_used']
    assert report['missing_documented_sections'] == [
        'surface_detail', 'edge_thickness', 'multi_config_data', 'solves_variables',
        'thermal_expansion_data', 'global_vertex', 'center_of_curvature', 'element_volume',
        'f_numbers', 'cardinal_points', 'pop_settings']


def test_english_surface_titles_are_recognised():
    text = ('Surface 2 Data Summary\n\nLens units: millimeters\n\n'
            'Edge Thickness:\nY Edge Thickness: 1.5\n\n'
            'Index of Refraction:\nGlass: N-BK7\n\n'
            'Surface Power (in air):\nSurface 2 : 0.25\n')
    report = parse_surface_data_report(text)
    assert report['surface'] == 2
    assert report['unit'] == 'millimeters'
    assert report['glass'] == 'N-BK7'
    assert report['fields']['Y Edge Thickness']['value_text'] == '1.5'
    assert report['surface_power']['power_in_air']['surface'] == 2
    assert report['identity_check']['consistent'] is True


# --- request contract ------------------------------------------------------

def test_kind_only_requests_are_accepted():
    adapter = TypeAdapter(AnalysisRequest)
    prescription = adapter.validate_python({'kind': 'prescription_data'})
    surface = adapter.validate_python({'kind': 'surface_data'})
    assert isinstance(prescription, PrescriptionDataReport) and prescription.model_dump() == {'kind': 'prescription_data', 'sections': None}
    assert isinstance(surface, SurfaceDataReport) and surface.model_dump() == {'kind': 'surface_data'}


@pytest.mark.parametrize('payload', [
    {'kind': 'prescription_data', 'section': 'index_data'},
    {'kind': 'prescription_data', 'sections': ['unknown']},
    {'kind': 'surface_data', 'surface': 2},
    {'kind': 'surface_data', 'section': 'index'},
])
def test_unknown_selection_fields_are_rejected(payload):
    """No fake selector field is offered while the official selection is unknown."""
    with pytest.raises(ValidationError):
        TypeAdapter(AnalysisRequest).validate_python(payload)


def test_report_analysis_names_are_the_native_enums():
    assert REPORT_ANALYSES == {'prescription_data': 'PrescriptionDataSettings',
                               'surface_data': 'SurfaceDataSettings'}


def test_missing_native_text_is_no_result_data():
    with pytest.raises(ZemaxError) as info:
        report_payload({'artifacts': [], 'native_messages': []}, 'surface_data')
    assert info.value.code == 'NO_RESULT_DATA'


def test_parse_report_dispatches_by_kind():
    assert parse_report('surface_data', sample_text(SURFACE_20261108))['surface'] == 1
    assert parse_report('prescription_data', sample_text(PRESCRIPTION))['section_count'] == 14
    with pytest.raises(ZemaxError) as info:
        parse_report('nope', 'x')
    assert info.value.code == 'INVALID_ARGUMENT'


# --- report identity --------------------------------------------------------

def test_prescription_rejects_another_report_with_familiar_sections():
    """Familiar section names alone do not make a prescription report."""
    text = '系统数据\n\n面数据概要:\n 表面\t类型\n\n折射率数据:\n 1 \t 0.55 \t 1.0\n'
    with pytest.raises(ZemaxError) as info:
        parse_prescription_report(text)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['report_title'] == '系统数据'
    assert '系统/详细数据' in info.value.details['expected_titles']
    assert any('面数据概要' in line for line in info.value.details['native_preamble'])


@pytest.mark.parametrize('title', ['系统/详细数据', 'System/Detail Data', 'Prescription Data'])
def test_prescription_accepts_documented_titles(title):
    report = parse_prescription_report(f'{title}\n\n常用透镜数据:\n面 : 2\n')
    assert report['report_title'] == title
    assert report['section_ids'] == ['general_data']


def test_surface_identity_conflict_is_rejected_with_partial_result():
    text = ('表面 1 数据概要\n\n透镜单位:             毫米\n\n'
            '表面光焦 (在空气中):\n面   2    :              0\n')
    with pytest.raises(ZemaxError) as info:
        parse_surface_data_report(text)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['title_surface'] == 1
    assert info.value.details['power_surfaces'] == [2]
    partial = info.value.details['partial']
    assert partial['surface'] == 1 and partial['unit'] == '毫米'
    assert partial['surface_power']['power_in_air']['surface'] == 2
    assert any('表面 1 数据概要' in row['text'] for row in partial['lines'])


@pytest.mark.parametrize('surface,expected', [(1, .028283), (2, .0014288)])
def test_surface_element_report_preserves_both_faces(surface, expected):
    report = parse_surface_data_report(
        f'Surface {surface} Data Summary\nLens Units: mm\n'
        'Surface Power (in situ):\nSurface 1: 0.028283\nSurface 2: 0.0014288\n'
        'EFL 1 2: 33.749\n'
        'Surface Power (in air):\nSurface 1: 0.028283\nSurface 2: 0.0014288\n')
    assert report['surface_power']['power_in_situ']['surface'] == surface
    assert report['surface_power']['power_in_situ']['value'] == expected
    for rows in report['surface_power_components'].values():
        assert [row['surface'] for row in rows] == [1, 2]
    assert report['identity_check']['consistent'] is True


def test_surface_identity_agreement_is_accepted():
    text = '表面 3 数据概要\n\n透镜单位: 毫米\n\n表面光焦 (在空气中):\n面   3    :  0.5\n'
    report = parse_surface_data_report(text)
    assert report['surface'] == 3
    assert report['identity_check']['consistent'] is True


# --- collector layering -----------------------------------------------------

def test_collector_empty_text_keeps_native_messages(tmp_path):
    path = tmp_path / 'empty.txt'
    path.write_bytes(''.encode('utf-16'))
    result = dict(artifacts=[dict(kind='native_text', path=str(path))], native_messages=['original'])
    with pytest.raises(ZemaxError) as info:
        report_payload(result, 'surface_data')
    assert info.value.code == 'NO_RESULT_DATA'
    assert info.value.details['native_messages'] == ['original']
    assert info.value.details['native_text'] == str(path)
    assert info.value.details['analysis_kind'] == 'surface_data'


def test_collector_decode_failure_keeps_native_text(tmp_path):
    path = tmp_path / 'bad.txt'
    path.write_bytes(b'\xff\xfe' + b'\x00\xd8' * 6)
    result = dict(artifacts=[dict(kind='native_text', path=str(path))], native_messages=['m'])
    with pytest.raises(ZemaxError) as info:
        report_payload(result, 'prescription_data')
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['native_text'] == str(path)
    assert info.value.details['native_messages'] == ['m']


def test_collector_identity_mismatch_keeps_native_text(tmp_path):
    path = tmp_path / 'other.txt'
    path.write_text('系统数据\n\n面数据概要:\n', encoding='utf-16')
    result = dict(artifacts=[dict(kind='native_text', path=str(path))], native_messages=[])
    with pytest.raises(ZemaxError) as info:
        report_payload(result, 'prescription_data')
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['native_text'] == str(path)
    assert info.value.details['report_title'] == '系统数据'


def test_collector_read_failure_carries_full_context(tmp_path):
    missing = tmp_path / 'gone.txt'
    result = dict(artifacts=[dict(kind='native_text', path=str(missing))], native_messages=['m'])
    with pytest.raises(ZemaxError) as info:
        report_payload(result, 'surface_data')
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['native_text'] == str(missing)
    assert info.value.details['analysis_kind'] == 'surface_data'
    assert info.value.details['native_messages'] == ['m']


def test_collector_success_separates_default_report_from_selection_scope(tmp_path):
    path = tmp_path / 'ok.txt'
    path.write_bytes(SURFACE_20261108.read_bytes())
    result = dict(artifacts=[dict(kind='native_text', path=str(path))], native_messages=[])
    payload = report_payload(result, 'surface_data')
    assert payload['surface'] == 1 and payload['unit'] == '毫米'
    assert payload['structured_data_available'] is True
    assert payload['acceptance_scope'] == 'default_report_only'
    assert payload['selection_scope']['status'] == 'blocked'
    assert payload['selection_scope']['supported'] == 'default_only'
    assert payload['selection_scope']['unlock_condition']


# --- run_text_report lifecycle ---------------------------------------------

def _report_backend(*, close_ok=True, tool=True):
    from types import SimpleNamespace as NS
    calls = dict(closed=[], started=[])
    tool_object = NS(GetSettings=lambda: object()) if tool else None

    def close(holder):
        calls['closed'].append(holder['native'])
        holder['cleanup_warnings'] = ['close failed']
        return close_ok

    def start(kind, native, settings, **kwargs):
        calls['started'].append(dict(kind=kind, native=native, settings=settings, **kwargs))
        return dict(kind=kind, task_id='t')

    backend = NS(_require_work=lambda: None, _close_task_native=close, _start_task=start)
    return backend, tool_object, calls


@pytest.mark.parametrize('close_ok', [True, False])
def test_settings_failure_closes_and_keeps_original_error(monkeypatch, close_ok):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    from zemax_mcp.native_text_reports import run_text_report
    backend, tool_object, calls = _report_backend(close_ok=close_ok)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool_object)

    def reject(*_):
        raise ZemaxError('SETTING_UNAVAILABLE', 'original')

    monkeypatch.setattr(analyses, 'scalar_settings', reject)
    with pytest.raises(ZemaxError) as info:
        run_text_report(backend, SurfaceDataReport(kind='surface_data'))
    assert info.value.code == 'SETTING_UNAVAILABLE' and str(info.value) == 'original'
    assert calls['closed'] == [tool_object]
    if not close_ok:
        assert info.value.details['cleanup_warnings'] == ['close failed']


def test_unavailable_factory_is_reported(monkeypatch):
    import zemax_mcp.imaging as imaging
    from zemax_mcp.native_text_reports import run_text_report
    backend, _, calls = _report_backend(tool=False)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: None)
    with pytest.raises(ZemaxError) as info:
        run_text_report(backend, PrescriptionDataReport(kind='prescription_data'))
    assert info.value.code == 'NATIVE_INTERFACE_UNAVAILABLE'
    assert info.value.details['analysis'] == 'PrescriptionDataSettings'
    assert calls['started'] == []


@pytest.mark.parametrize('kind,analysis', [('prescription_data', 'PrescriptionDataSettings'),
                                           ('surface_data', 'SurfaceDataSettings')])
def test_success_starts_analysis_task_with_default_only_selection(monkeypatch, kind, analysis):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    from zemax_mcp.native_text_reports import run_text_report
    backend, tool_object, calls = _report_backend()
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool_object)
    monkeypatch.setattr(analyses, 'scalar_settings', lambda *_: dict(IsValid=True))
    request = PrescriptionDataReport(kind='prescription_data') if kind == 'prescription_data' \
        else SurfaceDataReport(kind='surface_data')
    run_text_report(backend, request)
    started = calls['started'][0]
    assert started['kind'] == kind and started['native'] is tool_object
    assert started['analysis'] is True
    assert started['settings']['analysis'] == analysis
    assert started['settings']['selection_support'] == 'default_only'
    assert started['settings']['selection_note']
    assert started['settings']['settings_source'].startswith('AS_Default/base IAS_')
    assert callable(started['collector'])


def test_settings_unavailable_fields_raise(monkeypatch):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    from zemax_mcp.native_text_reports import run_text_report
    backend, tool_object, calls = _report_backend()
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool_object)
    monkeypatch.setattr(analyses, 'scalar_settings', lambda *_: dict(unavailable_fields=['IsValid']))
    with pytest.raises(ZemaxError) as info:
        run_text_report(backend, SurfaceDataReport(kind='surface_data'))
    assert info.value.code == 'SETTING_UNAVAILABLE'
    assert info.value.details['unavailable_fields'] == ['IsValid']
    assert calls['closed'] == [tool_object]
