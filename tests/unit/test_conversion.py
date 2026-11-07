"""Conversion scopes, dependency ordering, native readback and ownership."""
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.conversion_models import NscConversion
from zemax_mcp import conversion as cv
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[
    dict(first_surface=0),dict(first_surface=3,last_surface=2),dict(mode='group',create_sources_and_detectors=True),
    dict(overfill_factor=1.1),dict(overfill_factor=0,mode='pure',create_sources_and_detectors=True),
    dict(convert_stop_to_nsc_aperture=False,stop_mechanical_half_width=1),dict(stop_mechanical_half_width=float('nan')),
])
def test_invalid_conversion_requests(payload):
    with pytest.raises(ValidationError):NscConversion(**payload)

@pytest.mark.parametrize('mode',['group','pure'])
def test_conversion_defaults_roundtrip(mode):
    q=NscConversion(mode=mode)
    assert NscConversion.model_validate(q.model_dump())==q

class B(cv.ConversionMixin):
    def __init__(self):
        self.events=[];self.closed=[];self.revision=0;self.last_checkpoint=None;self.native=None
        self.tool=NS(Succeeded=True,ErrorMessage='',StopObjectNumber=1,StopObjectFace=0)
        self.system=NS(LDE=NS(NumberOfSurfaces=6),Tools=NS(OpenConvertToNSCGroup=lambda:self.tool))
        self.scene='Sequential';self.new_group=False
        self.system_context={'mode':'Sequential'};self.detector_history_known=True;self.detector_records={'old':1}
    def _require_sequential(self):pass
    def _mutate(self,label):self.events.append('checkpoint');self.last_checkpoint='baseline';self.revision+=1
    def _close_task_native(self,t):self.closed.append(t['native']);return True
    def _start_task(self,kind,tool,settings,**kwargs):self.events.append('start');self.settings=settings;self.collector=kwargs['collector'];return dict(kind=kind)
    def get_system_settings(self,_):self.system_context={'mode':self.scene}

def snapshot(b):
    return dict(mode=b.scene,nsc_groups=[1]if b.new_group else[],object_count=3)

@pytest.fixture
def adapted(monkeypatch):
    monkeypatch.setattr(cv,'scene_snapshot',snapshot)
    def checked(n,t,k,v):setattr(t,k,v)
    monkeypatch.setattr(cv,'checked_setting',checked)
    monkeypatch.setattr(cv,'check_setting_readback',lambda t,k,v:None if getattr(t,k)==v else(_ for _ in ()).throw(ZemaxError('SETTING_REJECTED','drift')))
    monkeypatch.setattr(cv,'scalar_settings',lambda t:{k:v for k,v in vars(t).items()if isinstance(v,(int,float,str,bool))})
    return B()

@pytest.mark.parametrize('q',[
    NscConversion(first_surface=5),NscConversion(last_surface=5),
    NscConversion(mode='pure',create_sources_and_detectors=True,first_surface=2),
])
def test_scope_rejected_before_checkpoint(adapted,q):
    with pytest.raises(ZemaxError):adapted.run_nsc_conversion(q)
    assert adapted.revision==0 and adapted.closed==[]

@pytest.mark.parametrize('mode',['group','pure'])
def test_settings_checkpoint_and_collection(adapted,mode):
    b=adapted;q=NscConversion(mode=mode)
    result=b.run_nsc_conversion(q)
    assert result['kind']=='nsc_conversion'and b.events==['checkpoint','start']
    assert b.tool.LastSurface==4 and b.tool.ConvertFileToNSC==(mode=='pure')
    b.scene='NonSequential'if mode=='pure'else'Sequential';b.new_group=mode=='group'
    data=b.collector(dict(native=b.tool))
    assert data['checkpoint']=='baseline' and data['after']['mode']==b.scene and b.closed==[b.tool]
    assert b.detector_history_known is False and b.detector_records=={}

def test_full_generation_dependencies(adapted):
    b=adapted;b.run_nsc_conversion(NscConversion(mode='pure',create_sources_and_detectors=True))
    assert b.tool.FirstSurface==1 and b.tool.LastSurface==4 and b.tool.OverfillFactor==1.2

def test_settings_failure_closes_tool(adapted,monkeypatch):
    monkeypatch.setattr(cv,'checked_setting',lambda *args:(_ for _ in ()).throw(RuntimeError('original native error')))
    with pytest.raises(RuntimeError,match='original native error'):adapted.run_nsc_conversion(NscConversion())
    assert adapted.closed==[adapted.tool]and adapted.revision==1

@pytest.mark.parametrize('mode',['group','pure'])
def test_mismatched_conversion_result_is_rejected(adapted,mode):
    b=adapted;b.run_nsc_conversion(NscConversion(mode=mode))
    with pytest.raises(ZemaxError)as exc:b.collector(dict(native=b.tool))
    assert exc.value.code=='CONVERSION_NOT_APPLIED'and b.closed==[b.tool]

def test_native_failed_conversion_preserves_reason(adapted):
    b=adapted;b.run_nsc_conversion(NscConversion());b.tool.Succeeded=False;b.tool.ErrorMessage='unsupported surface'
    with pytest.raises(ZemaxError)as exc:b.collector(dict(native=b.tool))
    assert exc.value.code=='TASK_FAILED'and str(exc.value)=='unsupported surface'


def test_settings_final_readback_detects_scope_reset(monkeypatch):
    b=B()
    def setter(n,t,key,value):
        setattr(t,key,value)
        if key=='LastSurface':t.FirstSurface=2
    monkeypatch.setattr(cv,'checked_setting',setter)
    with pytest.raises(ZemaxError)as exc:cv.configure(b,b.tool,NscConversion(),4)
    assert exc.value.code=='SETTING_REJECTED'


def test_failed_setup_invalidates_model_context(adapted,monkeypatch):
    monkeypatch.setattr(cv,'configure',lambda *args:(_ for _ in ()).throw(RuntimeError('setup failure')))
    with pytest.raises(RuntimeError):adapted.run_nsc_conversion(NscConversion())
    assert adapted.system_context=={} and not adapted.detector_history_known and not adapted.detector_records

def test_setup_and_close_errors_both_preserved(adapted,monkeypatch):
    monkeypatch.setattr(cv,'configure',lambda *args:(_ for _ in ()).throw(RuntimeError('original setup failure')))
    def close(t):t['cleanup_warnings']=['original close failure'];return False
    adapted._close_task_native=close
    with pytest.raises(ZemaxError)as caught:adapted.run_nsc_conversion(NscConversion())
    assert str(caught.value)=='original setup failure'
    assert caught.value.details['cleanup_warnings']==['original close failure']
