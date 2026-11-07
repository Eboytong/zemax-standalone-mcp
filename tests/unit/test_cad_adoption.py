"""Ignored native CAD settings and output/close failures must remain observable."""
from pathlib import Path
from types import SimpleNamespace as N
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.errors import ZemaxError
from zemax_mcp.export_models import CadExport
from zemax_mcp.models import TaskResult


class EnumValue:
    def __init__(self,value,label=None):self.value=value;self.label=label or value
    def Equals(self,other):return self.value==other.value
    def __str__(self):return self.label


class Tool:
    def __init__(self,reject=None,flush=True,close=True):
        self.reject=None
        for field in ['FirstSurface','LastSurface','FirstObject','LastObject','NumberOfRays','Field','Wavelength','Configuration']:
            setattr(self,field,-8)
        self.SurfacesAsSolids=False;self.ExportDummySurfaces=True;self.OutputFileName='ignored'
        self.FileType=EnumValue('IGES');self.Tolerance=EnumValue('wrong')
        for field in ['RayPattern','SplineSegments','AngularTolerance','FileVersion']:setattr(self,field,EnumValue('wrong'))
        for field in ['DeleteVignetted','RayLayer','LensLayer','DummyThickness','ScatterNSCRays',
                      'SplitNSCRays','UsePolarization','AutoNameFaces']:setattr(self,field,-8)
        self.reject=reject;self.flush=flush;self.close_result=close;self.closes=0
        self.CanCancel=True;self.IsRunning=False;self.Succeeded=True;self.ErrorMessage='native CAD error'
    def __setattr__(self,key,value):
        if key==getattr(self,'reject',None):return
        object.__setattr__(self,key,value)
    def GetType(self):return N(GetProperty=lambda name:N(PropertyType=name))
    def SetCurrentConfiguration(self):self.Configuration=0
    def SetSingleConfiguration(self,value):self.Configuration=value
    def SetFieldAll(self):self.Field=0
    def SetWavelengthAll(self):self.Wavelength=0
    def Run(self):return True
    def WaitForCompletion(self):pass
    def Close(self):
        self.closes+=1
        if self.close_result and self.flush:Path(self.OutputFileName).write_text('controlled output',encoding='ascii')
        return self.close_result


def backend(tmp_path,monkeypatch,**kwargs):
    tool=Tool(**kwargs)
    native=N(system=N(Mode='Sequential',LDE=N(NumberOfSurfaces=6),NCE=N(NumberOfObjects=4),
        MCE=N(CurrentConfiguration=3,NumberOfConfigurations=4),Tools=N(OpenExportCAD=lambda:tool)))
    native.enum=lambda typ,name:EnumValue(name)
    native.set_enum=lambda obj,name,value:setattr(obj,name,EnumValue(value,'native alias '+value))
    b=Backend(Config(tmp_path,tmp_path),native=native);b.directory=tmp_path;b.work_path=tmp_path/'model.zos'
    b.get_system_settings=lambda req:{}
    monkeypatch.setattr('zemax_mcp.exports.scalar_settings',lambda t:dict(FileType=str(t.FileType),Configuration=t.Configuration))
    return b,tool


@pytest.mark.parametrize('name',['FirstSurface','LastSurface','NumberOfRays','Field','Wavelength','Configuration',
    'SurfacesAsSolids','ExportDummySurfaces','OutputFileName','FileType','Tolerance'])
def test_ignored_cad_setting_rejected_before_run(tmp_path,monkeypatch,name):
    b,tool=backend(tmp_path,monkeypatch,reject=name,flush=False)
    with pytest.raises(ZemaxError)as caught:b.run_cad_export(CadExport(path=str(tmp_path/'a.step')))
    assert caught.value.code=='SETTING_REJECTED' and caught.value.details['setting']==name
    assert tool.closes==1 and b.active is None


def test_cad_enum_alias_final_settings_and_close_before_file_read(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch)
    task=b.run_cad_export(CadExport(path=str(tmp_path/'a.step')))
    # The task starter polls once; Close creates the only output in this fake.
    b.tick()
    result=b.get_task_result(TaskResult(task_id=task['task_id']))
    assert result['task']['state']=='succeeded' and result['task']['close_attempted']
    assert set(result['task']['settings']['checked_fields'])=={
        'SurfacesAsSolids','ExportDummySurfaces','NumberOfRays','Field','Wavelength',
        'Configuration','OutputFileName','FirstSurface','LastSurface','FileType','Tolerance'}
    assert result['task']['settings']['Configuration']==0
    assert result['task']['settings']['configuration_selection']==dict(mode='current',resolved_configuration=3,native_encoding=0)
    assert tool.closes==1 and Path(result['path']).is_file()


@pytest.mark.parametrize('flush,close,expected',[(False,True,'NO_RESULT_DATA'),(False,False,'CLEANUP_FAILED')])
def test_cad_success_without_output_and_close_failure(tmp_path,monkeypatch,flush,close,expected):
    b,tool=backend(tmp_path,monkeypatch,flush=flush,close=close)
    task=b.run_cad_export(CadExport(path=str(tmp_path/'a.step')));b.tick()
    result=b.get_task_result(TaskResult(task_id=task['task_id']))
    assert result['task']['state']=='failed' and result['task']['error']['code']==expected
    assert tool.closes==1
    assert b.requires_reconnect is (not close)


def test_cad_setup_and_close_error_both_retained(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch,reject='LastSurface',flush=False,close=False)
    with pytest.raises(ZemaxError)as caught:b.run_cad_export(CadExport(path=str(tmp_path/'a.step')))
    assert caught.value.code=='SETTING_REJECTED'
    assert caught.value.details['cleanup_error']['code']=='CLEANUP_FAILED'
    assert b.requires_reconnect and tool.closes==1


def test_cad_nsc_object_range_checked(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch,reject='LastObject',flush=False)
    b.native.system.Mode='NonSequential'
    with pytest.raises(ZemaxError)as caught:b.run_cad_export(CadExport(path=str(tmp_path/'a.step'),end=3))
    assert caught.value.details['setting']=='LastObject' and tool.closes==1


OPTIONS=dict(ray_pattern='Grid',delete_vignetted=True,ray_layer=2,lens_layer=3,dummy_thickness=.1,
    spline_segments='N_064',angular_tolerance='High',scatter_nsc_rays=True,split_nsc_rays=True,
    use_polarization=True,auto_name_faces=True,configuration=2)
NATIVE_OPTIONS=['RayPattern','DeleteVignetted','RayLayer','LensLayer','DummyThickness','SplineSegments',
    'AngularTolerance','ScatterNSCRays','SplitNSCRays','UsePolarization','AutoNameFaces','Configuration']


@pytest.mark.parametrize('reject',NATIVE_OPTIONS)
def test_extended_cad_settings_reject_ignored_values(tmp_path,monkeypatch,reject):
    b,tool=backend(tmp_path,monkeypatch,reject=reject,flush=False)
    with pytest.raises(ZemaxError)as caught:
        b.run_cad_export(CadExport(path=str(tmp_path/'a.stl'),format='STL',export_dummy_surfaces=True,**OPTIONS))
    assert caught.value.code=='SETTING_REJECTED' and caught.value.details['setting']==reject
    assert tool.closes==1


def test_extended_cad_adoption_and_selected_configuration(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch)
    started=b.run_cad_export(CadExport(path=str(tmp_path/'a.stl'),format='STL',export_dummy_surfaces=True,**OPTIONS))
    result=b.get_task_result(TaskResult(task_id=started['task_id']))
    assert result['task']['state']=='succeeded'
    assert set(NATIVE_OPTIONS)<=set(result['task']['settings']['checked_fields'])
    assert tool.Configuration==2 and b.system.MCE.CurrentConfiguration==3
    for public,native in zip(OPTIONS,NATIVE_OPTIONS):
        adopted=getattr(tool,native)
        assert getattr(adopted,'value',adopted)==OPTIONS[public]
    assert tool.closes==1


@pytest.mark.parametrize('options',[
    dict(ray_pattern='missing'),dict(spline_segments='N_999'),dict(angular_tolerance='High'),
    dict(format='STL',angular_tolerance='missing'),dict(dummy_thickness=.1),
    dict(dummy_thickness=float('nan'),export_dummy_surfaces=True),dict(ray_layer=-1),dict(lens_layer=True),
    dict(configuration=0),dict(file_version='V99'),dict(ray_pattern='SolidRing',number_of_rays=7),
    dict(format='VisualizationJSON',delete_vignetted=False),
])
def test_extended_cad_typed_boundaries(options):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):CadExport(path='a.step',**options)


@pytest.mark.parametrize('options,code',[(dict(configuration=5),'INDEX_OUT_OF_RANGE'),
    (dict(ray_pattern='SolidRing',number_of_rays=8),'UNSUPPORTED_SETTING')])
def test_cad_mode_and_configuration_before_open(tmp_path,monkeypatch,options,code):
    b,tool=backend(tmp_path,monkeypatch)
    b.native.system.Mode='NonSequential'
    with pytest.raises(ZemaxError)as caught:b.run_cad_export(CadExport(path=str(tmp_path/'a.step'),**options))
    assert caught.value.code==code and tool.closes==0


def test_cad_capability_conditions_and_schema(tmp_path,monkeypatch):
    from zemax_mcp.models import Capabilities
    b,_=backend(tmp_path,monkeypatch)
    value=b.get_capabilities(Capabilities(topic='tool',tool_name='run_cad_export'))
    assert value['cad_export']['conditions']['angular_tolerance']=='STL'
    assert 'configuration'in value['request_schema']['properties']
    assert value['cad_export']['native_acceptance'].startswith('STEP/STL/SAT')
    assert 'native encoding 0' in value['cad_export']['configuration']


@pytest.mark.parametrize('mode,expected',[('all_by_file',5),('all_by_layer',6),('all_at_once',7)])
def test_multiple_configuration_adoption(tmp_path,monkeypatch,mode,expected):
    b,tool=backend(tmp_path,monkeypatch)
    setattr(tool,{'all_by_file':'SetConfigurationAllByFile','all_by_layer':'SetConfigurationAllByLayer','all_at_once':'SetConfigurationAllAtOnce'}[mode],lambda:setattr(tool,'Configuration',expected))
    task=b.run_cad_export(CadExport(path=str(tmp_path/'multi.step'),configuration_mode=mode))
    assert task['settings']['configuration_selection']==dict(mode=mode,resolved_configuration=[1,2,3,4],native_encoding=expected)
    assert tool.closes==1


@pytest.mark.parametrize('extra',[dict(configuration_mode='single'),dict(configuration_mode='current',configuration=1),dict(configuration_mode='all_by_file',configuration=2),dict(configuration_mode='all_by_layer',format='VisualizationJSON')])
def test_configuration_mode_rejects_conflicting_parameters(extra):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):CadExport(path='C:/output/model.step',**extra)


def test_multi_file_missing_configuration_preserves_output_location(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch)
    tool.SetConfigurationAllByFile=lambda:setattr(tool,'Configuration',5)
    task=b.run_cad_export(CadExport(path=str(tmp_path/'multi.step'),configuration_mode='all_by_file'));b.tick()
    result=b.get_task_result(TaskResult(task_id=task['task_id']))
    assert result['task']['error']['code']=='NO_RESULT_DATA'
    assert result['task']['error']['details']['expected_configurations']==4
    assert tool.closes==1


@pytest.mark.parametrize('mode,method',[('all_by_file','SetConfigurationAllByFile'),('all_by_layer','SetConfigurationAllByLayer'),('all_at_once','SetConfigurationAllAtOnce')])
def test_multiple_configuration_rejected_final_readback(tmp_path,monkeypatch,mode,method):
    b,tool=backend(tmp_path,monkeypatch)
    setattr(tool,method,lambda:setattr(tool,'Configuration',0))
    with pytest.raises(ZemaxError)as error:b.run_cad_export(CadExport(path=str(tmp_path/'multi.step'),configuration_mode=mode))
    assert error.value.code=='SETTING_REJECTED'and error.value.details['setting']=='Configuration'
    assert tool.closes==1



def test_nsc_number_of_rays_rejected_before_native_open(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch);b.native.system.Mode='NonSequential'
    b.native.system.Tools.OpenExportCAD=lambda:pytest.fail('inactive setting opened tool')
    with pytest.raises(ZemaxError)as error:b.run_cad_export(CadExport(path=str(tmp_path/'nsc.step'),number_of_rays=8))
    assert error.value.code=='INACTIVE_SETTING'and error.value.details['setting']=='number_of_rays'


@pytest.mark.parametrize('format,prefix',[('SAT',b'500 0 1 0\n'),('SAB',b'ACIS BinaryFile'+(500).to_bytes(4,'little'))])
def test_acis_actual_header_overrides_adopted_version(tmp_path,format,prefix):
    from zemax_mcp.exports import acis_metadata
    path=tmp_path/('native.'+format.lower());path.write_bytes(prefix)
    assert acis_metadata(path,format,'Current')['major']==5
    with pytest.raises(ZemaxError)as error:acis_metadata(path,format,'V30')
    assert error.value.code=='SETTING_REJECTED'and error.value.details['actual']['version_code']==500
    assert error.value.details['path']==str(path)


def test_acis_requested_version_adopted_in_file(tmp_path):
    from zemax_mcp.exports import acis_metadata
    path=tmp_path/'native.sat';path.write_bytes(b'3000 0 1 0\n')
    assert acis_metadata(path,'SAT','V30')['major']==30


def test_acis_version_setting_rejected_before_execution(tmp_path,monkeypatch):
    b,tool=backend(tmp_path,monkeypatch,reject='FileVersion',flush=False)
    with pytest.raises(ZemaxError)as error:b.run_cad_export(CadExport(path=str(tmp_path/'a.sat'),format='SAT',file_version='V30'))
    assert error.value.code=='SETTING_REJECTED'and tool.closes==1


def test_non_acis_version_is_inactive():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):CadExport(path='C:/output/a.stl',format='STL',file_version='V30')


@pytest.mark.parametrize('format,payload',[('SAT',b'not an ACIS header'),('SAB',b'ACIS BinaryFile')])
def test_malformed_acis_header_keeps_format_error(tmp_path,format,payload):
    from zemax_mcp.exports import acis_metadata
    path=tmp_path/'native';path.write_bytes(payload)
    with pytest.raises(ZemaxError)as error:acis_metadata(path,format)
    assert error.value.code=='INVALID_RESULT_DATA'
