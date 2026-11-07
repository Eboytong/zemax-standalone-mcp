"""Critical/single-ray typed settings and structured result contracts."""
from types import SimpleNamespace as NS
from pathlib import Path
import pytest
from pydantic import ValidationError
from zemax_mcp.path_models import CriticalRayTrace,NscSingleRayTrace
from zemax_mcp import nsc_analyses as na
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[dict(l=1),dict(n=0),dict(x=float('inf')),dict(reference_object=-1),dict(wavelength=0),dict(split_rays=True),dict(decimal_precision=16),dict(max_segments=0),dict(max_segments=100001)])
def test_invalid_single(payload):
    with pytest.raises(ValidationError):NscSingleRayTrace(kind='nsc_single_ray_trace',**payload)

@pytest.mark.parametrize('payload',[dict(position_tolerance=0),dict(angle_tolerance_deg=181),dict(angle_tolerance_deg=float('nan')),dict(rays_to_display='All')])
def test_invalid_critical(payload):
    with pytest.raises(ValidationError):CriticalRayTrace(kind='critical_ray_trace',path='rays.CRS',**payload)

class Wavelength:
    def SetWavelengthNumber(self,n):self.n=n
    def GetWavelengthNumber(self):return self.n

class B:
    def __init__(self,tmp):
        self.directory=tmp;self.native=None;self.closed=[]
        self.system=NS(SystemFile=str(tmp/'working.zos'),NCE=NS(NumberOfObjects=3),UpdateFileLists=lambda:None,
            SystemData=NS(Units=NS(LensUnits='Millimeters'),Wavelengths=NS(NumberOfWavelengths=2)))
        self.settings=NS(Wavelength=Wavelength());self.tool=NS(GetSettings=lambda:self.settings)
    def _require_nsc(self):pass
    def _require_work(self):pass
    def _close_task_native(self,t):self.closed.append(t['native']);return True
    def _start_task(self,kind,tool,settings,**kwargs):self.task=dict(task_id='a',kind=kind,native=tool,settings=settings,**kwargs);return self.task

@pytest.fixture
def backend(tmp_path,monkeypatch):
    b=B(tmp_path)
    monkeypatch.setattr(na,'new_analysis',lambda *args:b.tool)
    monkeypatch.setattr(na,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(na,'check',lambda n,s,k,v:None if getattr(s,k)==v else (_ for _ in ()).throw(ZemaxError('SETTING_REJECTED','final drift')))
    monkeypatch.setattr(na,'scalar_settings',lambda s:{k:v for k,v in vars(s).items()if k!='Wavelength'})
    return b

def report_result():return NS(IsValid=True,HeaderData=NS(Lines=['header']),NumberOfMessages=0,GetTextFile=lambda p:False)

def test_polarization_dependency_and_readback(backend,monkeypatch):
    events=[]
    def write(n,s,k,v):events.append(k);setattr(s,k,v)
    monkeypatch.setattr(na,'checked',write)
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace',split_rays=True,use_polarization=True))
    assert events.index('UsePolarization')<events.index('SplitNSCRays')
    assert backend.settings.Wavelength.n==1 and t['settings']['native']['RefObject']==0
    assert Path(backend.settings.SaveRaysFile).suffix=='.zrd'
    assert Path(backend.settings.SaveRaysFile).name==backend.settings.SaveRaysFile
    assert Path(t['settings']['database_output_path']).parent==backend.directory

@pytest.mark.parametrize('kw',[dict(wavelength=3),dict(reference_object=4)])
def test_index_bounds_before_open(backend,kw):
    with pytest.raises(ZemaxError)as caught:na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace',**kw))
    assert caught.value.code=='INDEX_OUT_OF_RANGE' and not backend.closed

def test_critical_staging(backend):
    path=backend.directory/'source.CRS';path.write_text('fixture')
    t=na.run_nsc_analysis(backend,CriticalRayTrace(kind='critical_ray_trace',path=str(path)))
    assert t['settings']['native']['PositionTolerance']==.01
    assert Path(t['settings']['working_file']).is_file() and t['settings']['working_file']!=str(path)
    assert backend.settings.Filename==t['settings']['working_file']

@pytest.mark.parametrize('phase',['checked','check'])
def test_rejected_settings_close(backend,monkeypatch,phase):
    def fail(*args):raise RuntimeError('native rejection')
    monkeypatch.setattr(na,phase,fail)
    with pytest.raises(RuntimeError,match='native rejection'):na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'))
    assert backend.closed==[backend.tool]

def critical_data():
    ray=NS(FieldPoint=1,RayType='ChiefRay',Pass=True,TerminationObject=4,Wavelength=.55)
    for suffix in ['In','Target','Actual']:
        for axis in 'XYZLMN':setattr(ray,axis+suffix,1. if axis=='N'else 0.)
    return NS(NumRays=1,Rays=[ray],HeaderLabels=['Field','Wavelength'])

def test_critical_coordinates_and_scope(backend):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'));t['settings']['requested']['rays_to_display']='PassedRays'
    r=report_result();r.CriticalRayData=critical_data();data=na.collect_critical(backend,t,r)
    assert data['rows'][0]['actual_direction']==[0.,0.,1.]
    assert data['summary']==dict(returned_rays=1,returned_passed=1,returned_failed=0,scope='PassedRays')
    assert data['native_export_error']=='GetTextFile returned false'

@pytest.mark.parametrize('scope,expected',[('AllRays',[True,False]),('PassedRays',[True]),('FailedRays',[False])])
def test_critical_display_scope_filters_unfiltered_native_rows(backend,scope,expected):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'));t['settings']['requested']['rays_to_display']=scope
    r=report_result();r.CriticalRayData=critical_data()
    from copy import copy
    failed=copy(r.CriticalRayData.Rays[0]);failed.Pass=False
    r.CriticalRayData.Rays.append(failed);r.CriticalRayData.NumRays=2
    result=na.collect_critical(backend,t,r)
    assert [row['passed']for row in result['rows']]==expected
    assert result['native_data_scope']['returned_rays']==2
    assert result['summary']['returned_rays']==len(expected)

@pytest.mark.parametrize('mutation,code',[
    (lambda d:setattr(d,'NumRays',127009),'RESULT_TOO_LARGE'),
    (lambda d:setattr(d,'NumRays',2),'INVALID_RESULT_DATA'),
    (lambda d:setattr(d.Rays[0],'XActual',float('nan')),'INVALID_RESULT_DATA'),
])
def test_critical_invalid_results(backend,mutation,code):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'));t['settings']['requested']['rays_to_display']='AllRays'
    r=report_result();r.CriticalRayData=critical_data();mutation(r.CriticalRayData)
    with pytest.raises(ZemaxError)as caught:na.collect_critical(backend,t,r)
    assert caught.value.code==code

def test_segments_status_and_limit(backend,monkeypatch):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace',max_segments=1))
    r=report_result();r.NSCSingleRayTraceData=NS(IsValid=True,NumberOfSegments=3,WaveIndex=1,WavelengthUM=.55,ZRDFile='')
    monkeypatch.setattr(na,'read_segment',lambda *args:(True,*([0]*5),'Transmitted',*([.1]*14),0,0,*([.2]*7)))
    data=na.collect_single(backend,t,r)
    assert data['rows'][0]['status']=='Transmitted' and data['rows'][0]['native_segment_index']==1
    assert data['summary']['truncated'] and data['summary']['returned_segments']==1
    assert data['rows'][0]['phase_at']==.2 and data['database_export_error']

@pytest.mark.parametrize('out',[(False,),(True,1),tuple([False]*30)])
def test_segment_failure_index(backend,monkeypatch,out):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'))
    r=report_result();r.NSCSingleRayTraceData=NS(IsValid=True,NumberOfSegments=1)
    monkeypatch.setattr(na,'read_segment',lambda *args:out)
    with pytest.raises(ZemaxError)as caught:na.collect_single(backend,t,r)
    assert caught.value.code=='RESULT_READ_FAILED' and caught.value.details['native_segment_index']==1

def test_invalid_native_analysis(backend):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'));r=report_result();r.IsValid=False
    backend.tool.GetResults=lambda:r
    with pytest.raises(ZemaxError)as caught:t['collector'](t)
    assert caught.value.code=='ANALYSIS_FAILED'

def test_relative_single_database_resolves_beside_model(backend,monkeypatch):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'))
    database=backend.directory/'ray.zrd';database.write_bytes(b'fixture')
    r=report_result();r.NSCSingleRayTraceData=NS(IsValid=True,NumberOfSegments=0,WaveIndex=1,WavelengthUM=.55,ZRDFile='ray.zrd')
    data=na.collect_single(backend,t,r)
    assert {'kind':'zrd','path':str(database)} in data['artifacts']

def test_saved_database_precedes_missing_native_temporary(backend):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'))
    database=Path(t['settings']['database_output_path']);database.write_bytes(b'fixture')
    r=report_result();r.NSCSingleRayTraceData=NS(IsValid=True,NumberOfSegments=0,WaveIndex=1,WavelengthUM=.55,ZRDFile='expired.zrd')
    data=na.collect_single(backend,t,r)
    assert {'kind':'zrd','path':str(database)} in data['artifacts']
    assert data['database_path_source']=='adopted_SaveRaysFile' and data['native_database_file']=='expired.zrd'

@pytest.mark.parametrize('collector,property_name',[(na.collect_single,'NSCSingleRayTraceData'),(na.collect_critical,'CriticalRayData')])
def test_missing_dedicated_result_keeps_native_export(backend,collector,property_name):
    t=na.run_nsc_analysis(backend,NscSingleRayTrace(kind='nsc_single_ray_trace'))
    r=report_result();setattr(r,property_name,None);r.HeaderData=None
    with pytest.raises(ZemaxError)as caught:collector(backend,t,r)
    assert caught.value.code=='RESULT_UNAVAILABLE'
    assert caught.value.details['native_report']['native_export_error']=='GetTextFile returned false'
