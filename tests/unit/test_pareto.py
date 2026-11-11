import pytest
from pydantic import ValidationError
from zemax_mcp.pareto import ParetoSettings,rank_candidates


def request(**changes):
    return ParetoSettings(**(dict(objectives=[dict(operand=1,target=0,scale=1,name='a'),dict(operand=2,target=1,scale=2,name='b')],weight_grid=[[1,1],[2,1]])|changes))


@pytest.mark.parametrize('changes',[
    dict(weight_grid=[[1],[2,1]]),dict(weight_grid=[[1,0],[1,1]]),dict(weight_grid=[[1,float('inf')],[1,1]]),
    dict(objectives=[dict(operand=1,target=0,scale=1,name='a')]*2),
    dict(budget_seconds=0),
    dict(objectives=[dict(operand=1,target=0,scale=1e-300,name='a'),dict(operand=2,target=1,scale=1,name='b')]),
])
def test_invalid_pareto_contract(changes):
    with pytest.raises(ValidationError):request(**changes)


def test_pareto_constraints_dominance_and_duplicates():
    rows=[dict(index=i,state='succeeded',feasible=i!=4,normalized_errors=v) for i,v in enumerate([[0,2],[1,1],[2,0],[2,2],[0,0],[1,1]])]
    rows.append(dict(index=6,state='failed'))
    assert rank_candidates(rows)==[0,1,2,5]
    assert rows[3]['dominated_by']==[0,1,2,5]
    assert not rows[4]['pareto_optimal'] and not rows[6]['pareto_optimal']


def test_scaled_merit_weights_and_typed_multistart():
    from zemax_mcp.models import Multistart
    q=Multistart(starts=[[dict(surface=1,radius=50)]],evaluation=dict(merit=True),pareto=request())
    assert q.pareto.objectives[1].scale==2
