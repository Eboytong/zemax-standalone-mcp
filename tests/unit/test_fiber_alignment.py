import math
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.fiber_alignment import FiberAlignment, loss_crossings, pose_settings, refined, run_fiber_alignment
from zemax_mcp.pop_models import Pop


def request(**patch):
    return dict(kind='fiber_alignment',settings=dict(fiber_type='AstigmaticGaussian',
        fiber_parameters={0:.1,1:.2}),axes=[dict(axis='x',values=[-.2,0,.2])],save_best=False)|patch


@pytest.mark.parametrize('patch',[
    dict(settings=dict(fiber_type='GaussianWaist')),dict(axes=[]),
    dict(axes=[dict(axis='x',values=[0,0])]),dict(axes=[dict(axis='x',values=[1,0])]),
    dict(axes=[dict(axis='x',values=[0,float('nan')])]),dict(max_evaluations=2),
    dict(axes=[dict(axis='x',values=[0,1]),dict(axis='x',values=[0,1])]),
    dict(optimization=dict(bounds=[dict(axis='z',minimum=1,maximum=1)])),
    dict(settings=dict(fiber_type='AstigmaticGaussian',fiber_parameters={0:.1,1:.1},save_output_beam=False)),
    dict(settings=dict(fiber_type='AstigmaticGaussian',fiber_parameters={0:.1,1:.1,6:0})),
    dict(axes=[dict(axis='tilt_x',values=[0,90])]),
])
def test_contract(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=request(**patch))


def test_pose_updates_all_requested_components_without_changing_input():
    pop=Pop(fiber_type='AstigmaticGaussian',fiber_parameters={0:.1,1:.2,2:3,3:4,4:.3,5:.4},
            fiber_tilt_x=1,fiber_tilt_y=2)
    result=pose_settings(pop,dict(x=.1,y=-.2,z=5,tilt_x=.5,tilt_y=-.5))
    assert result.fiber_parameters=={0:.1,1:.2,2:8,3:9,4:.4,5:.2}
    assert result.fiber_tilt_x==1.5 and result.fiber_tilt_y==1.5
    assert pop.fiber_parameters[2]==3


def test_crossing_refinement_gaussian_and_missing_sides():
    values=[i*.01 for i in range(-15,16)]
    efficiency=[math.exp(-(x/.1)**2) for x in values]
    for db in (1,3):
        result=loss_crossings(values,efficiency,1,0,db)
        half=.1*math.sqrt(db*math.log(10)/10)
        assert result['state']=='bracketed'
        assert result['left']==pytest.approx(-half,abs=.0003)
        assert result['right']==pytest.approx(half,abs=.0003)
    assert loss_crossings([0,.01],[1,.99],1,0,3)['state']=='range_not_bracketing'
    assert loss_crossings([0,1],[0,0],0,0,3)['state']=='zero_peak'
    assert refined([0,1,2])==[0,.5,1,1.5,2]


def fake_backend(target=.027):
    poses=[]
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,context=lambda:dict(model_revision=4),
         system=NS(SystemData=NS(Units=NS(LensUnits='Millimeters'))))
    b._cancel_boundary=lambda _:None
    b._evaluation_error=lambda e:dict(message=str(e))
    b.run_pop=lambda q:None
    def child(task,method,q):
        p=q.fiber_parameters
        x,y=p.get(4,0),p.get(5,0)
        value=math.exp(-((x-target)/.1)**2-(y/.1)**2)
        poses.append(dict(x=x,y=y))
        yield
        return dict(metrics=dict(receiver_efficiency=value),task=dict(task_id=str(len(poses)),
            settings=q.model_dump(),close_attempted=True))
    b._child_job=child
    def composite(kind,settings,factory):
        task=dict(rows=[],cancel_requested=False)
        for _ in factory(task):pass
        return task
    b._composite=composite
    return b,poses


def test_scan_search_tolerances_and_cache():
    b,poses=fake_backend()
    q=FiberAlignment(**request(axes=[dict(axis='x',values=[-.2,0,.2])],
        tolerance_axes=[dict(axis='x',values=[i*.01 for i in range(-20,21)])],
        optimization=dict(bounds=[dict(axis='x',minimum=-.1,maximum=.1)],max_iterations=40),
        max_evaluations=150))
    result=run_fiber_alignment(b,q)
    assert result['summary']['best']['pose']['x']==pytest.approx(.027,abs=.0003)
    assert result['summary']['best']['value']>.99999
    assert result['payload']['search']['state']=='step_tolerance'
    assert all(x['state']=='bracketed' for x in result['payload']['tolerances'][0]['crossings'])
    assert result['restoration']['restored']
    assert len(poses)==len({p['x'] for p in poses})


def test_two_dimensional_grid_is_y_x_and_budget_retains_results():
    b,poses=fake_backend(target=0)
    q=FiberAlignment(**request(axes=[dict(axis='x',values=[-.1,0,.1]),
        dict(axis='y',values=[-.2,0,.2])],refine=False,max_evaluations=9))
    result=run_fiber_alignment(b,q)
    grid=result['payload']['grids'][0]
    assert grid['nx']==grid['ny']==3 and grid['values'][1][1]==1
    assert grid['values'][0][1]==pytest.approx(math.exp(-4))
    assert result['summary']['evaluations']==9


def test_cancellation_and_child_failure_preserve_original_details():
    b,_=fake_backend()
    def fail(_):raise RuntimeError('cancel boundary')
    b._cancel_boundary=fail
    with pytest.raises(RuntimeError,match='cancel boundary'):
        run_fiber_alignment(b,FiberAlignment(**request()))
    b,_=fake_backend()
    def child(*args):
        yield
        raise RuntimeError('original native failure')
    b._child_job=child
    with pytest.raises(RuntimeError,match='original native failure'):
        run_fiber_alignment(b,FiberAlignment(**request()))
