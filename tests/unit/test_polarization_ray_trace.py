from types import SimpleNamespace as N

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.polarization_topics import PolarizationRayTrace, parse_polarization_ray_trace_text
from zemax_mcp.polarization_operand import run_polarization_operand, uses_operand

HEADER = (
    '偏振光线追迹数据\n\n'
    '文件 : C:\\work\\lens.zos\n'
    '题目: A SIMPLE COOKE TRIPLET.\n'
    '日期 : 2026/11/8\n\n\n'
    '透镜单位                    :\t 毫米.\n'
    '波长                        :\t     0.550000000 µm\n'
    '归一化X视场坐标(Hx) :\t     0.000000000\n'
    '归一化Y视场坐标(Hy) :\t     0.000000000\n'
    '归一化X光瞳坐标(Px) :\t     0.000000000\n'
    '归一化Y光瞳坐标(Py) :\t     1.000000000\n\n'
    '输入偏振:\n'
    'X-视场   :\t  0.000000\n'
    'Y-视场   :\t  1.000000\n'
    'X-相位   :\t  0.000000\n'
    'Y-相位   :\t  0.000000\n\n'
    '所有坐标和余弦在表面局部坐标中.\n\n\n'
)
BLOCK = (
    '追迹光线到表面{surface}:\t \n\n'
    '通过空气的路径长度                              (tau):\t   5.7534969E-01\n'
    '每透镜单位的内部吸收    (alpha):\t   0.0000000E+00\n'
    '光线的内部透射率           (IT):\t  1.000000000000\n'
    '传播相位因子           (pc,ps):\t  0.843160781146\t -0.537661507956\n'
    '表面坐标               (x,y,z):\t   0.0000000E+00\t   5.0000000E+00\t   5.7534969E-01\n'
    '入射光线的方向余弦 (l1,m1,n1):\t  0.000000000000\t  0.000000000000\t  1.000000000000\n'
    '入射光线的余弦角             :\t  0.973863889316\t (13.128302 deg)\n'
    '出射光线的余弦角                 :\t  0.990154351127\t (8.046681 deg)\n'
    '出射光线的方向余弦     (l2,m2,n2):\t  0.000000000000\t -0.088574799707\t  0.996069528124\n'
    '法线的方向余弦       (ln,mn,nn):\t  0.000000000000\t  0.227132395500\t -0.973863889316\n'
    'S弧矢的方向余弦     (sx,sy,sz):\t  1.000000000000\t -0.000000000000\t  0.000000000000\n'
    'P弧矢的方向余弦     (px,py,pz):\t  0.000000000000\t  1.000000000000\t -0.000000000000\n'
    '在膜层前面的E电场(xyz)   (Exr,Eyr,Ezr):\t  0.000000000000\t  0.843160781146\t  0.000000000000\n'
    '                               (Exi,Eyi,Ezi):\t  0.000000000000\t -0.537661507956\t  0.000000000000\n'
    '在膜层前面的E电场(s&p)       (Esr,Epr):\t  0.000000000000\t  0.843160781146\n'
    '                                   (Esi,Epi):\t  0.000000000000\t -0.537661507956\n'
    '在膜层前的光线强度            (I1):\t  1.000000000000\n'
    '膜层                                     :\t  AR\n'
    '反射系数强度    (Rs,Rp):\t  0.006994076309\t  0.005597273491\n'
    '透射系数强度  (Ts,Tp):\t  0.993005923691\t  0.994402726509\n'
    '吸收系数强度    (As,Ap):\t  0.000000000000\t  0.000000000000\n'
    '双衰减                                   (D):\t  0.000702826174\n'
    '场振幅反射S极   (rsr,rsi):\t -0.083554527385\t  0.003566127081\n'
    '场振幅反射P极   (rpr,rpi):\t -0.074737436733\t  0.003404268073\n'
    '场振幅透射S极(tsr,tsi):\t  0.021977167663\t -0.996254449321\n'
    '场振幅透射P极(tpr,tpi):\t  0.021921579502\t -0.996956453844\n'
    '场反射相位             (Prs,Prp):\t  3.098938303179\t  3.096074412881\n'
    '场反射迟缓(P-S)       (Sr):\t -0.002863890297\t (-0.164089 deg)\n'
    '场反射迟缓(P-S+pi)    (Sr):\t  3.138728763292\t (179.835911 deg)\n'
    '场透射相位           (Pts,Ptp):\t -1.548740110364\t -1.548811367014\n'
    '场透射迟缓(P-S)     (St):\t -0.000071256651\t (-0.004083 deg)\n'
    '场透射迟缓(P-S+pi)  (St):\t  3.141521396939\t (179.995917 deg)\n'
    '光线振幅反射S极     (rsr,rsi):\t  0.047593934380\t -0.068766952231\n'
    '光线振幅反射P极     (rpr,rpi):\t  0.042400608353\t -0.061639775323\n'
    '光线振幅透射S极   (tsr,tsi):\t  0.909003785103\t -0.408311207731\n'
    '光线振幅透射P极   (tpr,tpi):\t  0.909613763768\t -0.408663097519\n'
    '光线反射相位               (Prs,Prp):\t -0.965388864260\t -0.968252754557\n'
    '光线反射延迟(P-S)         (Sr):\t -0.002863890297\t (-0.164089 deg)\n'
    '光线反射延迟(P-S+pi)      (Sr):\t  3.138728763292\t (179.835911 deg)\n'
    '光线透射相位             (Pts,Ptp):\t -0.422176278332\t -0.422247534983\n'
    '光线透射延迟(P-S)       (St):\t -0.000071256651\t (-0.004083 deg)\n'
    '光线透射延迟(P-S+pi)    (St):\t  3.141521396939\t (179.995917 deg)\n'
    '在膜层后的电场       (Esr,Epr):\t  0.000000000000\t  0.547228234341\n'
    '                                   (Esi,Epi):\t  0.000000000000\t -0.833633004414\n'
    '在膜层后的光线强度             (I2):\t  0.994402726509\n'
    '新S弧矢的方向余弦 (sx,sy,sz):\t  1.000000000000\t -0.000000000000\t  0.000000000000\n'
    '新P弧矢的方向余弦 (px,py,pz):\t  0.000000000000\t  0.996069528124\t  0.088574799707\n'
    'E电场后                  (Exr,Eyr,Ezr):\t  0.000000000000\t  0.545077369156\t  0.048470631251\n'
    '                               (Exi,Eyi,Ezi):\t  0.000000000000\t -0.830356433336\t -0.073838876395\n'
    'X,Y和Z方向的振幅(Ax, Ay, Az):\t  0.000000000000\t  0.993277979595\t  0.088326563168\n'
    ' X,Y和Z方向的相位     (Px, Py, Pz):\t  0.000000000000\t -0.989908700964\t -0.989908700964\n'
    'X和Y的相位差       (Pxy):\t  0.989908700964\t (56.717591 deg)\n'
    '长，短半轴XY椭圆   (EM, Em):\t  1.000000000000\t  0.000000000000\n'
    'XY偏振椭圆的角度        (Ap):\t  1.570796326795\t (90.000000 deg)\n'
    '输出光线强度                     (I2):\t  0.994402726509\n\n\n'
)
SUMMARY = '总结\n\n总透射强度:\t  0.965740841914\n'


def text(blocks=(1, 2), summary=SUMMARY):
    return HEADER + ''.join(BLOCK.format(surface=surface) for surface in blocks) + summary


def test_request_is_kind_only():
    request = PolarizationRayTrace(kind='polarization_ray_trace')
    assert request.model_fields_set == {'kind'}
    assert not uses_operand(request)


@pytest.mark.parametrize('patch', [dict(hx=0), dict(hy=0), dict(px=0), dict(py=1),
                                   dict(jx=1), dict(global_coordinates=True), dict(field=0),
                                   dict(wavelength=0), dict(pupil_x=-1.1), dict(pupil_y=float('nan'))])
def test_request_rejects_selector_parameters(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='polarization_ray_trace', **patch))


def test_operand_selector_and_native_rejection():
    assert uses_operand(PolarizationRayTrace(kind='polarization_ray_trace', pupil_x=.2))
    assert uses_operand(PolarizationRayTrace(kind='polarization_ray_trace', method='operand'))
    with pytest.raises(ZemaxError, match='选择器'):
        uses_operand(PolarizationRayTrace(kind='polarization_ray_trace', method='native', field=1))


def test_operand_returns_documented_codes_and_selected_identity():
    class Fake:
        def __init__(self):
            self.values=[]
            self.native=N(api=N(Editors=N(MFE=N(MeritOperandType=object()))),enum=lambda *args:'CODA')
            self.system=N(LDE=N(NumberOfSurfaces=5),MFE=N(GetOperandValue=self.query))
        def query(self, code, *args):
            self.values.append((code,args));return float(args[3])
        def _require_sequential(self):pass
        def get_system_settings(self, _):
            return dict(fields=[dict(number=1,x=0,y=0)],wavelengths=[dict(number=1,wavelength_um=.55)],configuration=1,polarization=dict(jx=0,jy=1))
        def _composite(self,kind,settings,factory):
            self.task=dict(rows=[]);self.flow=factory(self.task);return self.task
        def _cancel_boundary(self,task):pass
    b=Fake();q=PolarizationRayTrace(kind='polarization_ray_trace',method='operand',surface=0,pupil_x=.2)
    run_polarization_operand(b,q);list(b.flow)
    assert len(b.values)==len(b.task['rows'])==29
    assert all(args[0:3]==(0,1,1) and args[4:6]==(.2,1.) for _,args in b.values)
    assert b.task['payload']['actual_settings']['surface']==0
    assert b.task['rows'][0]['quantity']=='s_reflectance'
    assert b.task['rows'][14]['quantity']=='ex_real'
    phase = next(row for row in b.task['rows'] if row['quantity']=='phase_y_deg')
    assert phase['value']==pytest.approx(__import__('math').degrees(112.))
    assert phase['unit']=='degrees'
    assert b.task['payload']['native_phase_unit']=='radians'
    assert next(row for row in b.task['payload']['native_queries'] if row['arguments'][3]==112)['value']==112.
    assert b.task['payload']['native_ellipse_angle_unit']=='degrees'
    ellipse = next(row for row in b.task['rows'] if row['quantity']=='ellipse_angle_deg')
    assert ellipse == dict(quantity='ellipse_angle_deg', value=123., unit='degrees')
    assert {row['quantity']: row['value'] for row in b.task['rows']}['polarized_transmitted_intensity']==0.


def test_parses_header_polarization_and_surfaces():
    data = parse_polarization_ray_trace_text(text())
    header = data['input_header']
    assert header['lens_units'] == '毫米'
    assert header['wavelength_um'] == 0.55
    assert header['pupil'] == dict(hx=0.0, hy=0.0, px=0.0, py=1.0)
    assert header['jones'] == dict(jx=0.0, jy=1.0, x_phase_deg=0.0, y_phase_deg=0.0)
    assert header['global_coordinates'] is False
    assert data['total_transmission'] == pytest.approx(0.965740841914, abs=1e-15)
    assert [row['surface'] for row in data['rows']] == [1, 2]


@pytest.mark.parametrize('failure', ['cancel', 'nonfinite', 'native'])
def test_operand_stops_at_failure_without_consuming_remaining_queries(failure):
    from zemax_mcp.evaluation import Cancelled

    calls = []
    task = dict(rows=[])

    def query(*args):
        calls.append(args)
        if len(calls) == 2:
            if failure == 'native':
                raise RuntimeError('CODA controlled native failure')
            if failure == 'nonfinite':
                return float('nan')
        return .25

    def boundary(current):
        if failure == 'cancel' and len(current['rows']) == 1:
            raise Cancelled()

    def composite(kind, settings, factory):
        return factory(task)

    backend = N(
        _require_sequential=lambda: None,
        get_system_settings=lambda _: dict(fields=[dict(number=1)], wavelengths=[dict(number=1)],
                                          polarization={}, configuration=1),
        native=N(enum=lambda *args: 'CODA', api=N(Editors=N(MFE=N(MeritOperandType=None)))),
        system=N(LDE=N(NumberOfSurfaces=3), MFE=N(GetOperandValue=query)),
        _composite=composite, _cancel_boundary=boundary)
    flow = run_polarization_operand(backend, PolarizationRayTrace(kind='polarization_ray_trace', method='operand'))
    expected = {'cancel': Cancelled, 'nonfinite': ZemaxError, 'native': RuntimeError}[failure]
    with pytest.raises(expected) as caught:
        list(flow)
    assert len(task['rows']) == 1
    assert len(calls) == (1 if failure == 'cancel' else 2)
    if failure == 'nonfinite':
        assert caught.value.code == 'INVALID_RESULT_DATA'
        assert caught.value.details['quantity'] == 's_transmittance'
    if failure == 'native':
        assert str(caught.value) == 'CODA controlled native failure'


def test_parses_scalars_vectors_complex_fields_and_angles():
    row = parse_polarization_ray_trace_text(text())['rows'][0]
    assert row['path_length'] == pytest.approx(0.57534969, abs=1e-12)
    assert row['internal_transmittance'] == 1.0
    assert row['propagation_phase'] == pytest.approx([0.843160781146, -0.537661507956], abs=1e-15)
    assert row['surface_coordinates'] == pytest.approx([0.0, 5.0, 0.57534969], abs=1e-12)
    assert row['s_vector'] == pytest.approx([1.0, 0.0, 0.0], abs=1e-15)
    assert row['incident_angle'] == dict(value=0.973863889316, deg=13.128302)
    assert row['ellipse_angle'] == dict(value=1.570796326795, deg=90.0)
    assert row['coating'] == 'AR'
    assert row['reflectance'] == pytest.approx([0.006994076309, 0.005597273491], abs=1e-15)
    assert row['transmittance'] == pytest.approx([0.993005923691, 0.994402726509], abs=1e-15)
    assert row['diattenuation'] == pytest.approx(0.000702826174, abs=1e-15)
    assert row['e_before_coating_xyz'] == dict(real=[0.0, 0.843160781146, 0.0],
                                               imag=[0.0, -0.537661507956, 0.0])
    assert row['e_before_coating_sp'] == dict(real=[0.0, 0.843160781146], imag=[0.0, -0.537661507956])
    assert row['e_after_coating_sp'] == dict(real=[0.0, 0.547228234341], imag=[0.0, -0.833633004414])
    assert row['e_after_coating_xyz'] == dict(real=[0.0, 0.545077369156, 0.048470631251],
                                              imag=[0.0, -0.830356433336, -0.073838876395])
    assert row['field_amplitude_reflection_s'] == dict(real=-0.083554527385, imag=0.003566127081)
    assert row['ray_amplitude_transmission_p'] == dict(real=0.909613763768, imag=-0.408663097519)
    assert row['field_reflection_retardance'] == dict(value=-0.002863890297, deg=-0.164089)
    assert row['field_reflection_retardance_pi'] == dict(value=3.138728763292, deg=179.835911)
    assert row['ray_transmission_retardance_pi'] == dict(value=3.141521396939, deg=179.995917)
    assert row['intensity_before'] == 1.0 and row['intensity_after'] == pytest.approx(0.994402726509, abs=1e-15)
    assert row['amplitude_xyz'] == pytest.approx([0.0, 0.993277979595, 0.088326563168], abs=1e-15)
    assert row['phase_difference_xy'] == pytest.approx([0.989908700964, 56.717591], abs=1e-15)
    assert row['ellipse_axes'] == pytest.approx([1.0, 0.0], abs=1e-15)


def test_energy_identity_holds_for_the_first_surface():
    row = parse_polarization_ray_trace_text(text())['rows'][0]
    assert row['intensity_after'] == pytest.approx(row['intensity_before'] * row['transmittance'][1], abs=1e-12)
    assert row['reflectance'][1] + row['transmittance'][1] + row['absorptance'][1] == pytest.approx(1.0, abs=1e-12)


def test_full_width_colon_labels_are_accepted():
    body = text().replace('膜层                                     :\t  AR', '膜层                                     ：\t  AR')
    data = parse_polarization_ray_trace_text(body)
    assert data['rows'][0]['coating'] == 'AR'


def test_rows_page_through_the_shared_task_result_path():
    data = parse_polarization_ray_trace_text(text())
    page = Backend._page_task_result(None, data, N(series=None, grid=None, start=0, count=1))
    assert len(page['rows']) == 1 and page['total'] == 2 and page['next_start'] == 1
    assert page['rows'][0]['surface'] == 1
    tail = Backend._page_task_result(None, data, N(series=None, grid=None, start=1, count=5))
    assert tail['next_start'] is None and tail['rows'][0]['surface'] == 2


def test_units_and_phase_convention_are_declared():
    data = parse_polarization_ray_trace_text(text())
    assert data['units']['path_length'] == 'lens units'
    assert 'radians' in data['units']['phase']
    assert data['units']['ellipse']=='major/minor semi-axis amplitudes of the local XY electric-field projection'
    assert 'not verified' in data['phase_convention']
    assert data['selection']['writable_selectors'] == []
    assert data['structured_data_available'] is True


@pytest.mark.parametrize('mutation,code', [
    (lambda body: body.replace('波长                        :\t     0.550000000 µm\n', ''), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('Y-相位   :\t  0.000000\n\n', '', 1), 'INVALID_RESULT_DATA'),
    (lambda body: body.split('追迹光线到表面')[0], 'NO_RESULT_DATA'),
    (lambda body: body.replace('总透射强度', '总透射'), 'NO_RESULT_DATA'),
    (lambda body: '\n'.join(line for line in body.splitlines() if '(I1)' not in line), 'INVALID_RESULT_DATA'),
    (lambda body: body.replace('0.965740841914', 'nan'), 'INVALID_RESULT_DATA'),
    (lambda body: text(blocks=(1, 1)), 'INVALID_RESULT_DATA'),
    (lambda body: '\n'.join(line.replace('\t  0.000000000000\t -0.830356433336\t -0.073838876395',
                                         '\t  0.000000000000\t -0.830356433336')
                            for line in body.splitlines()), 'INVALID_RESULT_DATA'),
])
def test_malformed_reports_raise_specific_codes(mutation, code):
    with pytest.raises(ZemaxError) as caught:
        parse_polarization_ray_trace_text(mutation(text()))
    assert caught.value.code == code


def test_non_increasing_surface_numbers_are_rejected():
    with pytest.raises(ZemaxError) as caught:
        parse_polarization_ray_trace_text(text(blocks=(2, 1)))
    assert caught.value.code == 'INVALID_RESULT_DATA'
    assert caught.value.details['surfaces'] == [2, 1]


def test_unbalanced_complex_continuation_is_rejected():
    body = '\n'.join(line.replace('\t  0.000000000000\t -0.537661507956\t  0.000000000000',
                                  '\t  0.000000000000\t -0.537661507956')
                     for line in text().splitlines())
    with pytest.raises(ZemaxError) as caught:
        parse_polarization_ray_trace_text(body)
    assert caught.value.code == 'INVALID_RESULT_DATA'
