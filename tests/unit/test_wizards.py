"""Wizard type contracts, dependencies and cooperative task results."""
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.wizard_models import OptimizationWizard, WizardOptions, WIZARD_FIELDS
from zemax_mcp.wizards import conditions, selections
from zemax_mcp.errors import ZemaxError
from tests.unit.test_design_tools import Backend, Enum

@pytest.mark.parametrize('payload',[
    dict(kind='sequential',rings=0),dict(kind='sequential',rings=1.5),
    dict(kind='sequential',criterion='bad'),dict(kind='sequential',target=1),
    dict(kind='sequential',overall_weight=float('nan')),dict(kind='sequential',rings=None),
    dict(kind='bitmap',bitmap_file=-1),dict(kind='roadway',number_of_lanes=0),
    dict(kind='nsc',configuration=True),dict(kind='nsc',road_class=1),
])
def test_wizard_request_rejects(payload):
    with pytest.raises(ValidationError):OptimizationWizard(request=payload)

def defaults(kind):
    data={name:False if name.startswith(('Is','Use','Optimize','Assume','Ignore','Add','Delete')) else 1 for name in WIZARD_FIELDS[kind].values()}
    if kind=='sequential':
        data.update(UseGaussianQuadrature=True,UseRectangularArray=False,Obscuration=0.,UseAllConfigurations=True,UseAllFields=True,
            IsHighManufacturingYieldAvailable=False,Criterion=Enum('Spot'),Type=Enum('RMS'),Reference=Enum('Centroid'),Arms=Enum('Arms_6'))
    return data

class Wizard:
    def __init__(self,kind):
        self.state=defaults(kind);self.applied=0;self.reset=0;self.CommonSettings=self;self.NSCSettings=self
    def __getattr__(self,name):
        if name in self.state:return self.state[name]
        raise AttributeError(name)
    def __setattr__(self,name,value):
        if name!='state'and 'state'in self.__dict__ and name in self.state:
            if name!=getattr(self,'reject',None):self.state[name]=value
        else:object.__setattr__(self,name,value)
    def GetType(self):return N(GetProperty=lambda name:N(PropertyType=N(IsEnum=isinstance(self.state[name],Enum))))
    def ResetSettings(self):self.reset+=1
    def Apply(self):
        self.applied+=1
        if getattr(self,'fail',False):raise RuntimeError('original apply failure')

@pytest.fixture
def b(monkeypatch):
    from zemax_mcp import wizards
    b=Backend();b.wizard=Wizard('sequential');b._system.MFE=N(NumberOfOperands=1)
    b._system.SystemData.Fields=N(NumberOfFields=3);b._system.MCE.NumberOfConfigurations=2
    b._wizard=lambda kind:(b.wizard,b.wizard,b.wizard)
    b.get_merit_function=lambda req:dict(total=1,rows=[dict(type='RSCE')])
    monkeypatch.setattr(wizards,'scalar_settings',lambda target:dict(target.state))
    monkeypatch.setattr(wizards,'native_setting',lambda native,target,name,value:setattr(target,name,Enum(value)if isinstance(target.state[name],Enum)else value))
    b.native.enum=lambda t,v:Enum(v)
    return b

def finish(b,payload):
    view=b.run_optimization_wizard(OptimizationWizard(request=payload))
    for _ in range(8):
        if b.active is None:break
        b.tick()
    return b.tasks[view['task_id']]

def test_preview_keeps_revision_and_merit(b):
    task=finish(b,dict(kind='sequential',rings=5))
    assert task['state']=='succeeded'and b.revision==0 and b.wizard.applied==0
    assert task['result']['settings']['Rings']==5 and task['result']['applied']is False

def test_apply_generates_merit_with_checkpoint(b):
    task=finish(b,dict(kind='sequential',apply=True,rings=5))
    assert task['state']=='succeeded'and b.revision==1 and b.wizard.applied==1
    assert task['result']['operands']['rows'][0]['type']=='RSCE'

def test_inactive_sampling_fails_before_model_write(b):
    task=finish(b,dict(kind='sequential',grid_size_nx_n=16,apply=True))
    assert task['state']=='failed'and task['error']['code']=='INACTIVE_SETTING'and b.revision==0

def test_switch_sampling_changes_radio_pair(b):
    task=finish(b,dict(kind='sequential',use_rectangular_array=True,grid_size_nx_n=16))
    assert task['state']=='succeeded'and b.wizard.UseGaussianQuadrature is False

def test_setting_rejection_stops_apply(b):
    b.wizard.reject='Rings'
    task=finish(b,dict(kind='sequential',rings=5,apply=True))
    assert task['state']=='failed'and task['error']['code']=='SETTING_REJECTED'and b.wizard.applied==0

def test_apply_failure_retains_original_and_counts(b):
    b.wizard.fail=True
    task=finish(b,dict(kind='sequential',apply=True))
    assert task['state']=='failed'and task['error']['code']=='WIZARD_APPLY_FAILED'
    assert task['error']['details']['cause']['message']=='original apply failure'
    assert task['error']['details']['operands_after']==1 and b.revision==1

def test_cancel_at_boundary_keeps_merit(b):
    view=b.run_optimization_wizard(OptimizationWizard(request=dict(kind='sequential',apply=True)))
    b.tick();task=b.tasks[view['task_id']];task['cancel_requested']=True;b.tick()
    assert task['state']=='cancelled'and b.wizard.applied==0 and b.revision==0

@pytest.mark.parametrize('patch,code',[
    ({'UseGaussianQuadrature':False},'INVALID_SETTINGS'),
    ({'UseAllFields':False,'FieldNumber':4},'INDEX_OUT_OF_RANGE'),
    ({'FieldNumber':1},'INACTIVE_SETTING'),
    ({'UseGlassBoundaryValues':True,'GlassMin':2,'GlassMax':1},'INVALID_SETTINGS'),
    ({'OptimizeForManufacturingYield':True},'CAPABILITY_UNAVAILABLE'),
    ({'Obscuration':1},'INVALID_SETTINGS'),
    ({'OverallWeight':-1},'INVALID_SETTINGS'),
])
def test_sequential_conditions(b,patch,code):
    final={**defaults('sequential'),**patch}
    with pytest.raises(ZemaxError)as exc:conditions('sequential',final,patch,b.system)
    assert exc.value.code==code

@pytest.mark.parametrize('kind',['nsc','bitmap'])
def test_nsc_inactive_target(b,kind):
    final={**defaults(kind),'Target':2}
    with pytest.raises(ZemaxError)as exc:conditions(kind,final,{'Target':2},b.system)
    assert exc.value.code=='INACTIVE_SETTING'

def test_discovery_retains_failed_accessor():
    def get(i):
        if i==1:raise RuntimeError('bad lookup')
        return 'choice'
    data=selections(N(Count=2,GetAt=get),[('Count','GetAt')])
    assert data['GetAt']['entries']==[dict(native_index=0,label='choice'),dict(native_index=1,error='bad lookup')]


def test_merit_readback_available_to_nonsequential_wizard():
    from zemax_mcp.backend import Backend as RealBackend
    cell=N(Header='',DataType='Integer',IsActive=False,IsReadOnly=False)
    row=N(Type='NSDD',Target=0,Weight=1,Value=0,Contribution=0,GetCellAt=lambda _:cell)
    owner=N(system=N(Mode='NonSequential',MFE=N(NumberOfOperands=1,GetOperandAt=lambda _:row)),
        _require_work=lambda:None)
    result=RealBackend.get_merit_function(owner,None)
    assert result['operands'][0]['type']=='NSDD'
    assert result['total']==1 and result['values_are_cached']
