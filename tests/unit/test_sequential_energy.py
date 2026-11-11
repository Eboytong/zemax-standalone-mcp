import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.sequential_energy import SequentialEnergyBudget,summarize_surface


def request(**changes):
    return dict(kind='sequential_energy_budget',rays=[dict(hx=0,hy=0,px=0,py=0)],first_surface=1)|changes


@pytest.mark.parametrize('payload',[request(rays=[]),request(rays=[dict(hx=0,hy=0,px=0,py=0,x=0)]),
    request(input_mode='Direct'),request(input_mode='Direct',rays=[dict(x=0,y=0,z=0,l=0,m=0,n=1)]),
    request(polarization=dict(jx=1,jy=1)),request(rays=[dict(hx=0,hy=0,px=0,py=0,weight=0)]),request(input_power_w=0)])
def test_invalid_contract(payload):
    with pytest.raises(ValidationError):SequentialEnergyBudget.model_validate(payload)


def test_dispatch_union_and_weighted_surface_accounting():
    parsed=RunAnalysis(request=request(input_power_w=2)).request
    assert isinstance(parsed,SequentialEnergyBudget)
    rows=[dict(state='succeeded',intensity=.9),dict(state='vignetted',intensity=.8),dict(state='error',intensity=None)]
    data=summarize_surface(2,rows,[1,2,1],4,4)
    assert data['succeeded']==1 and data['vignetted']==1 and data['error']==1
    assert data['weighted_intensity_out']==pytest.approx(.9)
    assert data['cumulative_throughput']==pytest.approx(.225)
    assert data['surface_retention']==pytest.approx(.225)
