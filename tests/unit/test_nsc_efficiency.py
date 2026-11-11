import math
from types import SimpleNamespace as S

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.nsc_efficiency import NscEfficiency, roi_statistics, run_nsc_efficiency, score


def query(**kw):
    return dict(kind='nsc_efficiency',sources=[1],detectors=[dict(detector=2,width=2,height=2)])|kw


@pytest.mark.parametrize('change',[
    dict(sources=[1,1]),dict(sources=[]),dict(detectors=[]),dict(random_seed=-1),dict(rays_per_source=0),
    dict(rays_per_source=100,verification_rays_per_source=99),dict(verification_seeds=[1,1]),
    dict(mode='scan'),dict(mode='optimize'),dict(detectors=[dict(detector=2,width=0,height=2)]),
    dict(detectors=[dict(detector=2,width=128,height=128)]),dict(hotspot_factor=1),
    dict(detectors=[dict(detector=2,width=2,height=2),dict(detector=2,width=1,height=1)]),
    dict(variables=[dict(object=1,cell='Power',minimum=0,maximum=2)]),
    dict(mode='scan',variables=[dict(object=1,cell='Power',minimum=0,maximum=2)]),
    dict(mode='scan',variables=[dict(object=1,cell='Power',minimum=-1,maximum=2,scan_values=[0,1])]),
    dict(mode='scan',variables=[dict(object=1,cell='XPosition',minimum=2,maximum=1,scan_values=[1])]),
    dict(mode='scan',variables=[dict(object=1,cell='XPosition',minimum=0,maximum=1,scan_values=[2])]),
    dict(mode='scan',variables=[dict(object=1,cell='XPosition',minimum=0,maximum=1,scan_values=[1,1])]),
    dict(ranking='target_error'),dict(budget_seconds=float('inf')),
])
def test_request_rejections(change):
    with pytest.raises(ValidationError):NscEfficiency.model_validate(query(**change))


def test_discriminated_contract_and_scan_limit():
    q=RunAnalysis(request=query()).request
    assert isinstance(q,NscEfficiency)
    axes=[dict(object=1,cell=c,minimum=-1,maximum=1,scan_values=[-1,-.5,0,.5,1]) for c in ('XPosition','YPosition','ZPosition')]
    assert NscEfficiency.model_validate(query(mode='scan',variables=axes))
    axes[0]['scan_values']=[-1,-.5,0,.2,.5,1]
    with pytest.raises(ValidationError):NscEfficiency.model_validate(query(mode='scan',variables=axes))


def test_uniformity_includes_zeros_and_population_variance():
    r=roi_statistics([[1,0],[0,0]],1)
    assert r['power']==1 and r['efficiency']==1 and r['zero_count']==3
    assert r['cv']==pytest.approx(math.sqrt(3))
    assert r['hotspot_count']==1 and r['peak_to_mean']==4
    assert roi_statistics([[.25,.25],[.25,.25]],1)['cv']==0


@pytest.mark.parametrize('values,state',[
    ([[0,0]],'dark'),([[None,1]],'invalid_pixels'),([[float('nan'),1]],'invalid_pixels'),([[-1,1]],'invalid_pixels')])
def test_dark_and_invalid(values,state):
    r=roi_statistics(values,1)
    assert r['state']==state and r['cv'] is None
    if state=='invalid_pixels':assert r['efficiency'] is None


def test_ranking_and_no_source_power():
    r=roi_statistics([[1]],0)
    assert r['efficiency'] is None
    q=NscEfficiency.model_validate(query())
    assert score(dict(detectors=[r]),q) is None
    assert score(dict(detectors=[roi_statistics([[.5,.5]],1)]),q)==-1
    q.ranking='cv'
    assert score(dict(detectors=[roi_statistics([[.5,.5]],1)]),q)==0


def test_copy_closed_after_prepare_failure_and_source_unchanged():
    closed=[];system=S(NCE=S(NumberOfObjects=0),Close=lambda save:closed.append(save))
    b=S(system=S(CopySystem=lambda:system),_require_nsc=lambda:None,_require_work=lambda:None,
        _cancel_boundary=lambda task:None,requires_reconnect=False,_evaluation_error=lambda e:dict(message=str(e)))
    def composite(kind,settings,factory,require_sequential):
        assert require_sequential is False
        task={}
        with pytest.raises(ZemaxError) as exc:list(factory(task))
        assert exc.value.code=='INVALID_SOURCE'
        assert task['payload']['resources']['copy_closed']
    b._composite=composite
    run_nsc_efficiency(b,NscEfficiency.model_validate(query()))
    assert closed==[False]


def test_close_failure_keeps_original_error():
    def close(save):raise RuntimeError('owned close failure')
    system=S(NCE=S(NumberOfObjects=0),Close=close)
    b=S(system=S(CopySystem=lambda:system),_require_nsc=lambda:None,_require_work=lambda:None,
        _cancel_boundary=lambda task:None,requires_reconnect=False,_evaluation_error=lambda e:e.as_dict())
    def composite(kind,settings,factory,require_sequential):
        with pytest.raises(ZemaxError) as exc:list(factory({}))
        assert exc.value.code=='CLEANUP_FAILED'
        assert exc.value.details['operation_error']['code']=='INVALID_SOURCE'
        assert b.requires_reconnect
    b._composite=composite
    run_nsc_efficiency(b,NscEfficiency.model_validate(query()))
