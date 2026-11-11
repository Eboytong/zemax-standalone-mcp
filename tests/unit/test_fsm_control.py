import pytest
from pydantic import ValidationError
from zemax_mcp.fsm_control import FsmControl,simulate,response_inverse
from zemax_mcp.errors import ZemaxError


I=[[float(i==j) for j in range(4)] for i in range(4)]


def request(**changes):
    return FsmControl(**(dict(kind='fsm_control',start_surface=1,
        mirrors=[dict(tilt_surface=2,mirror_surface=3,return_surface=4),dict(tilt_surface=5,mirror_surface=6,return_surface=7)],
        observation_surfaces=[8,9],disturbances=[[.02,-.01,.001,-.002]]*20,sample_period_seconds=.001)|changes))


def test_zero_delay_closed_form():
    q=request();rows,summary=simulate(I,I,q)
    for k,row in enumerate(rows):
        assert row['residual']==pytest.approx([v*.5**k for v in q.disturbances[k]],abs=1e-14)
    assert summary['converged'] and summary['settling_time_seconds']==pytest.approx(.011)


def test_delay_saturation_lag_and_noise():
    rows,s=simulate(I,I,request(limits_deg=[.001]*4,delay_samples=2,actuator_time_constant_seconds=.002))
    assert s['saturated_samples'] and not s['converged']
    assert rows[0]['next_command_angles_deg']==[0]*4 and 0<s['actuator_discrete_alpha']<1
    q=request(measurement_noise_std=[1e-6]*4,seed=17)
    assert simulate(I,I,q)==simulate(I,I,q)
    assert simulate(I,I,q)[0][0]['measurement']!=q.disturbances[0]


@pytest.mark.parametrize('changes',[dict(observation_surfaces=[9,8]),dict(gain=0),dict(sample_period_seconds=0),
    dict(disturbances=[[0,0]]*2),dict(limits_deg=[0]*4),dict(delay_samples=-1)])
def test_invalid_control_requests(changes):
    with pytest.raises(ValidationError):request(**changes)


def test_observability_and_condition():
    with pytest.raises(ZemaxError,match='秩不足'):response_inverse([[0.]*4 for _ in range(4)],1e8)
    a=[r[:] for r in I];a[0][0]=1e-10
    with pytest.raises(ZemaxError,match='条件数'):response_inverse(a,1e8)


def test_typed_dispatch():
    from zemax_mcp.models import RunAnalysis
    assert RunAnalysis(request=request().model_dump()).request.kind=='fsm_control'
