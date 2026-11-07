from types import SimpleNamespace as N
import pytest
from zemax_mcp.models import COMMAND_MODELS
from test_optimizer_diagnostics import diagnostic_backend


def test_local_optimizer_uses_native_contract_without_prior_registration(tmp_path):
    b,_=diagnostic_backend(tmp_path)
    native=N(MaxCores=2,Algorithm='DampedLeastSquares',Cycles='Fixed_5_Cycles',NumberOfCores=1)
    b.system.Tools=N(OpenLocalOptimization=lambda:native)
    b.native.set_enum=lambda obj,key,value:setattr(obj,key,value)
    launches=[]
    b._start_task=lambda kind,tool,settings,before:launches.append((kind,tool,settings,before)) or {'task_id':'local'}
    result=b.run_local_optimization(COMMAND_MODELS['run_local_optimization']())
    assert result['task_id']=='local'
    assert launches[0][0]=='local_optimization'
    assert launches[0][2]['cycles']=='Fixed_5_Cycles'
    assert not hasattr(b,'_engineering_policy')


@pytest.mark.parametrize('command,hammer',[('run_global_optimization',False),('run_hammer_optimization',True)])
def test_global_entry_uses_native_search_flow(tmp_path,command,hammer):
    b,_=diagnostic_backend(tmp_path)
    calls=[]
    b._global_search=lambda request,mode:calls.append(mode)or{'task_id':'search'}
    assert getattr(b,command)(COMMAND_MODELS[command](runtime_seconds=1))['task_id']=='search'
    assert calls==[hammer]


def test_explicit_merit_update_does_not_append_other_operands(tmp_path):
    from test_merit_edit_safety import setup,Row
    b,mfe=setup(tmp_path,[Row('EFFL')])
    result=b.update_merit_function(COMMAND_MODELS['update_merit_function'](mode='append',operands=[]))
    assert mfe.NumberOfOperands==1
    assert result['operands'][0]['type']=='EFFL'


def test_native_optimization_collection_does_not_run_geometry_or_restore(tmp_path):
    b,_=diagnostic_backend(tmp_path)
    b._check_geometry_now=lambda:pytest.fail('Geometry must be an explicit diagnostic request')
    b._restore_model=lambda *args:pytest.fail('No implicit geometry rollback')
    b._close_task_native=lambda task:True
    b.system.MFE.CalculateMeritFunction=lambda:2.0
    result=b._collect(dict(kind='local_optimization',analysis=False,before={'merit_function':3.0},native=N(Succeeded=True,CurrentMeritFunction=2.0)))
    assert result['after']['merit_function']==2.0
    assert 'candidate_accepted'not in result
    assert 'geometry'not in result
