import math
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.coating_optimization import (CoatingObjective, boundary_report, compare_objectives,
                                           objective_value, run_coating_optimization)
from zemax_mcp.errors import ZemaxError
from zemax_mcp import coating_optimization as co


def request(**patch):
    return dict(kind='coating_optimization',surface=1,
        variables=[dict(layer=1,minimum=.2,maximum=2)],
        objectives=[dict(wavelength_um=.55,angle_deg=30,direction='outward',polarization='p')])|patch


@pytest.mark.parametrize('patch',[
    dict(surface=0),dict(variables=[]),dict(objectives=[]),dict(algorithm='custom'),
    dict(variables=[dict(layer=1,minimum=0,maximum=2)]),
    dict(variables=[dict(layer=1,minimum=2,maximum=2)]),
    dict(variables=[dict(layer=1,minimum=1,maximum=11)]),
    dict(variables=[dict(layer=1,minimum=.2,maximum=2)]*2),
    dict(objectives=[dict(wavelength=1,wavelength_um=.55)]),
    dict(objectives=[dict(angle_deg=90)]),dict(objectives=[dict(polarization='unpolarized')]),
    dict(objectives=[dict(weight=0)]),dict(objectives=[dict(target=1.1)]),
    dict(objectives=[dict(wavelength_um=float('inf'))]),dict(budget_seconds=-1),
])
def test_typed_contract_rejects_ambiguous_or_invalid_requests(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=request(**patch))


def test_contract_roundtrip_and_objective_definition():
    q=RunAnalysis(request=request()).request
    assert RunAnalysis.model_validate(dict(request=q.model_dump(exclude_none=True))).request==q
    o=[CoatingObjective(metric='reflection',polarization='s',target=.1,weight=3),
       CoatingObjective(metric='transmission',polarization='p',target=.8,weight=1)]
    result=objective_value([dict(reflection=dict(s=.2)),dict(transmission=dict(p=.6))],o)
    assert result['weighted_mean_squared_error']==pytest.approx(.0175)
    assert result['weighted_rms_error']==pytest.approx(math.sqrt(.0175))
    with pytest.raises(ZemaxError):objective_value([],o)
    with pytest.raises(ZemaxError):objective_value([dict(reflection=dict(s=math.nan))],o[:1])


def test_final_bounds_are_hard_acceptance_conditions():
    q=RunAnalysis(request=request()).request
    assert boundary_report([dict(layer=1,thickness_multiplier=2.)],q.variables)[0]['satisfied']
    assert not boundary_report([dict(layer=1,thickness_multiplier=2.00000001)],q.variables)[0]['satisfied']


def test_mapping_requires_matching_finite_native_values():
    mfe=NS(CalculateMeritFunction=lambda:.01,GetOperandAt=lambda i:NS(Value={1:.2,2:.3}[i]))
    result=compare_objectives(NS(MFE=mfe),[1,2],[.2,.3])
    assert result['max_absolute_error']==0
    for values in ([.2,.5],[.2]):
        with pytest.raises(ZemaxError,match='CODA'):compare_objectives(NS(MFE=mfe),[1,2],values)
    mfe.GetOperandAt=lambda i:NS(Value=math.nan)
    with pytest.raises(ZemaxError):compare_objectives(NS(MFE=mfe),[1],[.2])


@pytest.mark.parametrize('layers,enabled,code',[
    ([],True,'INVALID_ARGUMENT'),
    ([dict(layer=1,thickness_multiplier=1,thickness_status=dict(mode='Pickup'))],True,'SOLVE_PROTECTED'),
    ([dict(layer=1,thickness_multiplier=3,thickness_status=dict(mode='Fixed'))],True,'INVALID_ARGUMENT'),
    ([dict(layer=1,thickness_multiplier=1,thickness_status=dict(mode='Fixed'))],False,'INACTIVE_SETTING'),
    ([dict(layer=2,thickness_multiplier=1,thickness_status=dict(mode='Fixed'))],True,'INDEX_OUT_OF_RANGE'),
])
def test_preflight_rejects_before_allocating_native_system(layers,enabled,code):
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,
         get_coating_layers=lambda q:dict(total=len(layers),rows=layers,use_layer_multiplier_and_offsets=enabled))
    with pytest.raises(ZemaxError) as e:run_coating_optimization(b,RunAnalysis(request=request()).request)
    assert e.value.code==code


@pytest.mark.parametrize('close_ok',[True,False])
def test_setup_failure_closes_owned_copy_and_preserves_original_error(monkeypatch,close_ok):
    closed=[];tasks=[]
    bench=NS(Close=lambda save:closed.append(save) or close_ok)
    state=dict(layer=1,thickness_multiplier=1,thickness_status=dict(mode='Fixed'))
    sample=dict(wavelength_um=.55,angle_deg=30,direction='outward',reflection=dict(s=.1,p=.05))
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,
        get_coating_layers=lambda q:dict(total=1,rows=[state],use_layer_multiplier_and_offsets=True),
        get_coating_rta=lambda q:dict(samples=[sample]),context=lambda:dict(model_revision=7),
        system=NS(CopySystem=lambda:bench),_cancel_boundary=lambda task:None,
        _evaluation_error=lambda e:dict(message=str(e)),requires_reconnect=False)
    def composite(kind,settings,factory):
        task=dict(rows=[]);tasks.append(task)
        list(factory(task))
    b._composite=composite
    def reject(*args):raise RuntimeError('original setting error')
    monkeypatch.setattr(co,'build_bench',reject)
    with pytest.raises(Exception) as e:run_coating_optimization(b,RunAnalysis(request=request()).request)
    assert closed==[False] and tasks[0]['restoration']['restored']
    if close_ok:
        assert str(e.value)=='original setting error' and not b.requires_reconnect
    else:
        assert e.value.code=='CLEANUP_FAILED' and b.requires_reconnect
        assert e.value.details['operation_error']['message']=='original setting error'
