from types import SimpleNamespace as N
import pytest
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.configurations import ConfigurationsMixin
from zemax_mcp.tolerancing import TolerancingMixin
from zemax_mcp.nonsequential import NonSequentialMixin
from zemax_mcp.errors import ZemaxError
from test_hpc import Enum, settings


class SetupComplete(Exception): pass


class Tool:
    def __init__(self):
        self.MaxCores=8; self.Filter=''; self.reject=None; self.events=[]
    def __setattr__(self,name,value):
        if name==getattr(self,'reject',None): return
        object.__setattr__(self,name,value)
    def GetType(self):
        return N(GetProperty=lambda name:N(PropertyType=N(IsEnum=isinstance(getattr(self,name),Enum))))
    def ClearDetectors(self,index): self.events.append('clear'); return 'Success'
    def SetRandomSeed(self,value): self.events.append(('seed',value))
    def ResetRandomSeed(self): self.events.append('seed_reset')


class Backend(ConfigurationsMixin,TolerancingMixin,NonSequentialMixin):
    def __init__(self,path):
        self.directory=path; self.work_path=path/'work.zos'; self.source_path=None
        self.requires_reconnect=False; self.revision=0; self.system_context={}; self.detector_history=[]
        self.events=[]; self.launch=None; self.tool=Tool(); self.cfg=settings()
        tools=N(GetHPCSettingsFromPrefs=lambda:self.cfg)
        for name in ['OpenNSCRayTrace','OpenTolerancing','OpenGlobalOptimization','OpenHammerOptimization']:
            setattr(tools,name,lambda name=name:self.open(name,None))
            setattr(tools,name+'_HPC',lambda cfg,name=name:self.open(name+'_HPC',cfg))
        self.system=N(Tools=tools,NCE=N(NumberOfObjects=0))
        self.native=N(api=N(Tools=N(HPCNodeSize=None,Tolerancing=N(Criterions=None,CriterionComps=None))),
                      enum=lambda typ,value:Enum(value),set_enum=lambda obj,name,value:setattr(obj,name,Enum(value)))
    def open(self,name,cfg): self.events.append((name,cfg)); return self.tool
    def _require_sequential(self,**kwargs): pass
    def _require_nsc(self): pass
    def _require_work(self): pass
    def _optimization_preflight(self): return {}
    def _mutate(self,label): self.revision+=1; self.events.append('mutate')
    def _checkpoint(self,label): self.events.append('checkpoint'); return 'checkpoint.zos'
    def context(self): return {'model_revision':self.revision}
    def evaluate_merit_function(self,req): return {'merit_function':1.}
    def get_tolerances(self,req): return {'rows':[],'next_start':None}
    def get_external_dependencies(self,req): return {'rows':[],'next_start':None}
    def _clear_detector_records(self): self.events.append('detector_records_cleared')
    def _composite(self,kind,settings,factory):
        self.parent=dict(task_id='parent',cancel_requested=False,rows=[])
        self.flow=factory(self.parent); return self.parent
    def _child_job(self,parent,launch,req):
        launch(req)
        raise SetupComplete()
        yield
    def _start_task(self,kind,tool,settings,**kwargs):
        self.launch=dict(kind=kind,tool=tool,settings=settings,**kwargs)
        return dict(task_id='native',state='running')
    def _restore_model(self,*args): self.events.append('restore')
    def _release_owned(self,tool): self.events.append('close'); assert tool is self.tool


@pytest.fixture
def execution(tmp_path,monkeypatch):
    import zemax_mcp.nonsequential as nsc
    import zemax_mcp.configurations as opt
    import zemax_mcp.tolerancing as tol
    for module in (nsc,opt,tol):monkeypatch.setattr(module,'scalar_settings',lambda obj:{})
    return Backend(tmp_path)


CASES=[('run_nsc_ray_trace',{},'OpenNSCRayTrace_HPC'),
       ('run_tolerance_analysis',{'mode':'monte_carlo'},'OpenTolerancing_HPC'),
       ('run_global_optimization',{'runtime_seconds':2},'OpenGlobalOptimization_HPC'),
       ('run_hammer_optimization',{'runtime_seconds':2},'OpenHammerOptimization_HPC')]


@pytest.mark.parametrize('command,args,factory',CASES)
def test_hpc_entry_uses_existing_task_with_adopted_configuration(execution,command,args,factory):
    b=execution
    q=COMMAND_MODELS[command](**args,hpc={'mode':'preferences'})
    getattr(b,command)(q)
    if command!='run_nsc_ray_trace':
        with pytest.raises(SetupComplete): list(b.flow)
    assert (factory,b.cfg) in b.events
    assert b.launch['tool'] is b.tool
    assert b.launch['settings']['hpc']['node_count']==2
    if 'optimization' in command:assert b.launch['budget_seconds']==2
    if command=='run_nsc_ray_trace':
        assert b.launch['settings']['trace_options']['hpc']['source']=='GetHPCSettingsFromPrefs'
        assert b.tool.events[-1]=='clear'
    b._release_owned(b.tool)
    assert b.events[-1]=='close'


@pytest.mark.parametrize('command,args,factory',CASES)
def test_hpc_unconfigured_preflight_preserves_model_and_detectors(execution,command,args,factory):
    b=execution;b.cfg.IsHPCConfigured=False
    with pytest.raises(ZemaxError) as exc:
        getattr(b,command)(COMMAND_MODELS[command](**args,hpc={'mode':'preferences'}))
    assert exc.value.code=='HPC_NOT_CONFIGURED'
    assert b.revision==0 and b.events==[] and b.tool.events==[] and b.launch is None


def test_hpc_nsc_settings_rejection_precedes_detector_clear(execution):
    b=execution;b.tool.reject='Filter'
    with pytest.raises(ZemaxError) as exc:
        b.run_nsc_ray_trace(COMMAND_MODELS['run_nsc_ray_trace'](filter='requested-filter',hpc={'mode':'preferences'}))
    assert exc.value.code=='SETTING_REJECTED'
    assert 'clear' not in b.tool.events and b.events[-1]=='close' and b.launch is None


@pytest.mark.parametrize('command',['run_global_optimization','run_hammer_optimization','run_tolerance_analysis'])
def test_hpc_native_setup_refusal_closes_before_execution(execution,command):
    b=execution
    if command=='run_tolerance_analysis':
        b.tool.CriterionSampling=3;b.tool.reject='CriterionSampling'
        args=dict(mode='monte_carlo',sampling=4)
    else:
        b.tool.Algorithm=Enum('OrthogonalDescent');b.tool.reject='Algorithm';args=dict(runtime_seconds=2)
    getattr(b,command)(COMMAND_MODELS[command](**args,hpc={'mode':'preferences'}))
    with pytest.raises(ZemaxError) as exc:list(b.flow)
    assert exc.value.code=='SETTING_REJECTED'
    assert 'close' in b.events and b.launch is None
