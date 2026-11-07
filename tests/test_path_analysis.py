"""Native path settings and result contracts with asymmetric native arrays."""
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.path_models import PathAnalysis
from zemax_mcp import path_analysis as pa
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[
    dict(first_ray=0),dict(first_ray=True),dict(last_ray=0),dict(last_ray=-2),dict(first_ray=3,last_ray=2),
    dict(relative_minimum_flux=-.1),dict(relative_minimum_flux=1.1),dict(relative_minimum_flux=float('nan')),
    dict(sort_by='NumberOfUniqueObjectsStruct'),dict(path='data.paf',filter='H2'),dict(extra=1),
])
def test_invalid_path_requests(payload):
    with pytest.raises(ValidationError):PathAnalysis.model_validate(dict(kind='path_analysis',path='data.zrd')|payload)

@pytest.mark.parametrize('last',[-1,1,20])
def test_native_ray_range_sentinels(last):
    assert PathAnalysis(kind='path_analysis',path='data.zrd',last_ray=last).last_ray==last

class Matrix:
    Rank=2
    def __init__(self,rows):self.rows=rows
    def GetLength(self,i):return len(self.rows)if i==0 else len(self.rows[0])
    def __getitem__(self,ij):return self.rows[ij[0]][ij[1]]

def entry(number=1):
    return NS(PathNumber=number,RaysInPath=4,HitsInPath=8,GhostsInPath=0,UniqueObjectsInPath=3,
        TotalPathFlux=.7,NumberOfObjectsInPath=3,PathObjectList=[1,2,3],PathObjectAndFaceList=Matrix([[1,0],[2,1],[3,0]]),PathSource=1)

def result():
    data=NS(NumPaths=1,Paths=[entry()],PathNumber=1,PathBranches=4,LastObject=3,LastFace=0,PathFluxOut=.7,
        PathFluxPercent=70,PathSource=1,PathSequence='1.0, 2.1, 3.0',GetPathUncategorized=lambda:entry(0),TotalFluxIn=1,TotalFluxOut=.9,TotalRays=4,TotalHits=8)
    return NS(IsValid=True,PathAnalysisData=data,HeaderData=NS(Lines=['path header']),NumberOfMessages=0,GetTextFile=lambda p:False)

class B:
    def __init__(self,tmp):
        self.directory=tmp;self.closed=[];self.events=[];self.native=None
        self.settings=NS(AvailableRayDatabaseFiles=[])
        def update():self.settings.AvailableRayDatabaseFiles=[p.name for p in tmp.glob('path_*')]
        self.system=NS(SystemFile=str(tmp/'working.zos'),UpdateFileLists=update)
        self.tool=NS(GetSettings=lambda:self.settings,GetResults=result)
    def _require_nsc(self):self.events.append('nsc')
    def _require_work(self):self.events.append('work')
    def _mutate(self,name):self.events.append('checkpoint:'+name)
    def _close_task_native(self,t):self.closed.append(t['native']);return True
    def _start_task(self,kind,tool,settings,**kwargs):self.task=dict(task_id='a',kind=kind,native=tool,settings=settings,**kwargs);return self.task

@pytest.fixture
def backend(tmp_path,monkeypatch):
    b=B(tmp_path)
    monkeypatch.setattr(pa,'new_analysis',lambda *args:b.tool)
    monkeypatch.setattr(pa,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(pa,'check',lambda n,s,k,v:None if getattr(s,k)==v else (_ for _ in ()).throw(ZemaxError('SETTING_REJECTED','setting drift')))
    monkeypatch.setattr(pa,'scalar_settings',lambda s:{k:v for k,v in vars(s).items()if k!='AvailableRayDatabaseFiles'})
    (tmp_path/'input.zrd').write_bytes(b'local fixture')
    return b

def request(b,**kw):return PathAnalysis(kind='path_analysis',path=str(b.directory/'input.zrd'),**kw)

def test_staging_resource_readback_and_enum_alias(backend):
    b=backend;t=pa.run_path_analysis(b,request(b,sort_by='NumberOfUniqueObjectsStruck'))
    assert b.settings.SortBy=='NumberOfUniqueObjectsStruct'
    assert b.settings.FirstRay==1 and b.settings.LastRay==-1
    assert b.settings.RayDatabaseFile.startswith('path_')
    assert Path(t['settings']['working_database']).is_file()
    assert not b.closed and b.events==['nsc','work']

@pytest.mark.parametrize('generate',[False,True])
def test_generated_filters_revision_condition(backend,generate):
    b=backend;pa.run_path_analysis(b,request(b,generate_path_filters=generate))
    assert any(x.startswith('checkpoint:')for x in b.events)==generate

@pytest.mark.parametrize('phase',['set','final'])
def test_setting_rejection_closes_analysis(backend,monkeypatch,phase):
    def fail(*args):raise ZemaxError('SETTING_REJECTED','original setting failure')
    monkeypatch.setattr(pa,'checked'if phase=='set'else'check',fail)
    with pytest.raises(ZemaxError,match='original setting failure'):pa.run_path_analysis(backend,request(backend))
    assert backend.closed==[backend.tool]

def test_resource_not_listed_closes_analysis(backend):
    backend.system.UpdateFileLists=lambda:None
    with pytest.raises(ZemaxError)as caught:pa.run_path_analysis(backend,request(backend))
    assert caught.value.code=='INVALID_RESOURCE' and backend.closed==[backend.tool]

def test_input_missing_before_analysis_open(backend):
    q=PathAnalysis(kind='path_analysis',path=str(backend.directory/'missing.zrd'))
    with pytest.raises(ZemaxError)as caught:pa.run_path_analysis(backend,q)
    assert caught.value.code=='INVALID_INPUT_FILE' and not backend.closed

def test_path_rows_and_uncategorized_retained(backend):
    t=pa.run_path_analysis(backend,request(backend));data=t['collector'](t)
    assert data['rows'][0]['path_sequence']=='1.0, 2.1, 3.0'
    assert data['rows'][0]['native_object_face_shape']==[3,2]
    assert data['rows'][0]['native_object_face_matrix']==[[1,0],[2,1],[3,0]]
    assert data['uncategorized']['category']=='uncategorized'
    assert data['units']['flux']=='W' and data['summary']['total_flux_out_w']==.9
    assert data['native_export_error']=='GetTextFile returned false'

@pytest.mark.parametrize('mutation,code',[
    (lambda r:setattr(r,'IsValid',False),'ANALYSIS_FAILED'),
    (lambda r:setattr(r,'PathAnalysisData',None),'RESULT_UNAVAILABLE'),
    (lambda r:setattr(r.PathAnalysisData,'NumPaths',10001),'RESULT_TOO_LARGE'),
    (lambda r:setattr(r.PathAnalysisData,'NumPaths',2),'INVALID_RESULT_DATA'),
    (lambda r:setattr(r.PathAnalysisData,'TotalFluxIn',float('nan')),'INVALID_RESULT_DATA'),
    (lambda r:setattr(r.PathAnalysisData.Paths[0],'NumberOfObjectsInPath',4),'INVALID_RESULT_DATA'),
    (lambda r:setattr(r.PathAnalysisData.Paths[0],'PathObjectAndFaceList',Matrix([[1,2,3],[1,2,3],[1,2,3]])),'INVALID_RESULT_DATA'),
])
def test_invalid_results_keep_error_source(backend,mutation,code):
    r=result();mutation(r);backend.tool.GetResults=lambda:r
    t=pa.run_path_analysis(backend,request(backend))
    with pytest.raises(ZemaxError)as caught:t['collector'](t)
    assert caught.value.code==code

def test_duplicate_native_paths_rejected(backend):
    r=result();r.PathAnalysisData.Paths=[entry(),entry()];r.PathAnalysisData.NumPaths=2
    backend.tool.GetResults=lambda:r;t=pa.run_path_analysis(backend,request(backend))
    with pytest.raises(ZemaxError)as caught:t['collector'](t)
    assert caught.value.code=='INVALID_RESULT_DATA'

def test_empty_classified_paths_keep_uncategorized(backend):
    r=result();r.PathAnalysisData.Paths=[];r.PathAnalysisData.NumPaths=0
    backend.tool.GetResults=lambda:r;t=pa.run_path_analysis(backend,request(backend));data=t['collector'](t)
    assert data['rows']==[] and data['uncategorized']

def test_native_object_list_may_deduplicate_repeated_face_hits(backend):
    r=result();row=r.PathAnalysisData.Paths[0]
    row.NumberOfObjectsInPath=4
    row.PathObjectAndFaceList=Matrix([[1,0],[2,1],[2,2],[3,0]])
    r.PathAnalysisData.PathSequence='1.0, 2.1, 2.2, 3.0'
    backend.tool.GetResults=lambda:r
    t=pa.run_path_analysis(backend,request(backend));data=t['collector'](t)
    assert data['rows'][0]['object_count']==4
    assert data['rows'][0]['objects']==[1,2,3]
    assert data['rows'][0]['native_object_list_length']==3

def test_native_export_exception_keeps_structured_paths(backend):
    r=result()
    def fail(_):raise RuntimeError('original export failure')
    r.GetTextFile=fail;backend.tool.GetResults=lambda:r
    t=pa.run_path_analysis(backend,request(backend));data=t['collector'](t)
    assert data['rows'] and data['native_export_error']['message']=='original export failure'

@pytest.mark.parametrize('message',['There are no uncategorized paths.','database read failed'])
def test_uncategorized_absence_preserves_other_native_errors(backend,message):
    r=result()
    def fail():raise RuntimeError(message)
    r.PathAnalysisData.GetPathUncategorized=fail
    backend.tool.GetResults=lambda:r
    t=pa.run_path_analysis(backend,request(backend))
    if message=='There are no uncategorized paths.':
        data=t['collector'](t)
        assert data['uncategorized'] is None and data['uncategorized_native_message']==message
        assert data['rows']
    else:
        with pytest.raises(RuntimeError,match=message):t['collector'](t)

def test_setup_failure_and_cleanup_failure_preserved(backend,monkeypatch):
    def fail(*args):raise RuntimeError('original failure')
    monkeypatch.setattr(pa,'checked',fail)
    def close(t):t['cleanup_warnings']=['close failure'];return False
    backend._close_task_native=close
    with pytest.raises(ZemaxError)as caught:pa.run_path_analysis(backend,request(backend))
    assert str(caught.value)=='original failure' and caught.value.details['cleanup_warnings']==['close failure']
