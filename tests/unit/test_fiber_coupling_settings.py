from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.polarization_topics import FiberCouplingSettings, parse_fiber_coupling_text

REPORT = (
    '光纤耦合效率-惠更斯积分法\n\n'
    '文件 : C:\\work\\lens.zos\n'
    '题目: A SIMPLE COOKE TRIPLET.\n'
    '日期 : 2026/11/8\n\n\n'
    '波长                      :\t       0.550000 µm.\n'
    '视场类型                      :\t 角（度）\n'
    'X 视场 坐标              :\t   0.000000E+00\n'
    'Y 视场 坐标              :\t   0.000000E+00\n'
    '位置单位                  :\t 毫米\n'
    '角度单位                   :\t 度\n\n'
    '源光纤                    :\t 忽略\n\n'
    '接收光纤 NA X-方向   :\t       0.100000\n'
    '接收光纤 NA Y-方向   :\t       0.100000\n'
    '接收名义位置X     :\t       0.000000\n'
    '接收名义位置Y     :\t       0.000000\n'
    '接收偏心X             :\t       0.000000\n'
    '接收偏心Y             :\t       0.000000\n'
    '接收偏心 Z            :\t       0.000000\n'
    '接收关于X倾斜(deg)     :\t       0.000000\n'
    '接收关于Y倾斜(deg)     :\t       0.000000\n\n'
    '系统 效率               :\t       1.000000\n\n'
    '接收 效率             :\t       0.148061\n\n'
    '耦合效率             :\t       0.148061\t (-8.2956 dB)\n\n'
    '系统效率是源光束能量\n'
    '存在于光学系统中的部分。这个值由以下因素决定:\n'
    '入射NA，入瞳尺寸和位置，切趾，\n'
    '光学元件的透射率和渐晕。\n\n'
    '接收效率是透射能量从\n'
    '出瞳耦合到接收光纤中的部分。\n'
    '该值由接收光纤的NA及像差大小决定。\n\n'
    '耦合效率是\n'
    '由源光纤辐射能量耦合到接收光纤中的部分。\n'
    '该值是系统效率和接收效率的乘积。\n'
)


def test_default_request_retains_native_route():
    from zemax_mcp.fiber_operand import uses_operand
    assert not uses_operand(FiberCouplingSettings(kind='fiber_coupling_settings'))
    assert RunAnalysis(request=dict(kind='fiber_coupling_settings')).request.kind == 'fiber_coupling_settings'


@pytest.mark.parametrize('patch', [dict(receiver_na_x=0.1), dict(receiver_na_y=0.1), dict(field=0), dict(wavelength=0),
                                   dict(receiver_position=0.0), dict(source_fiber='file.fib')])
def test_request_rejects_selector_parameters(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='fiber_coupling_settings', **patch))


def test_parses_header_receiver_and_efficiencies():
    data = parse_fiber_coupling_text(REPORT)
    header = data['input_header']
    assert header['wavelength_um'] == pytest.approx(0.55, abs=1e-12)
    assert header['field_type'] == '角（度）'
    assert header['field_position'] == dict(x=0.0, y=0.0)
    assert header['position_units'] == '毫米' and header['angle_units'] == '度'
    assert header['source_fiber'] == '忽略'
    assert data['receiver']['na_x'] == pytest.approx(0.1) and data['receiver']['na_y'] == pytest.approx(0.1)
    assert data['receiver']['position_x'] == 0.0 and data['receiver']['position_y'] == 0.0
    assert data['receiver']['decenter'] == dict(x=0.0, y=0.0, z=0.0)
    assert data['receiver']['tilt_deg'] == dict(x=0.0, y=0.0)
    assert data['efficiencies'] == dict(system=1.0, receiver=pytest.approx(0.148061), total_coupling=pytest.approx(0.148061))
    assert data['total_coupling_db'] == pytest.approx(-8.2956)


def test_product_identity_is_recorded_as_consistency():
    data = parse_fiber_coupling_text(REPORT)
    consistency = data['consistency']
    assert consistency['status'] == 'match'
    assert consistency['residual'] == pytest.approx(0.0, abs=1e-12)
    assert consistency['product'] == pytest.approx(0.148061)
    assert consistency['tolerance'] == 1e-6
    assert 'times receiver efficiency' in consistency['identity']


@pytest.mark.parametrize('title,expected', [
    ('光纤耦合效率-惠更斯积分法', 'huygens'),
    ('Fiber Coupling Efficiency - Huygens Integral', 'huygens'),
    ('Fiber Coupling Efficiency - Ray-based Integration', 'ray_based'),
    ('光纤耦合效率', None),
])
def test_integration_method_requires_report_title_evidence(title, expected):
    data = parse_fiber_coupling_text(REPORT.replace('光纤耦合效率-惠更斯积分法', title, 1))
    assert data['integration_method'] == expected
    assert data['integration_method_source']['title'] == title
    assert data['integration_method_source']['status'] == ('declared' if expected else 'not_declared')
    assert 'Huygens integral' not in data['computation_method']


def test_integration_method_does_not_use_incidental_body_mentions():
    body = REPORT.replace('光纤耦合效率-惠更斯积分法', '光纤耦合效率', 1)
    data = parse_fiber_coupling_text(body+'\nConsider using Huygens if ray-based integration fails.\n')
    assert data['integration_method'] is None


def test_product_mismatch_is_recorded_not_raised():
    report = REPORT.replace('耦合效率             :\t       0.148061', '耦合效率             :\t       0.500000')
    data = parse_fiber_coupling_text(report)
    assert data['consistency']['status'] == 'mismatch'
    assert data['consistency']['residual'] == pytest.approx(0.5 - 0.148061, abs=1e-12)


def test_definitions_and_units_are_preserved():
    data = parse_fiber_coupling_text(REPORT)
    assert 'entrance-pupil' in data['definition']['system']
    assert 'product' in data['definition']['total_coupling']
    assert any('接收效率' in line for line in data['definition']['definition_lines'])
    assert data['units']['efficiency'] == 'dimensionless fraction'
    assert data['units']['na'] == 'dimensionless numerical aperture'
    assert data['selection']['writable_selectors'] == []
    assert data['structured_data_available'] is True


def test_rows_page_through_the_shared_task_result_path():
    data = parse_fiber_coupling_text(REPORT)
    assert [row['quantity'] for row in data['rows']] == ['system_efficiency', 'receiver_efficiency', 'total_coupling_efficiency']
    page = Backend._page_task_result(None, data, N(series=None, grid=None, start=1, count=1))
    assert [row['value'] for row in page['rows']] == [pytest.approx(0.148061)]
    assert page['total'] == 3 and page['next_start'] == 2


@pytest.mark.parametrize('mutation,code', [
    (lambda body: body.replace('接收光纤 NA X-方向   :\t       0.100000\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('系统 效率               :\t       1.000000\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('接收 效率             :\t       0.148061', '接收 效率             :\t       1.480610'), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('接收光纤 NA Y-方向   :\t       0.100000', '接收光纤 NA Y-方向   :\t       0.000000'), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('耦合效率             :\t       0.148061\t (-8.2956 dB)', '耦合效率             :\t        nan\t (-8.2956 dB)'), 'INVALID_RESULT_DATA'),
    (lambda body: body.split('波长                      :')[0], 'INVALID_RESULT_DATA'),
])
def test_malformed_reports_raise_specific_codes(mutation, code):
    with pytest.raises(ZemaxError) as caught:
        parse_fiber_coupling_text(mutation(REPORT))
    assert caught.value.code == code


def test_full_width_colon_is_accepted():
    report = REPORT.replace('系统 效率               :\t       1.000000', '系统 效率               ：\t       1.000000')
    assert parse_fiber_coupling_text(report)['efficiencies']['system'] == 1.0
