import pytest
from pydantic import ValidationError
from zemax_mcp.tolerance_budget import ToleranceBudget, allocation_cost, wilson


def request(**changes):
    return ToleranceBudget(**(dict(kind='tolerance_budget',processes=[dict(operand=1,name='image spacing',unit='mm',
        minimum_half_width=.01,maximum_half_width=.2,reference_half_width=.01,variable_cost=100)],
        allocations=[[.01],[.05],[.2]],currency='CNY',costing_unit='piece',criterion_unit='mm',threshold=.001,
        target_yield=.8,screening_samples=32,validation_samples=64)|changes))


def test_known_cost_and_wilson():
    q=request()
    assert [allocation_cost(a,q.processes)['total'] for a in q.allocations]==pytest.approx([100,20,5])
    assert wilson(32,32,.95)['lower']==pytest.approx(.8928208017449294)
    assert wilson(0,32,.95)['upper']==pytest.approx(.1071791982550706)
    assert wilson(16,32,.95)['estimate']==.5
    with pytest.raises(ValueError):wilson(33,32,.95)


@pytest.mark.parametrize('changes',[dict(allocations=[[.01],[.3]]),dict(allocations=[[.01],[.01]]),
    dict(allocations=[[.01,.02],[.05,.03]]),dict(seed=314159),dict(target_yield=1),dict(confidence=1),
    dict(screening_samples=1),dict(save_validation_samples=65),dict(threshold=float('nan'))])
def test_bad_request(changes):
    with pytest.raises(ValidationError):request(**changes)


def test_typed_dispatch():
    from zemax_mcp.models import RunAnalysis
    assert RunAnalysis(request=request().model_dump()).request.kind=='tolerance_budget'
