import pytest
from pydantic import ValidationError
from zemax_mcp.thermal_compensation import ThermalCompensation


def request(**changes):
    return ThermalCompensation(**(dict(kind='thermal_compensation',configurations=[1,2,3],
        compensation_surface=2,minimum_gap=40,maximum_gap=60)|changes))


@pytest.mark.parametrize('changes',[
    dict(configurations=[1,1]),dict(reference_configuration=4),
    dict(minimum_gap=60),dict(maximum_gap=float('inf')),
    dict(compensation_surface=0),dict(configurations=[1]),
    dict(budget_seconds=0),dict(configurations=[True,2]),
])
def test_invalid_thermal_requests(changes):
    with pytest.raises(ValidationError):request(**changes)


def test_explicit_compensation_dependency_permission():
    assert request().replace_compensation_solves is False
    assert request(replace_compensation_solves=True).replace_compensation_solves


def test_dispatch_contract():
    from zemax_mcp.models import RunAnalysis
    assert RunAnalysis(request=request().model_dump()).request.kind=='thermal_compensation'
