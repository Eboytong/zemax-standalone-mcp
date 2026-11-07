"""Design tool contracts and task lifecycle using controlled native doubles."""
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.backend import Backend as RealBackend
from zemax_mcp.design_tools import DesignToolsMixin, FIELDS
from zemax_mcp.design_models import DesignTool, DesignToolOptions
from zemax_mcp.errors import ZemaxError

class Enum(str):
    def Equals(self, other): return self == other

class Tool:
    def __init__(self, owner):
        self.owner=owner;self.closed=0;self.IsRunning=False;self.CanCancel=True
        self.Progress=0;self.Status='running';self.Succeeded=True;self.ErrorMessage='native failure'
        defaults=dict(ScaleByFactor=True,ScaleByUnits=False,ScaleFactor=1.,FirstComponent=1,LastComponent=2,NumberOfComponents=3,
            ScaleToUnit=Enum('Millimeters'),AdjustSurface=1,SurfaceParameter=Enum('Thickness'),Criterion=Enum('SpotSizeRadial'),EvaluateSurface=3,
            FirstSurface=1,LastSurface=2,AsphereType=Enum('Conic'),Surface=1,NumberOfTerms=8,ExcludeSecondOrderTerm=False,
            AllowRadiusVariation=False,AllowConicVariation=False,StartMeritFunction=2.,BestMeritFunction=1.,BestSurface=1,ResidualRMSError=1e-9)
        self.__dict__.update(defaults)
    def __setattr__(self,name,value):
        if name==getattr(self,'reject',None):return
        object.__setattr__(self,name,value)
    def GetType(self):return N(GetProperty=lambda name:N(PropertyType=name))
    def SetEvaluateSurfaceImage(self):self.EvaluateSurface=3
    def Close(self):self.closed+=1;return not getattr(self,'close_fail',False)
    def Run(self):
        self.IsRunning=getattr(self,'delayed',False)
        return not getattr(self,'start_fail',False)
    def WaitForCompletion(self):return True
    def Cancel(self):self.IsRunning=False;return True

class Backend(RealBackend):
    def __init__(self):
        self.revision=0;self.last_checkpoint=None;self.tasks={};self.active=None;self.request_id=None;self.requires_reconnect=False
        self.rows=[N(Type='Standard',Radius=50.,Thickness=10.,Conic=0.,RadiusCell=N(Solve='Fixed'),ThicknessCell=N(Solve='Fixed'))for _ in range(4)]
        lde=N(NumberOfSurfaces=4,GetSurfaceAt=lambda i:self.rows[i])
        self._system=N(Mode='Sequential',LDE=lde,MCE=N(CurrentConfiguration=1),SystemData=N(Units=N(LensUnits='Millimeters')))
        self.tool=Tool(self)
        self._system.Tools=N(**{name:lambda:self.tool for name in ['OpenScale','OpenQuickAdjust','OpenFindBestAsphere','OpenConvertAsphereTypes','OpenRayAimingWizard']})
        self.native=N(set_enum=lambda o,n,v:setattr(o,n,Enum(v)),enum=lambda t,v:Enum(v),property_enum_names=lambda o,n:['allowed'])
    @property
    def system(self):return self._system
    def _mutate(self,label):self.revision+=1;self.last_checkpoint='checkpoint.zos'
    def _guard_cell(self,cell,replace=False):
        if cell.Solve not in ('Fixed','Variable')and not replace:raise ZemaxError('SOLVE_PROTECTED','protected')
    def context(self):return dict(checkpoint=self.last_checkpoint,model_revision=self.revision)
    def get_system_settings(self,req):return {}
    def _save_task_result(self,task,result):task['result']=result

@pytest.mark.parametrize('payload',[
    {'kind':'scale_factor','factor':0},{'kind':'scale_factor','factor':float('inf')},
    {'kind':'scale_factor','factor':2,'first_component':3,'last_component':2},
    {'kind':'scale_units','unit':'bad'}, {'kind':'scale_units','unit':'Inches','factor':2},
    {'kind':'quick_adjust','surface':True},{'kind':'quick_adjust','surface':0},
    {'kind':'quick_adjust','surface':1,'parameter':'Conic'},
    {'kind':'find_best_asphere','first_surface':2,'last_surface':1},
    {'kind':'convert_asphere','surface':1,'asphere_type':'EvenAsphere','number_of_terms':0},
    {'kind':'ray_aiming_wizard','surface':1},
])
def test_contract_rejects(payload):
    with pytest.raises(ValidationError):DesignTool(request=payload)

@pytest.mark.parametrize('payload,expected',[
    ({'kind':'scale_factor','factor':2},'ScaleFactor'),
    ({'kind':'scale_units','unit':'Inches'},'ScaleToUnit'),
    ({'kind':'quick_adjust','surface':1},'EvaluateSurface'),
    ({'kind':'find_best_asphere','first_surface':1,'last_surface':2},'FirstSurface'),
    ({'kind':'convert_asphere','surface':1,'asphere_type':'EvenAsphere'},'Surface'),
    ({'kind':'convert_asphere','surface':1,'asphere_type':'QTypeAsphereType0','number_of_terms':12},'NumberOfTerms'),
])
def test_success_closes_once_and_saves_result(payload,expected):
    b=Backend();view=b.run_design_tool(DesignTool(request=payload));task=b.tasks[view['task_id']]
    assert view['state']=='succeeded'and b.tool.closed==1 and b.active is None
    assert expected in task['result']['settings']and task['result']['checkpoint']=='checkpoint.zos'
    assert task['result']['before']['model_revision']==0 and task['result']['after']['model_revision']==1

@pytest.mark.parametrize('payload',[
    {'kind':'quick_adjust','surface':3}, {'kind':'quick_adjust','surface':2,'evaluate_surface':1},
    {'kind':'find_best_asphere','first_surface':1,'last_surface':3},
    {'kind':'convert_asphere','surface':3,'asphere_type':'EvenAsphere'}])
def test_runtime_bounds_before_mutation(payload):
    b=Backend()
    with pytest.raises(ZemaxError)as exc:b.run_design_tool(DesignTool(request=payload))
    assert exc.value.code=='INDEX_OUT_OF_RANGE'and b.revision==0 and b.tool.closed==0

def test_solve_protection():
    b=Backend();b.rows[1].ThicknessCell.Solve='Pickup'
    with pytest.raises(ZemaxError)as exc:b.run_design_tool(DesignTool(request={'kind':'quick_adjust','surface':1}))
    assert exc.value.code=='SOLVE_PROTECTED'and b.revision==0

def test_readback_rejection_closes():
    b=Backend();b.tool.reject='ScaleFactor'
    with pytest.raises(ZemaxError)as exc:b.run_design_tool(DesignTool(request={'kind':'scale_factor','factor':2}))
    assert exc.value.code=='SETTING_REJECTED'and b.tool.closed==1 and b.revision==1

def test_original_error_survives_close_failure():
    b=Backend();b.tool.reject='ScaleFactor';b.tool.close_fail=True
    with pytest.raises(ZemaxError)as exc:b.run_design_tool(DesignTool(request={'kind':'scale_factor','factor':2}))
    assert exc.value.code=='SETTING_REJECTED'and b.requires_reconnect

def test_native_start_failure_closes_once():
    b=Backend();b.tool.start_fail=True
    with pytest.raises(ZemaxError)as exc:b.run_design_tool(DesignTool(request={'kind':'scale_factor','factor':2}))
    assert exc.value.code=='TASK_START_FAILED'and b.tool.closed==1 and b.active is None

def test_native_computation_failure_keeps_cause():
    b=Backend();b.tool.Succeeded=False
    t=b.run_design_tool(DesignTool(request={'kind':'scale_factor','factor':2}))
    assert t['state']=='failed'and b.tasks[t['task_id']]['error']['message']=='native failure'and b.tool.closed==1

def test_cancel_waits_then_closes_without_collecting():
    b=Backend();b.tool.delayed=True
    t=b.run_design_tool(DesignTool(request={'kind':'scale_factor','factor':2}));task=b.tasks[t['task_id']]
    assert b.tool.closed==0 and task['state']=='running'
    task['cancel_requested']=True;b.tool.Cancel();b.tick()
    assert task['state']=='cancelled'and b.tool.closed==1 and task['result']['completed']is False

@pytest.mark.parametrize('name',['StartMeritFunction','BestMeritFunction','BestSurface'])
def test_nonfinite_results_fail(name):
    b=Backend();setattr(b.tool,name,float('nan'))
    t=b.run_design_tool(DesignTool(request={'kind':'find_best_asphere','first_surface':1,'last_surface':2}))
    assert t['state']=='failed'and b.tasks[t['task_id']]['error']['code']=='INVALID_RESULT_DATA'and b.tool.closed==1

@pytest.mark.parametrize('kind',FIELDS)
def test_options_closes_without_model_mutation(kind):
    b=Backend();r=b.get_design_tool_options(DesignToolOptions(kind=kind))
    assert r['kind']==kind and b.revision==0 and b.tool.closed==1
@pytest.mark.parametrize('apply',[False,True])
def test_ray_aiming_preview_and_apply(apply):
    from zemax_mcp.design_tools import RAY_FIELDS
    b=Backend();values={name:False if name.startswith(('Use','Scale','Automatically')) else 0. for name in RAY_FIELDS}
    values.update(RayAiming=Enum('Off'),Method=Enum('Paraxial'),NumStepsCacheSetup=4)
    current=N(**values);recommended=N(**{**values,'UseRayAimingCache':True})
    current.GetType=b.tool.GetType
    b.system.SystemData.RayAiming=current;b.tool.GetRecommendedSettings=lambda:recommended
    b.tool.ApplyRecommendedSettings=lambda:current.__dict__.update(recommended.__dict__)
    t=b.run_design_tool(DesignTool(request=dict(kind='ray_aiming_wizard',apply=apply)))
    task=b.tasks[t['task_id']]
    assert t['state']=='succeeded'and b.tool.closed==1 and b.revision==int(apply)
    assert task['result']['applied']==apply and current.UseRayAimingCache==apply

def test_ray_aiming_missing_recommendations():
    from zemax_mcp.design_tools import RAY_FIELDS
    b=Backend();b.system.SystemData.RayAiming=N(**{name:Enum('Off')if name in ('RayAiming','Method')else 0 for name in RAY_FIELDS})
    b.tool.GetRecommendedSettings=lambda:None
    t=b.run_design_tool(DesignTool(request=dict(kind='ray_aiming_wizard')))
    assert t['state']=='failed'and b.tasks[t['task_id']]['error']['code']=='RESULT_UNAVAILABLE'and b.tool.closed==1
