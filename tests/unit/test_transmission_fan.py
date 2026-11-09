import pytest
from pydantic import ValidationError
from types import SimpleNamespace as N

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.basic_analyses import parse_polarization_transmission_fan
from zemax_mcp.errors import ZemaxError
from zemax_mcp.transmission_fan import transmission_fan, uses_batch


def report(header='0.55', rows='-1 .9\n0 .91\n1 .9'):
    return '场是非偏振的。\n子午光扇，视场号1 = 0.00 (度)\n光瞳 '+header+'\n'+rows


@pytest.mark.parametrize('waves', [[.55], [.55,.65], [.48,.55,.65,.7]])
def test_fan_retains_any_native_wavelength_column_count(waves):
    text=report(' '.join(map(str,waves)), '\n'.join(str(x)+' '+' '.join(str(.8+i*.01) for i in range(len(waves))) for x in [-1,0,1]))
    result=parse_polarization_transmission_fan(text)
    assert result['wavelengths_um']==waves
    assert len(result['series'])==len(waves)
    for i,series in enumerate(result['series']):
        assert series['wavelength_um']==waves[i]
        assert series['y']==[[.8+i*.01]]*3


@pytest.mark.parametrize('header,rows', [
    ('0.55','-1 .9\n0 NaN\n1 .9'),
    ('0.55','-1 .9\n0 1e999\n1 .9'),
    ('0.55','-1 .9\n0 -1\n1 .9'),
    ('0.55','-1 .9\n0 bad\n1 .9'),
    ('0.55','-1 .9\n0 .9 1\n1 .9'),
    ('0.55','-1 .9\n-1 .9'),
    ('0.55','0 .9\n-1 .9'),
    ('0.55','-1.1 .9\n1 .9'),
    ('0.55 0.55','-1 .9 .9\n1 .9 .9'),
    ('0','-1 .9\n1 .9'),
    ('NaN','-1 .9\n1 .9'),
    ('1e999','-1 .9\n1 .9'),
    ('bad','-1 .9\n1 .9'),
    ('0.55','-1 .9\n光瞳 0.55\n1 .9'),
])
def test_fan_rejects_damaged_data_instead_of_partial_curves(header,rows):
    with pytest.raises(ZemaxError):
        parse_polarization_transmission_fan(report(header,rows))


def test_fan_rejects_unknown_polarization_and_duplicate_sections():
    with pytest.raises(ZemaxError):
        parse_polarization_transmission_fan(report().replace('非偏振','偏振'))
    with pytest.raises(ZemaxError):
        parse_polarization_transmission_fan(report()+'\n'+report())


def test_fan_rejects_wavelength_mismatch_between_sections():
    with pytest.raises(ZemaxError):
        parse_polarization_transmission_fan(report()+'\n'+report('0.65').replace('子午','弧矢'))


def test_fan_preserves_native_invalid_ray_markers_per_wavelength():
    result=parse_polarization_transmission_fan(report('0.55 0.65','-1.000-------------       0.9000\n0 .91 .92\n1 .9-------------'))
    assert result['series'][0]['y']==[[None],[.91],[.9]]
    assert result['series'][1]['y']==[[.9],[.92],[None]]
    assert [s['invalid_count'] for s in result['series']]==[1,1]
    assert [r['invalid_count'] for r in result['rows']]==[1,0,1]


def request(**values):
    return RunAnalysis(request=dict(kind='polarization_transmission_fan',**values)).request


@pytest.mark.parametrize('values',[dict(sampling=4),dict(sampling=True),dict(sampling=1003),dict(field=-1),
    dict(polarization=dict(jx=0,jy=0)),dict(polarization=dict(jx=-1)),dict(polarization=dict(y_phase=float('inf')))])
def test_fan_typed_selectors_reject_invalid_values(values):
    with pytest.raises(ValidationError):request(**values)


def test_fan_method_selection_preserves_native_default_and_rejects_unadopted_settings():
    assert not uses_batch(request())
    assert uses_batch(request(field=0))
    assert uses_batch(request(method='ray_trace'))
    with pytest.raises(ZemaxError):uses_batch(request(method='native',wavelength=1))


def fake_backend(invalid=False):
    settings=dict(fields=[dict(number=1,x=0.,y=0.)],wavelengths=[dict(number=1,wavelength_um=.55)],
        configuration=1,field_normalization='Radial')
    backend=N(system=N(LDE=N(NumberOfSurfaces=3)),get_system_settings=lambda _:settings,
        _require_sequential=lambda:None,_cancel_boundary=lambda _:None,calls=[])
    def run(req):return req
    backend.run_batch_ray_trace=run
    def child(task,method,req):
        backend.calls.append(req)
        yield
        return dict(rows=[dict(state='vignetted' if invalid and i==0 else 'succeeded',
            error_code=0,vignette_code=1 if invalid and i==0 else 0,
            intensity=.8 if req.polarization and req.polarization.jx else .6) for i,_ in enumerate(req.rays)])
    backend._child_job=child
    def composite(kind,settings,flow):
        task=dict(rows=[])
        list(flow(task))
        return task
    backend._composite=composite
    return backend


def test_fan_batch_averages_two_basis_powers_and_preserves_invalid_status():
    backend=fake_backend(invalid=True)
    task=transmission_fan(backend,request(method='ray_trace',sampling=3))
    assert len(backend.calls)==6
    assert task['payload']['series'][0]['y']==[[None],[.7],[.7]]
    assert task['payload']['series'][0]['invalid_count']==1
    assert task['rows'][0]['ray_status'][0]['vignette_code']==1
    assert task['payload']['actual_settings']['field_numbers']==[1]


def test_fan_jones_normalizes_large_finite_amplitudes_without_overflow():
    backend=fake_backend()
    task=transmission_fan(backend,request(sampling=3,polarization=dict(jx=1e308,jy=1e308,y_phase=90)))
    assert len(backend.calls)==4
    assert task['payload']['actual_settings']['polarization_inputs'][0]['jx']==pytest.approx(2**-.5)


def test_fan_bounds_and_cancellation_precede_ray_execution():
    backend=fake_backend()
    with pytest.raises(ZemaxError):transmission_fan(backend,request(field=2))
    with pytest.raises(ZemaxError):transmission_fan(backend,request(wavelength=2))
    from zemax_mcp.evaluation import Cancelled
    def cancel(_):raise Cancelled()
    backend._cancel_boundary=cancel
    with pytest.raises(Cancelled):transmission_fan(backend,request(sampling=3))
    assert backend.calls==[]
