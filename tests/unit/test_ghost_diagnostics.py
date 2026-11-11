import pytest
from pydantic import ValidationError

from zemax_mcp.ghost_diagnostics import GhostDiagnostics,ancestry,classify_arrivals
from zemax_mcp.errors import ZemaxError


def query(**changes):
    return dict(kind='ghost_diagnostics',detector=3,expected_paths=[[dict(object=2,face=1),dict(object=2,face=2),dict(object=3)]])|changes


@pytest.mark.parametrize('change',[
    dict(expected_paths=[]),dict(expected_paths=[[dict(object=2)]]),dict(max_segments=0),dict(max_paths=0),
    dict(minimum_relative_power=2),dict(trace_budget_seconds=0),dict(rays_per_source=0),
    dict(minimum_expected_fraction=-1),dict(minimum_expected_fraction=1.1),
    dict(candidates=[dict(name='a',changes=[dict(object=2,x=float('nan'))])]),
    dict(candidates=[dict(name='a',changes=[dict(object=2)])]),
    dict(candidates=[dict(name='a',changes=[dict(object=2,coating='AR')])]),
    dict(candidates=[dict(name='a',changes=[dict(object=2,face=1)])]),
])
def test_request_rejections(change):
    with pytest.raises(ValidationError):GhostDiagnostics.model_validate(query(**change))


def segment(index,parent,obj,face,power,n=1):
    return dict(ray_index=0,segment_index=index,SegmentParent=parent,HitObject=obj,HitFace=face,Intensity=power,
        XNorm=0,YNorm=0,ZNorm=1,L=0,M=0,N=n,WlUM=.55,X=0,Y=0,Z=0)


def slab():
    return [segment(0,0,0,0,1),segment(1,0,2,1,1),segment(2,1,2,2,.95),segment(3,2,3,0,.9),
        segment(4,2,2,1,.05,-1),segment(5,4,2,2,.002),segment(6,5,3,0,.0018)]


def test_parent_tree_power_reflection_pairs_and_precision_residual():
    result=classify_arrivals(slab(),GhostDiagnostics.model_validate(query()),.901800001)
    assert result['power']['expected']==.9 and result['power']['ghost']==.0018
    assert result['power']['unread_or_precision_residual']==pytest.approx(1e-9)
    ghost=next(r for r in result['paths'] if r['category']=='ghost')
    assert ghost['reflection_faces']==[dict(object=2,face=2),dict(object=2,face=1)]
    assert ghost['arrivals']==1


def test_limits_filter_and_missing_parents_keep_unclassified_power():
    q=GhostDiagnostics.model_validate(query(max_paths=1))
    result=classify_arrivals(slab(),q,1)
    assert result['power']['retained']==.9 and result['power']['excluded']==.0018
    assert result['power']['unclassified']==pytest.approx(.1)
    result=classify_arrivals([slab()[-1]],q,1)
    assert result['power']['ancestry_unclassified']==.0018 and result['ancestry_errors']
    with pytest.raises(ZemaxError):ancestry({1:segment(1,1,2,1,1)},1)


def test_scattering_interaction_attribution():
    rows=slab();rows[4]['SegScattered']=True
    result=classify_arrivals(rows,GhostDiagnostics.model_validate(query()),1)
    assert result['power']['scatter_related']==.0018 and result['power']['ghost']==0


def test_native_ray_error_is_kept_in_unclassified_power():
    rows=slab();rows[4]['RayError']=True
    result=classify_arrivals(rows,GhostDiagnostics.model_validate(query()),1)
    assert result['power']['ghost']==0 and result['power']['ancestry_unclassified']==.0018
    assert result['ancestry_errors'][0]['error']=='native RayError in ancestry'


def test_final_update_rejection_is_reported():
    from types import SimpleNamespace as NS
    from zemax_mcp.ghost_diagnostics import apply_changes,GhostCandidate
    row=NS(XPosition=0,GetObjectCell=lambda _:object())
    system=NS(NCE=NS(NumberOfObjects=2,GetObjectAt=lambda _:row),UpdateStatus=lambda:setattr(row,'XPosition',0))
    b=NS(native=NS(enum=lambda *args:0,api=NS(Editors=NS(NCE=NS(ObjectColumn=object())))),_guard_nsc_cell=lambda *args:None)
    with pytest.raises(ZemaxError) as error:apply_changes(b,system,GhostCandidate(name='pose',changes=[dict(object=2,x=1)]))
    assert error.value.code=='SETTING_REJECTED'
