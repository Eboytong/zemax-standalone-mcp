import pytest
from pydantic import ValidationError

from zemax_mcp.desensitization import DesignDesensitize,sensitivity_norm


def payload(**change):
    return dict(kind='design_desensitize',variables=[dict(surface=1,cell='radius',minimum=40,maximum=80)],
        merit=dict(wizard=dict(kind='sequential',optimize_for_manufacturing_yield=True)),threshold=.01,maximum_nominal=.001)|change


@pytest.mark.parametrize('change',[dict(seed=314159),dict(variables=[]),dict(threshold=0),dict(budget_seconds=float('inf')),
    dict(merit=dict(targets=[dict(kind='opd')])),dict(merit=dict(wizard=dict(kind='sequential',optimize_for_manufacturing_yield=False)))])
def test_request_contract(change):
    with pytest.raises(ValidationError):DesignDesensitize.model_validate(payload(**change))


def test_fixed_sensitivity_definition_and_registration():
    from zemax_mcp.analysis_models import RunAnalysis
    assert isinstance(RunAnalysis(request=payload()).request,DesignDesensitize)
    actual=sensitivity_norm(dict(summary=dict(sensitivity=[dict(nominal=.001,effects=[dict(minimum=-3,maximum=2),dict(minimum=4,maximum=-1)])])))
    assert actual['rss']==5 and actual['nominal']==.001
