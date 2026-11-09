from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.transmission_pupil import uses_batch,pupil_nodes,transmission_pupil


def request(**values):return RunAnalysis(request=dict(kind='polarization_transmission',**values)).request


def test_native_default_and_selector_routing():
    assert not uses_batch(request())
    assert uses_batch(request(field=0))
    assert uses_batch(request(method='ray_trace'))
    with pytest.raises(ZemaxError):uses_batch(request(method='native',sampling=32))


@pytest.mark.parametrize('values',[dict(sampling=31),dict(sampling=True),dict(field=-1),dict(polarization=dict(jx=0,jy=0)),dict(polarization=dict(jx=float('inf')))])
def test_invalid_contract(values):
    with pytest.raises(ValidationError):request(**values)


def fake():
    settings=dict(fields=[dict(number=1,x=0.,y=0.)],wavelengths=[dict(number=1,wavelength_um=.55,weight=1)],
        configuration=1,field_normalization='Radial',polarization=dict(unpolarized=True,jx=1.,jy=0.,x_phase=0.,y_phase=0.))
    b=N(system=N(LDE=N(NumberOfSurfaces=3,GetApodization=lambda x,y:1.)),get_system_settings=lambda _:settings,
        _require_sequential=lambda:None,_cancel_boundary=lambda _:None,run_batch_ray_trace=lambda q:q,calls=[])
    def child(task,method,q):
        b.calls.append(q);yield
        return dict(rows=[dict(state='vignetted' if q.polarization is None and ray.px<0 else 'succeeded',
            error_code=0,vignette_code=1 if ray.px<0 else 0,intensity=.8 if q.polarization and q.polarization.jx else .6) for ray in q.rays])
    b._child_job=child
    def composite(kind,settings,flow):
        t=dict(rows=[]);list(flow(t));return t
    b._composite=composite
    return b


def test_pupil_losses_count_in_denominator_and_chief_has_surface_identity():
    b=fake();t=transmission_pupil(b,request(method='ray_trace',sampling=8))
    p=pupil_nodes(8);ref=.7*sum(x>=0 for x,y in p)/len(p)
    item=t['payload']['fields'][0]['wavelengths'][0]
    assert item['transmission']==pytest.approx(ref)
    assert item['vignetted']==sum(x<0 for x,y in p)
    assert len(t['rows'])==len(p)
    assert [r['surface'] for r in t['payload']['chief_ray_surfaces'][0]['rows']]==[1,2]
    assert t['payload']['chief_ray_surfaces'][0]['final_total']==pytest.approx(.7)


def test_large_jones_amplitudes_normalize_without_overflow():
    t=transmission_pupil(fake(),request(sampling=8,polarization=dict(jx=1e308,jy=1e308),include_chief_ray=False))
    assert t['payload']['actual_settings']['polarization_inputs'][0]['jx']==pytest.approx(2**-.5)


def test_bounds_and_cancellation_precede_child_execution():
    b=fake()
    with pytest.raises(ZemaxError):transmission_pupil(b,request(field=2))
    def cancel(_):raise RuntimeError('cancelled')
    b._cancel_boundary=cancel
    with pytest.raises(RuntimeError,match='cancelled'):transmission_pupil(b,request(sampling=8))
    assert not b.calls


def test_integrated_transmission_normalizes_by_incident_apodized_power():
    b=fake();b.system.LDE.GetApodization=lambda x,y: .5
    t=transmission_pupil(b,request(sampling=8,include_chief_ray=False))
    p=pupil_nodes(8);expected=.7*sum(x>=0 for x,y in p)/(.5*len(p))
    item=t['payload']['fields'][0]['wavelengths'][0]
    assert item['transmission']==pytest.approx(expected)
    assert item['incident_power']==.5*len(p)
    assert all(r['incident_power']==.5 for r in t['rows'])


@pytest.mark.parametrize('fault',['missing','short','nan'])
def test_invalid_native_child_data_keeps_specific_failure(fault):
    b=fake();original=b._child_job
    def child(task,method,q):
        result=yield from original(task,method,q)
        if q.polarization:
            if fault=='missing':result['rows'][0]['state']='missing'
            elif fault=='short':result['rows'].pop()
            else:result['rows'][-1]['intensity']=float('nan')
        return result
    b._child_job=child
    with pytest.raises(ZemaxError) as exc:transmission_pupil(b,request(sampling=8))
    assert exc.value.code=='INVALID_RESULT_DATA'


def test_zero_incident_power_is_an_explicit_no_data_result():
    b=fake();b.system.LDE.GetApodization=lambda x,y:0.
    with pytest.raises(ZemaxError) as exc:transmission_pupil(b,request(sampling=8))
    assert exc.value.code=='NO_RESULT_DATA'
