"""NSC MTF sampling, source identity and dedicated final settings."""
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.path_models import NscGeometricMtf
from zemax_mcp import nsc_mtf as nm
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[dict(detector=0),dict(filter='H2'),dict(maximum_frequency=-1),dict(maximum_frequency=float('nan')),dict(minimum_plot_scale=1),dict(minimum_plot_scale=2,maximum_plot_scale=1),
    dict(frequencies=[]),dict(frequencies=[0,.1,.1]),dict(frequencies=[.2,.1]),dict(frequencies=[-1]),
    dict(frequencies=[float('nan')]),dict(frequencies=[.1],maximum_frequency=.2),dict(frequencies=list(range(302)))])
def test_invalid_requests(payload):
    with pytest.raises(ValidationError):NscGeometricMtf.model_validate(dict(kind='nsc_geometric_mtf',detector=2)|payload)

class Detector:
    def SetDetectorNumber(self,n):self.n=n
    def GetDetectorNumber(self):return self.n

class B:
    def __init__(self,tmp):
        self.directory=tmp;self.closed=[];self.native=None
        self.object=NS(Type='DetectorRectangle',ObjectData=NS(PsfWaveNumber=0,NumberXPixels=7,NumberYPixels=5,XHalfWidth=1,YHalfWidth=2))
        self.system=NS(SystemFile=str(tmp/'work.zos'),UpdateFileLists=lambda:None,SystemData=NS(Units=NS(LensUnits='Millimeters')))
        self.settings=NS(Detector=Detector());self.tool=NS(GetSettings=lambda:self.settings)
    def _object(self,n):return self.object
    def _require_nsc(self):pass
    def _require_work(self):pass
    def _detector_provenance(self,n):return dict(history_known=False,trace_history=[])
    def _close_task_native(self,t):self.closed.append(t['native']);return True
    def _start_task(self,kind,tool,settings,**kw):self.task=dict(kind=kind,native=tool,settings=settings,**kw);return self.task

@pytest.fixture
def backend(tmp_path,monkeypatch):
    b=B(tmp_path)
    monkeypatch.setattr(nm,'new_analysis',lambda *args:b.tool)
    monkeypatch.setattr(nm,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(nm,'check',lambda n,s,k,v:None if getattr(s,k)==v else (_ for _ in ()).throw(ZemaxError('SETTING_REJECTED','drift')))
    monkeypatch.setattr(nm,'scalar_settings',lambda s:{k:v for k,v in vars(s).items()if k!='Detector'})
    monkeypatch.setattr(nm,'collect_imaging',lambda *args:dict(series=[dict(labels=['X','Y'],x=[0,.1],y=[[1,1],[.5,.6]])]))
    return b

@pytest.mark.parametrize('unit,factor',[('Millimeters',1),('Centimeters',10),('Inches',25.4),('Meters',1000)])
def test_rectangular_nyquist_uses_mm(backend,unit,factor):
    backend.system.SystemData.Units.LensUnits=unit
    d=nm.detector_sampling(backend,2)
    assert d['nyquist_cycles_per_mm']==pytest.approx(.625/factor)
    assert d['x_pixel_width_mm']==pytest.approx(2*factor/7)

@pytest.mark.parametrize('attribute,value,code',[('PsfWaveNumber',1,'CONDITION_NOT_MET'),('NumberXPixels',0,'INVALID_DETECTOR_DATA'),('XHalfWidth',float('nan'),'INVALID_DETECTOR_DATA')])
def test_invalid_detector_sampling(backend,attribute,value,code):
    setattr(backend.object.ObjectData,attribute,value)
    with pytest.raises(ZemaxError)as caught:nm.detector_sampling(backend,2)
    assert caught.value.code==code

def test_wrong_detector_type(backend):
    backend.object.Type='DetectorPolar'
    with pytest.raises(ZemaxError)as caught:nm.detector_sampling(backend,2)
    assert caught.value.code=='UNSUPPORTED_DETECTOR'

def test_beyond_nyquist_rejected_before_open(backend):
    with pytest.raises(ZemaxError)as caught:nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2,maximum_frequency=1))
    assert caught.value.code=='SAMPLING_LIMIT' and not backend.closed

def test_accumulation_provenance_and_final_settings(backend):
    t=nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2))
    assert t['settings']['native']['RayDatabaseFilename']=='' and backend.settings.Detector.n==2
    assert t['settings']['provenance']['source']=='current accumulated detector'
    data=t['collector'](t)
    assert data['frequency_unit']=='cycles/mm' and data['series'][0]['value_units']==['dimensionless MTF']*2
    assert data['direction_axes']=={'Tangential':'detector local Y','Sagittal':'detector local X'}

def test_database_staged_and_filter_adopted(backend):
    path=backend.directory/'input.zrd';path.write_bytes(b'fixture')
    t=nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2,path=str(path),filter='H2'))
    assert t['settings']['native']['Filter']=='H2' and backend.settings.RayDatabaseFilename.startswith('nsc_mtf_')
    assert t['settings']['provenance']['source_file']==str(path)

@pytest.mark.parametrize('phase',['checked','check'])
def test_setting_failure_closes(backend,monkeypatch,phase):
    def fail(*args):raise RuntimeError('native failure')
    monkeypatch.setattr(nm,phase,fail)
    with pytest.raises(RuntimeError,match='native failure'):nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2))
    assert backend.closed==[backend.tool]

def test_missing_curves_keeps_result_source(backend,monkeypatch):
    monkeypatch.setattr(nm,'collect_imaging',lambda *args:dict(series=[],artifacts=['native table']))
    t=nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2))
    with pytest.raises(ZemaxError)as caught:t['collector'](t)
    assert caught.value.code=='RESULT_UNAVAILABLE' and caught.value.details['artifacts']==['native table']


def test_native_endpoint_selection_preserves_raw_values_and_zero_node():
    curves=[dict(labels=['Tangential','Sagittal'],x=[0,.1],y=[[1.,1.],[.5,.6]])]
    assert nm.endpoint_values(curves,.1)[0]['values']==[.5,.6]
    assert nm.endpoint_values(curves,0)[0]['values']==[1.,1.]
    assert nm.endpoint_values(curves,.1)[0]['native_node']==1


@pytest.mark.parametrize('curve,frequency,code',[
    (dict(labels=['T'],x=[0,.1],y=[[1],[.5]]),.2,'FREQUENCY_MAPPING_FAILED'),
    (dict(labels=['T'],x=[0],y=[]),0,'INVALID_RESULT_DATA'),
    (dict(labels=['T'],x=[0],y=[[float('nan')]]),0,'INVALID_RESULT_DATA'),
    (dict(labels=['T'],x=[0],y=[[None]]),0,'INVALID_RESULT_DATA')])
def test_endpoint_mapping_and_invalid_data(curve,frequency,code):
    with pytest.raises(ZemaxError)as exc:nm.endpoint_values([curve],frequency)
    assert exc.value.code==code


def test_endpoint_composite_preserves_queries_series_and_pagination_rows(backend):
    calls=[];task=dict(payload={},rows=[])
    def child_job(parent,method,q):
        calls.append(q)
        yield
        return dict(task=dict(task_id='child'+str(len(calls)),settings=dict(native=dict(MaximumFrequency=q.maximum_frequency))),
            provenance=dict(source='current accumulation'),
            series=[dict(labels=['Tangential','Sagittal'],x=[0,q.maximum_frequency or .625],
                y=[[1.,1.],[.5,.6]],x_unit='cycles/mm')])
    backend._child_job=child_job;backend._cancel_boundary=lambda task:None
    def composite(kind,settings,flow,require_sequential):
        assert require_sequential is False
        for _ in flow(task):pass
        return task
    backend._composite=composite
    result=nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2,frequencies=[0,.1,.3]))
    assert all(q.frequencies is None for q in calls)
    assert result['payload']['series'][0]['x']==[0,.1,.3]
    assert result['payload']['series'][0]['y']==[[1.,1.],[.5,.6],[.5,.6]]
    assert len(result['rows'])==3 and result['progress']==100
    assert result['rows'][1]['actual_settings']['MaximumFrequency']==.1


def test_endpoint_limit_rejected_before_task_or_native_open(backend):
    with pytest.raises(ZemaxError)as exc:
        nm.run_nsc_mtf(backend,NscGeometricMtf(kind='nsc_geometric_mtf',detector=2,frequencies=[.7]))
    assert exc.value.code=='SAMPLING_LIMIT'and not backend.closed
