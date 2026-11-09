from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.polarization_topics import PolarizationTransmission, parse_polarization_transmission_text

HEADER = (
    '偏振透射数据\n\n'
    '文件 : C:\\work\\lens.zos\n'
    '题目: A SIMPLE COOKE TRIPLET.\n'
    '日期 : 2026/11/8\n\n\n'
    '场是非偏振的.\n\n'
    '网格尺寸 : 32 x 32\n\n'
    '考虑了孔径, 菲涅尔, 膜层, 渐晕和内部透射效应.\n\n'
)
FIELDS = (
    '视场 Pos : 0.00 (度)\n'
    '  透射 at    0.4800:     0.946229361\n'
    '  透射 at    0.5500:     0.960700280\n'
    '  透射 at    0.6500:     0.942203090\n'
    '  总透射       :     0.950556246\n\n'
    '视场 Pos : 14.00 (度)\n'
    '  透射 at    0.4800:     0.949431572\n'
    '  透射 at    0.5500:     0.959023982\n'
    '  透射 at    0.6500:     0.937032333\n'
    '  总透射       :     0.949305810\n\n'
)
CHIEF = (
    '\n主光线逐面透过率:\n\n'
    '视场 Pos : 0.00 (度)\n'
    '波长 1: 0.480 µm\n\n'
    '表面    总透过率     相对透过率\n'
    '   1 \t    0.991023 \t    0.991023\n'
    '   2 \t    0.980259 \t    0.989138\n'
    '   3 \t    0.980259 \t    1.000000\n\n'
    '视场 Pos : 0.00 (度)\n'
    '波长 2: 0.550 µm\n\n'
    '表面    总透过率     相对透过率\n'
    '   1 \t    0.993748 \t    0.993748\n'
    '   2 \t    0.986226 \t    0.992430\n'
    '   3 \t    0.986226 \t    1.000000\n'
)
WEIGHTS = dict(field_type='Angle', wavelengths=[dict(number=1, wavelength_um=0.48, weight=0.8),
                                                dict(number=2, wavelength_um=0.55, weight=1.0),
                                                dict(number=3, wavelength_um=0.65, weight=0.8)])


def text(fields=FIELDS, chief=CHIEF, header=HEADER):
    return header + fields + chief


def test_request_retains_native_default():
    assert PolarizationTransmission(kind='polarization_transmission').method=='auto'
    assert RunAnalysis(request=dict(kind='polarization_transmission')).request.kind == 'polarization_transmission'


@pytest.mark.parametrize('patch', [dict(sampling=31), dict(unpolarized=True), dict(field=-1), dict(wavelength=-1), dict(jx=1)])
def test_request_rejects_selector_parameters(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='polarization_transmission', **patch))


def test_parses_fields_totals_and_chief_ray_surfaces():
    data = parse_polarization_transmission_text(text(), dict(system_settings=WEIGHTS))
    assert data['input_header']['unpolarized'] is True
    assert data['input_header']['grid'] == dict(nx=32, ny=32)
    assert data['input_header']['effects'][:2] == ['孔径', '菲涅尔']
    assert [field['field_position_deg'] for field in data['fields']] == [0.0, 14.0]
    assert [item['transmission'] for item in data['fields'][0]['wavelengths']] == [0.946229361, 0.960700280, 0.942203090]
    assert data['fields'][0]['total_transmission'] == 0.950556246
    assert len(data['rows']) == 6
    assert data['rows'][0] == dict(index=0, field_position_deg=0.0, field_position_values=[0.0], field_unit='degrees',
                                   wavelength_um=0.48, transmission=0.946229361, field_total_transmission=0.950556246)
    assert len(data['chief_ray_surfaces']) == 2
    first = data['chief_ray_surfaces'][0]
    assert first['wavelength_um'] == 0.48 and first['wavelength_number'] == 1
    assert [row['surface'] for row in first['rows']] == [1, 2, 3]
    assert first['final_total'] == 0.980259 and first['surface_totals_non_increasing'] is True


POLARIZED_HEADER = HEADER.replace('场是非偏振的.',
    'X-场 : 1.0000\nY-场 : 0.0000\nX-相位 : 0.00\nY-相位 : 90.00')


def test_polarized_native_header_has_jones_fields_instead_of_unpolarized_sentence():
    data = parse_polarization_transmission_text(text(header=POLARIZED_HEADER))
    assert data['input_header']['unpolarized'] is False
    assert data['input_header']['jones'] == dict(jx=1., jy=0., x_phase_deg=0., y_phase_deg=90.)
    assert data['input_header']['polarization_line'] is None
    assert len(data['rows']) == 6


@pytest.mark.parametrize('header', [
    POLARIZED_HEADER.replace('Y-相位 : 90.00', ''),
    POLARIZED_HEADER.replace('X-场 : 1.0000', 'X-场 : 0.0000'),
    POLARIZED_HEADER.replace('X-场 : 1.0000', 'X-场 : -1.0000'),
    POLARIZED_HEADER.replace('X-场 : 1.0000', 'X-场 : NaN'),
    POLARIZED_HEADER.replace('X-场 : 1.0000', 'X-场 : 1.0000\nX-场 : 1.0000'),
])
def test_polarized_header_rejects_incomplete_or_invalid_jones(header):
    with pytest.raises(ZemaxError) as error:
        parse_polarization_transmission_text(text(header=header))
    assert error.value.code == 'INVALID_RESULT_DATA'


def test_weighted_mean_aggregation_matches_with_system_weights():
    data = parse_polarization_transmission_text(text(), dict(system_settings=WEIGHTS))
    for field in data['fields']:
        aggregation = field['aggregation']
        assert aggregation['status'] == 'match'
        assert abs(aggregation['residual']) <= 1e-8
        assert aggregation['weights'] == [0.8, 1.0, 0.8]
        assert 'offline check' in aggregation['source']


def test_aggregation_is_not_assumed_without_weights():
    data = parse_polarization_transmission_text(text())
    assert data['fields'][0]['aggregation']['status'] == 'not_evaluated'
    assert 'unavailable' in data['fields'][0]['aggregation']['reason']


def test_aggregation_mismatch_is_reported_not_raised():
    wrong = dict(WEIGHTS, wavelengths=[dict(number=1, wavelength_um=0.48, weight=1.0),
                                       dict(number=2, wavelength_um=0.55, weight=0.2),
                                       dict(number=3, wavelength_um=0.65, weight=0.2)])
    data = parse_polarization_transmission_text(text(), dict(system_settings=wrong))
    assert data['fields'][0]['aggregation']['status'] == 'mismatch'
    assert abs(data['fields'][0]['aggregation']['residual']) > 1e-8


def test_field_unit_comes_from_header_then_system_field_type():
    degrees = parse_polarization_transmission_text(text(), dict(system_settings=WEIGHTS))
    assert degrees['units']['field_position'] == 'degrees'
    assert degrees['input_header']['field_unit_source'] == 'native report header parentheses'
    bare = text(header=HEADER.replace('视场 Pos : 0.00 (度)', '视场 Pos : 0.00'),
                fields=FIELDS.replace('视场 Pos : 0.00 (度)', '视场 Pos : 0.00').replace('视场 Pos : 14.00 (度)', '视场 Pos : 14.00'),
                chief=CHIEF.replace('视场 Pos : 0.00 (度)', '视场 Pos : 0.00'))
    height = parse_polarization_transmission_text(bare, dict(system_settings=dict(field_type='ObjectHeight')))
    assert height['units']['field_position'] == 'object height in system lens units'
    assert height['rows'][0]['field_position_deg'] is None
    assert height['rows'][0]['field_position_values'] == [0.0]
    unknown = parse_polarization_transmission_text(bare)
    assert unknown['units']['field_position'] is None
    assert unknown['input_header']['field_unit_source'].startswith('unknown')


def test_two_dimensional_field_keeps_both_coordinates():
    fields = FIELDS.replace('视场 Pos : 14.00 (度)', '视场 Pos : 3.00, 14.00 (度)')
    data = parse_polarization_transmission_text(text(fields=fields), dict(system_settings=WEIGHTS))
    second = data['fields'][1]
    assert second['field_position'] == dict(x=3.0, y=14.0)
    assert second['field_position_deg'] is None
    assert second['field_position_values'] == [3.0, 14.0]


def test_rows_page_through_the_shared_task_result_path():
    data = parse_polarization_transmission_text(text(), dict(system_settings=WEIGHTS))
    page = Backend._page_task_result(None, data, N(series=None, grid=None, start=0, count=4))
    assert len(page['rows']) == 4 and page['total'] == 6 and page['next_start'] == 4
    tail = Backend._page_task_result(None, data, N(series=None, grid=None, start=4, count=10))
    assert tail['next_start'] is None and [row['index'] for row in tail['rows']] == [4, 5]


@pytest.mark.parametrize('mutation,code', [
    (lambda body: body.replace('场是非偏振的.\n\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('网格尺寸 : 32 x 32\n\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('  总透射       :     0.950556246\n', '', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('0.946229361', '1.200000000', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('0.946229361', '-0.100000000', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('0.960700280', 'nan', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.split('主光线逐面透过率')[0], 'NO_RESULT_DATA'),
    (lambda body: body.replace('   2 \t    0.980259', '   0 \t    0.980259', 1), 'INVALID_RESULT_DATA'),
])
def test_malformed_reports_raise_specific_codes(mutation, code):
    with pytest.raises(ZemaxError) as caught:
        parse_polarization_transmission_text(mutation(text()))
    assert caught.value.code == code


def test_surface_block_without_a_wavelength_row_is_rejected():
    chief = CHIEF.replace('波长 2: 0.550 µm\n\n', '')
    with pytest.raises(ZemaxError) as caught:
        parse_polarization_transmission_text(text(chief=chief))
    assert caught.value.code == 'INVALID_RESULT_DATA'
    assert '缺少波长行' in str(caught.value)


def test_vignetting_annotations_preserve_original_and_area_adjusted_values():
    fields='视场 Pos : 0.0000 (度) (相对渐晕光瞳面积 = 0.560)\n 透射 0.4800: 0.9 (渐晕 0.504)\n 总透射 : 0.9 (渐晕 0.504)\n'
    data=parse_polarization_transmission_text(text(fields=fields))
    field=data['fields'][0]
    assert field['field_position_values']==[0.]
    assert field['relative_vignetted_pupil_area']==.56
    assert field['wavelengths'][0]==dict(wavelength_um=.48,transmission=.9,vignetted_transmission=.504)
    assert field['total_transmission']==.9 and field['total_vignetted_transmission']==.504
    assert data['rows'][0]['vignetted_transmission']==.504
