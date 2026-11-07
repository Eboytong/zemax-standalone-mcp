"""Final combinations use enum-aware readback; error snapshots preserve original failures."""
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.nsc_models import ObjectPatch
from zemax_mcp import nsc_state as ns
from zemax_mcp.errors import ZemaxError
from zemax_mcp.detectors import check_setting_readback

@pytest.fixture(autouse=True)
def scalar_readback(monkeypatch):
    monkeypatch.setattr(ns,'check',lambda n,o,k,v:check_setting_readback(o,k,v))

def test_final_numeric_field_and_no_unrequested_pages():
    ns.verify_patch(NS(native=None),NS(RefObject=1),ObjectPatch(object=2,ref_object=1),dict(ref_object='RefObject'))

def test_final_combination_rejects_changed_prior_setting():
    with pytest.raises(ZemaxError)as caught:ns.verify_patch(NS(native=None),NS(RefObject=0),ObjectPatch(object=2,ref_object=1),dict(ref_object='RefObject'))
    assert caught.value.details['object']==2 and caught.value.details['page']=='object'

def test_final_face_settings_and_ray_count():
    face=NS(Coating='AR',NumberOfRays=7,CurrentScatterModel='Lambertian',CurrentScatterModelSettings=NS(_S_Lambertian=NS(ScatterFraction=.2)))
    row=NS(CoatScatterData=NS(GetFaceData=lambda n:face))
    patch=ObjectPatch(object=2,faces=[dict(face=0,coating='AR',number_of_rays=7,scatter_model='Lambertian',settings=dict(ScatterFraction=.2))])
    ns.verify_patch(NS(native=None),row,patch,{})
    face.CurrentScatterModelSettings._S_Lambertian.ScatterFraction=.3
    with pytest.raises(ZemaxError)as caught:ns.verify_patch(NS(native=None),row,patch,{})
    assert caught.value.details['property']=='ScatterFraction'

def test_failed_snapshot_preserves_original_native_error():
    def fail(n):raise RuntimeError('state unavailable')
    original=RuntimeError('original native write failure')
    err=ns.failure(NS(last_checkpoint='baseline',_object=fail),original,3,[1,2],[1,2,3],'write_properties')
    assert str(err)=='original native write failure' and err.details['failed_object_state_error']['message']=='state unavailable'
    assert err.details['completed_objects']==[1,2] and err.details['prepared_objects']==[1,2,3]

def test_failed_page_snapshot_keeps_error(monkeypatch):
    def fail(obj):raise RuntimeError('cannot read page')
    monkeypatch.setattr(ns,'scalar_settings',fail)
    original=ZemaxError('SETTING_REJECTED','failed setting',property='X')
    err=ns.failure(NS(last_checkpoint='baseline',_object=lambda n:NS(ObjectData=None)),original,2,[1],[1,2],'final_readback')
    assert err is original and err.details['property']=='X' and err.details['failed_object_state']['object']['unavailable']=='cannot read page'

def test_final_volume_parameters():
    setting=NS(Range=1,GetParameterValue=lambda i:3)
    row=NS(VolumePhysicsData=NS(Model='DLLDefinedScattering',ModelSettings=NS(_S_DLLDefinedScattering=setting)))
    ns.verify_patch(NS(native=None),row,ObjectPatch(object=1,volume=dict(model='DLLDefinedScattering',settings=dict(Range=1),parameters={0:3})),{})

def test_final_spectrum_settings():
    row=NS(SourcesData=NS(SourceColor='Wavelength',SourceColorSettings=NS(_S_Wavelength=NS(Wavelength=.55))))
    ns.verify_patch(NS(native=None),row,ObjectPatch(object=1,spectrum=dict(mode='Wavelength',settings=dict(Wavelength=.55))),{})
