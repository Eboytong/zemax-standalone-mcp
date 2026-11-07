from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.hpc_models import HpcSettingsQuery
from zemax_mcp.hpc import prepare_hpc, open_execution_tool, close_failed_setup
from zemax_mcp.errors import ZemaxError


class Enum:
    def __init__(self,name): self.name=name
    def __str__(self): return self.name
    def Equals(self,other): return isinstance(other,Enum) and self.name==other.name


def settings(configured=True,nodes=2,instance='Small'):
    return N(IsHPCConfigured=configured,NodeCount=nodes,MaxNodeCount=8,InstanceType=Enum(instance),
             ThreadsPerTask=4,ShutdownTimeTicks=123)


def backend(cfg=None):
    cfg=cfg or settings();calls=[]
    tools=N(GetHPCSettingsFromPrefs=lambda:calls.append('preferences') or cfg,
            GetHPCSettingsCustom=lambda count,kind:calls.append((count,str(kind))) or cfg)
    return N(system=N(Tools=tools),native=N(api=N(Tools=N(HPCNodeSize=None)),enum=lambda _,name:Enum(name)),
             calls=calls,requires_reconnect=False)


@pytest.mark.parametrize('payload',[
    {},{'mode':'automatic'},{'mode':'preferences','node_count':2},
    {'mode':'custom','node_count':0},{'mode':'custom','node_count':True},
    {'mode':'custom','node_count':2147483648},
    {'mode':'custom','node_count':2,'instance_type':'Huge'},
    {'mode':'custom','node_count':2,'threads_per_task':8},
])
def test_hpc_type_specific_conditions(payload):
    with pytest.raises(ValidationError): HpcSettingsQuery(request=payload)


@pytest.mark.parametrize('command,args',[
    ('run_nsc_ray_trace',{}),('run_tolerance_analysis',{'mode':'monte_carlo'}),
    ('run_global_optimization',{'runtime_seconds':1}),('run_hammer_optimization',{'runtime_seconds':1}),
])
def test_hpc_nested_requests_survive_worker_validation(command,args):
    model=COMMAND_MODELS[command]
    q=model(**args,hpc={'mode':'custom','node_count':2,'instance_type':'Small'})
    assert model.model_validate(q.model_dump())==q
    assert q.hpc.node_count==2
    assert model(**args).hpc is None


def test_hpc_preferences_unconfigured_query_does_not_claim_job_ready():
    b=backend(settings(configured=False))
    selection=HpcSettingsQuery(request={'mode':'preferences'}).request
    result=prepare_hpc(b,selection,require_configured=False)
    assert result['actual']['is_configured'] is False
    with pytest.raises(ZemaxError) as exc: prepare_hpc(b,selection)
    assert exc.value.code=='HPC_NOT_CONFIGURED'
    assert exc.value.details['actual']['threads_per_task']==4


def test_hpc_custom_readback_and_default_instance_resolution():
    b=backend()
    selection=HpcSettingsQuery(request={'mode':'custom','node_count':2,'instance_type':'Small'}).request
    result=prepare_hpc(b,selection)
    assert b.calls==[(2,'Small')] and result['actual']['instance_type']=='Small'
    default=HpcSettingsQuery(request={'mode':'custom','node_count':2}).request
    assert prepare_hpc(b,default)['actual']['default_instance_resolved']
    b.system.Tools.GetHPCSettingsCustom=lambda *_:settings(nodes=1)
    with pytest.raises(ZemaxError) as exc: prepare_hpc(b,selection)
    assert exc.value.code=='SETTING_REJECTED'


def test_hpc_custom_instance_rejection_and_factory_error():
    b=backend(settings(instance='Large'))
    selection=HpcSettingsQuery(request={'mode':'custom','node_count':2,'instance_type':'Small'}).request
    with pytest.raises(ZemaxError) as exc: prepare_hpc(b,selection)
    assert exc.value.code=='SETTING_REJECTED'
    b.system.Tools.GetHPCSettingsCustom=lambda *_:(_ for _ in ()).throw(RuntimeError('node service error'))
    with pytest.raises(ZemaxError) as exc: prepare_hpc(b,selection)
    assert exc.value.code=='HPC_SETTINGS_ERROR' and 'node service error' in str(exc.value)


def test_hpc_default_instance_still_unresolved_is_reported_as_such():
    b=backend(settings(instance='Default'))
    selection=HpcSettingsQuery(request={'mode':'custom','node_count':2}).request
    actual=prepare_hpc(b,selection)['actual']
    assert actual['instance_type']=='Default' and actual['default_instance_resolved'] is False


@pytest.mark.parametrize('method',['OpenNSCRayTrace','OpenTolerancing','OpenGlobalOptimization','OpenHammerOptimization'])
def test_hpc_factory_uses_exact_selected_configuration_and_preserves_local_factory(method):
    b=backend();cfg=prepare_hpc(b,HpcSettingsQuery(request={'mode':'preferences'}).request)
    tool=object();seen=[]
    setattr(b.system.Tools,method,lambda:seen.append('local') or tool)
    setattr(b.system.Tools,method+'_HPC',lambda setting:seen.append(setting) or tool)
    assert open_execution_tool(b,method,cfg) is tool and seen==[cfg['native']]
    assert open_execution_tool(b,method,None) is tool and seen[-1]=='local'
    delattr(b.system.Tools,method+'_HPC')
    with pytest.raises(ZemaxError) as exc:open_execution_tool(b,method,cfg)
    assert exc.value.code=='UNSUPPORTED_INTERFACE'


def test_hpc_setup_cleanup_failure_keeps_original_error():
    b=backend()
    b._release_owned=lambda tool:(_ for _ in ()).throw(ZemaxError('CLEANUP_FAILED','close failed'))
    with pytest.raises(ZemaxError) as exc:
        close_failed_setup(b,object(),ZemaxError('SETTING_REJECTED','native setting refused',setting='Algorithm'))
    assert exc.value.code=='SETTING_REJECTED'
    assert exc.value.details['cleanup_error']['code']=='CLEANUP_FAILED' and b.requires_reconnect


def test_hpc_factory_null_and_native_error_do_not_fall_back():
    b=backend();cfg=prepare_hpc(b,HpcSettingsQuery(request={'mode':'preferences'}).request)
    b.system.Tools.OpenNSCRayTrace=lambda:pytest.fail('HPC must not silently switch to local')
    b.system.Tools.OpenNSCRayTrace_HPC=lambda _:None
    with pytest.raises(ZemaxError) as exc:open_execution_tool(b,'OpenNSCRayTrace',cfg)
    assert exc.value.code=='HPC_TOOL_UNAVAILABLE'
    b.system.Tools.OpenNSCRayTrace_HPC=lambda _:(_ for _ in ()).throw(RuntimeError('native node failure'))
    with pytest.raises(ZemaxError) as exc:open_execution_tool(b,'OpenNSCRayTrace',cfg)
    assert exc.value.code=='HPC_TOOL_ERROR' and 'native node failure' in str(exc.value)
