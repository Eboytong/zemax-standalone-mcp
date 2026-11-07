from pathlib import Path
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import TaskRequest
from zemax_mcp.speos_models import RunSpeosExport
from zemax_mcp.speos import OwnedCopyTool
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('patch',[
    {'sensor_width':0},{'sensor_height':float('inf')},{'sample_points':21},
    {'assume_radial_symmetry':True,'x_sampling':5}, {'x_sampling':2147483648},
    {'x_sampling':True},{'sampling':'S_31x31'},{'file_format_version':3},
])
def test_lens_system_typed_conditions(patch):
    with pytest.raises(ValidationError):
        RunSpeosExport(request={**dict(kind='lens_system',path='fixture.OPTDistortion',sensor_width=8,sensor_height=6),**patch})


@pytest.mark.parametrize('patch',[{'configuration':1},{'sensor_width':8},{'overwrite':True}])
def test_whitebox_dedicated_request(patch):
    with pytest.raises(ValidationError):RunSpeosExport(request=dict(kind='whitebox',output_directory='fixture',**patch))


class Enum:
    def __init__(self,name):self.name=name
    def __str__(self):return self.name
    def Equals(self,other):return isinstance(other,Enum) and self.name==other.name


class NativeTool:
    def __init__(self,b,system):
        self.b=b;self.system=system;self.kind='';self.reject=None
        self.SensorWidth=0.;self.SensorHeight=0.;self.SampleSize=Enum('S_32x32')
        self.Configuration=0;self.FileFormatVersion=3;self.AssumeRadialSymmetry=False
        self.SkipSystemReversal=False;self.OPTDistortionFilename=''
        self.XSampling=1;self.YSampling=1;self.SamplePoints=1
        self.CanCancel=True;self.IsRunning=False;self.Succeeded=False;self.ErrorCode=0;self.ErrorMessage='fixture error'
        self.ran=False;self.no_output=False;self.close_ok=True;self.run_ok=True;self.run_success=True
        self.asynchronous=False;self.mutate_source=False;self.initial_unavailable=False;self.output_override=None
        self.closed=0;self.writes=[]
    def __setattr__(self,name,value):
        if name==getattr(self,'reject',None):return
        object.__setattr__(self,name,value)
        if name in {'Configuration','AssumeRadialSymmetry','SamplePoints','XSampling','YSampling','SensorWidth'} and hasattr(self,'writes'):
            self.writes.append(name)
    def GetType(self):
        def prop(name):
            if not hasattr(self,name):return None
            value=getattr(self,name)
            kind='System.Boolean' if type(value)is bool else 'System.Int32' if type(value)is int else 'System.Double' if type(value)is float else 'System.String'
            return N(CanWrite=True,PropertyType=N(IsEnum=isinstance(value,Enum),FullName=kind))
        return N(GetProperty=prop)
    @property
    def OutputFilename(self):
        if self.initial_unavailable and not self.ran:raise RuntimeError('output not initialized')
        return self.output_override or 'whitebox.native'
    def Run(self):
        self.ran=True;self.b.events.append('run');self.IsRunning=self.asynchronous
        if not self.run_ok:return False
        self.Succeeded=self.run_success
        if self.mutate_source:self.b.system.LDE.NumberOfSurfaces+=1
        if self.Succeeded and not self.no_output:
            path=Path(self.OPTDistortionFilename) if self.kind=='lens_system' else Path(self.system.SystemFile).parent/self.OutputFilename
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('native fixture',encoding='utf-8')
            if self.kind=='whitebox':(path.parent/'support.bin').write_bytes(b'fixture')
        return True
    def WaitForCompletion(self):return True
    def Cancel(self):self.IsRunning=False;self.Succeeded=False;self.b.events.append('cancel');return True
    def Close(self):self.closed+=1;self.b.events.append('tool_close');return self.close_ok


class System:
    def __init__(self,b,copied=False):
        self.b=b;self.copied=copied;self.SystemID=2 if copied else 1;self.Mode='Sequential'
        self.SystemFile=str(b.directory/('copy.zos' if copied else 'working.zos'))
        self.SystemData=N(Units=N(LensUnits='Millimeters'))
        self.MCE=N(CurrentConfiguration=1,NumberOfConfigurations=2);self.LDE=N(NumberOfSurfaces=4)
        self.NCE=N(NumberOfObjects=2)
        self.IsProjectDirectory=False;self.closed=0;self.close_ok=True
        self.Tools=N(OpenExportToSpeosLensSystem=lambda:self.open('lens_system'),OpenExportToSpeosWhitebox=lambda:self.open('whitebox'))
    def CopySystem(self):
        self.b.events.append('copy')
        if self.b.null_copy:return None
        self.b.copy=System(self.b,True);self.b.tool=NativeTool(self.b,self.b.copy)
        for key,value in self.b.tool_options.items():setattr(self.b.tool,key,value)
        self.b.copy.IsProjectDirectory=self.IsProjectDirectory
        self.b.copy.Mode=self.Mode
        self.b.copy.close_ok=self.b.copy_close_ok
        return self.b.copy
    def open(self,kind):self.b.tool.kind=kind;return self.b.tool
    def SaveAs(self,path):
        assert self.copied
        if self.b.copy_save_fails:raise RuntimeError('copy save error')
        self.SystemFile=path;Path(path).write_text('working fixture',encoding='utf-8')
    def Close(self,save):
        assert self.copied and save is False
        self.closed+=1;self.b.events.append('copy_close');return self.close_ok


@pytest.fixture
def backend(tmp_path,monkeypatch):
    import zemax_mcp.speos as module
    b=Backend(Config(Path('unused'),tmp_path),native=N())
    b.directory=tmp_path;b.work_path=tmp_path/'working.zos';b.events=[];b.null_copy=False;b.copy_close_ok=True;b.tool_options={}
    b.copy_save_fails=False
    b.native.system=System(b)
    b.native.enum=lambda typ,name:Enum(name)
    b.native.set_enum=lambda obj,name,value:setattr(obj,name,Enum(value))
    b.get_system_settings=lambda req:dict(lens_units='Millimeters')
    b.context=lambda:dict(model_revision=b.revision,checkpoint=None)
    b._record_task_history=lambda task:None
    b.tick=lambda:None
    def scalar(obj):
        return {k:str(v) if isinstance(v,Enum) else v for k,v in vars(obj).items() if type(v) in (str,bool,float,int) or isinstance(v,Enum)}
    monkeypatch.setattr(module,'scalar_settings',scalar)
    return b


def lens_request(b,**changes):
    return RunSpeosExport(request=dict(kind='lens_system',path=str(b.directory/'result.OPTDistortion'),sensor_width=8,sensor_height=6,**changes))


def finish(b,view):
    Backend.tick(b)
    return b.tasks[view['task_id']]


@pytest.mark.parametrize('radial',[False,True])
def test_native_lens_settings_and_real_task_close_chain(backend,radial):
    b=backend;q=lens_request(b,assume_radial_symmetry=radial)
    assert RunSpeosExport.model_validate(q.model_dump())==q
    task=finish(b,b.run_speos_export(q))
    assert task['state']=='succeeded',task.get('error')
    result=b._full_result(task['task_id'])
    assert result['source_metadata_preserved'] and result['copy_closed'] and result['tool_closed']
    assert b.events[-2:]==['tool_close','copy_close']
    assert b.copy.closed==1 and b.tool.closed==1 and b.revision==0 and b.system.closed==0
    assert b.tool.writes.index('Configuration')<b.tool.writes.index('SensorWidth')
    assert ('SamplePoints' in b.tool.writes)==radial
    assert ('XSampling' in b.tool.writes)!=radial


def test_whitebox_native_name_support_files_and_late_getter(backend):
    b=backend;b.tool_options['initial_unavailable']=True
    q=RunSpeosExport(request=dict(kind='whitebox',output_directory=str(b.directory/'whitebox')))
    task=finish(b,b.run_speos_export(q))
    assert task['state']=='succeeded',task.get('error')
    result=b._full_result(task['task_id'])
    assert Path(result['path']).name=='whitebox.native'
    assert any(Path(a['path']).name=='support.bin' for a in result['artifacts'])
    assert result['copy_closed'] and b.events[-2:]==['tool_close','copy_close']


def test_project_resources_staged_before_export(backend):
    b=backend;b.system.IsProjectDirectory=True
    (b.directory/'Glasscat').mkdir();(b.directory/'Glasscat'/'fixture.agf').write_text('fixture')
    task=finish(b,b.run_speos_export(lens_request(b)))
    assert task['state']=='succeeded'
    assert (Path(b.copy.SystemFile).parent/'Glasscat'/'fixture.agf').is_file()


def test_speos_setup_rejection_closes_tool_then_copy(backend):
    b=backend;b.tool_options['reject']='SensorWidth'
    with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b))
    assert exc.value.code=='SETTING_REJECTED'
    assert b.events[-2:]==['tool_close','copy_close'] and 'run' not in b.events


def test_speos_setup_and_copy_close_errors_are_both_retained(backend):
    b=backend;b.tool_options['reject']='SensorWidth';b.copy_close_ok=False
    with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b))
    assert exc.value.code=='SETTING_REJECTED'
    assert exc.value.details['cleanup_error']['code']=='CLEANUP_FAILED' and b.requires_reconnect


@pytest.mark.parametrize('option,code',[('no_output','NO_RESULT_DATA'),('run_success','SPEOS_EXPORT_FAILED'),('run_ok','TASK_START_FAILED')])
def test_speos_native_failure_and_missing_result_release_both(backend,option,code):
    b=backend;b.tool_options[option]=True if option=='no_output' else False
    if option=='run_ok':
        with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b))
        assert exc.value.code==code
    else:
        task=finish(b,b.run_speos_export(lens_request(b)))
        assert task['state']=='failed' and task['error']['code']==code
    assert b.copy.closed==1 and b.tool.closed==1 and b.system.closed==0


def test_cancelled_speos_task_closes_owned_copy(backend):
    b=backend;b.tool_options['asynchronous']=True
    view=b.run_speos_export(lens_request(b))
    b.cancel_task(TaskRequest(task_id=view['task_id']))
    task=finish(b,view)
    assert task['state']=='cancelled'
    assert b.events[-2:]==['tool_close','copy_close'] and b.system.closed==0


def test_source_metadata_mismatch_invalidates_revision_and_connection(backend):
    b=backend;b.tool_options['mutate_source']=True
    task=finish(b,b.run_speos_export(lens_request(b)))
    assert task['state']=='failed' and task['error']['code']=='SOURCE_MODEL_CHANGED'
    assert b.requires_reconnect and b.revision==1 and b.copy.closed==1


def test_invalid_configuration_and_directory_preflight(backend):
    b=backend
    with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b,configuration=3))
    assert exc.value.code=='INDEX_OUT_OF_RANGE' and b.events==[]
    with pytest.raises(ZemaxError) as exc:
        b.run_speos_export(RunSpeosExport(request=dict(kind='whitebox',output_directory=str(b.directory))))
    assert exc.value.code=='INVALID_OUTPUT_DIRECTORY' and b.events==[]


def test_close_failure_does_not_close_parent_under_live_tool(backend):
    b=backend;b.tool_options['close_ok']=False
    task=finish(b,b.run_speos_export(lens_request(b)))
    assert task['state']=='failed' and task['error']['code']=='CLEANUP_FAILED'
    assert b.copy.closed==0 and b.requires_reconnect


def test_whitebox_output_outside_owned_directory_is_rejected(backend):
    b=backend;b.tool_options['output_override']=str(b.directory/'outside.native')
    with pytest.raises(ZemaxError) as exc:
        b.run_speos_export(RunSpeosExport(request=dict(kind='whitebox',output_directory=str(b.directory/'wb'))))
    assert exc.value.code=='UNSUPPORTED_OUTPUT_LOCATION' and 'run' not in b.events
    assert b.copy.closed==1 and b.tool.closed==1


def test_whitebox_preserves_nsc_mode_of_the_copy(backend):
    b=backend;b.system.Mode='NonSequential'
    q=RunSpeosExport(request=dict(kind='whitebox',output_directory=str(b.directory/'wb')))
    task=finish(b,b.run_speos_export(q))
    assert task['state']=='succeeded'
    assert b.copy.Mode=='NonSequential' and b._full_result(task['task_id'])['source_system']['mode']=='NonSequential'


def test_output_overwrite_requires_explicit_request(backend):
    b=backend;(b.directory/'result.OPTDistortion').write_text('prior output')
    with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b))
    assert exc.value.code=='OUTPUT_EXISTS' and b.events==[]
    task=finish(b,b.run_speos_export(lens_request(b,overwrite=True)))
    assert task['state']=='succeeded'


def test_copy_save_failure_releases_copy_without_opening_tool(backend):
    b=backend;b.copy_save_fails=True
    with pytest.raises(RuntimeError,match='copy save error'):b.run_speos_export(lens_request(b))
    assert b.copy.closed==1 and b.tool.closed==0 and 'run' not in b.events


def test_null_copy_is_reported_without_native_tool_use(backend):
    b=backend;b.null_copy=True
    with pytest.raises(ZemaxError) as exc:b.run_speos_export(lens_request(b))
    assert exc.value.code=='COPY_FAILED' and b.events==['copy']
