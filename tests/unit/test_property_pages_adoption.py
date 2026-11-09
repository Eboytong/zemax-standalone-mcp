from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.models import AperturePatch,SurfacePatch
from zemax_mcp.property_pages import apply_pages,SURFACE_PAGES
from zemax_mcp.scattering_pages import settings,set_scattering,Lambertian
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('patch',[
 {'type':'None','maximum_radius':2}, {'pickup_from':2,'x_decenter':1},
 {'type':'Spider','width_of_arms':.2,'number_of_arms':4,'maximum_radius':2},
 {'type':'CircularAperture','maximum_radius':2,'x_half_width':1},
 {'type':'RectangularAperture','x_half_width':2,'y_half_width':1,'minimum_radius':.1},
 {'type':'UserAperture','aperture_file':'square.uda','maximum_radius':2},
 {'type':'FloatingAperture','x_decenter':1}])
def test_aperture_rejects_ignored_parameters(patch):
    with pytest.raises(ValidationError):AperturePatch(**patch)

@pytest.mark.parametrize('extra',[{'resample_after_refraction':False,'x_sampling':'S64'},{'auto_resample':True,'x_width':1}])
def test_pop_dependency_rejected_before_write(extra):
    target=N(ResampleAfterRefraction=True,AutoResample=False)
    row=N(PhysicalOpticsData=target)
    req=SurfacePatch(surface=1,physical_optics=extra)
    with pytest.raises(ZemaxError)as error:apply_pages(None,row,req,SURFACE_PAGES,validate=True)
    assert error.value.code=='UNSUPPORTED_SETTING'
    assert vars(target)=={'ResampleAfterRefraction':True,'AutoResample':False}

@pytest.mark.parametrize('message,kind,expected',[
 ('UILDEScatterData not marked serializable','User','UNSUPPORTED_SETTING'),
 ('unrelated native failure','User',None),
 ('UILDEScatterData not marked serializable','BSDF',None)])
def test_only_known_user_serialization_classified(message,kind,expected):
    def create(_):raise RuntimeError(message)
    native=N(api=N(Editors=N(LDE=N(SurfaceScatteringTypes=object()))),enum=lambda _,v:v)
    row=N(ScatteringData=N(CreateScatteringTypeSettings=create))
    with pytest.raises(ZemaxError if expected else RuntimeError)as error:settings(native,row,kind)
    if expected:
        assert error.value.code==expected
        assert error.value.details['native_error']==message


def test_scatter_preflight_does_not_apply_or_change_active_settings():
    prop=N(PropertyType=N(IsEnum=False,FullName="System.Double"),CanWrite=True)
    detached=N(ScatterFraction=.1,GetType=lambda:N(GetProperty=lambda _:prop))
    active=N(ScatterFraction=.2)
    applied=[]
    data=N(CurrentType='Lambertian',CurrentTypeSettings=N(_S_Lambertian=active),
           CreateScatteringTypeSettings=lambda _:N(_S_Lambertian=detached),
           ChangeScatteringTypeSettings=lambda value:applied.append(value))
    native=N(api=N(Editors=N(LDE=N(SurfaceScatteringTypes=object()))),enum=lambda _,v:v)
    set_scattering(native,N(ScatteringData=data),Lambertian(type='Lambertian',scatter_fraction=.3),validate=True)
    assert not applied and active.ScatterFraction==.2


def test_final_page_state_detects_later_setter_overwriting_earlier_value():
    class Interference:
        DoNotDrawThisSurface=False
        @property
        def DrawLocalAxis(self):return True
        @DrawLocalAxis.setter
        def DrawLocalAxis(self,v):self.DoNotDrawThisSurface=False
        def GetType(self):return N(GetProperty=lambda _:N(CanWrite=True,PropertyType=N(IsEnum=False,FullName="System.Boolean")))
    req=SurfacePatch(surface=1,drawing={'do_not_draw_this_surface':True,'draw_local_axis':True})
    with pytest.raises(ZemaxError)as error:apply_pages(None,N(DrawData=Interference()),req,SURFACE_PAGES)
    assert error.value.code=='SETTING_REJECTED'


def test_bsdf_native_abgf_list_is_capability_error():
    from zemax_mcp.scattering_pages import resource_names
    with pytest.raises(ZemaxError)as error:resource_names(N(GetAvailableFileNames=lambda:['ED01.ABGF']),'BSDF')
    assert error.value.code=='UNSUPPORTED_SETTING'
    assert error.value.details['native_filenames']==['ED01.ABGF']


@pytest.mark.parametrize('names',[[],['无'],['BrownVinyl.bsdf','ED01.ABGF']])
def test_bsdf_resource_list_requires_unambiguous_native_bsdf_names(names):
    from zemax_mcp.scattering_pages import resource_names
    with pytest.raises(ZemaxError)as error:resource_names(N(GetAvailableFileNames=lambda:names),'BSDF')
    assert error.value.code=='UNSUPPORTED_SETTING'
    assert error.value.details['native_filenames']==names


def test_bsdf_resource_list_returns_only_native_bsdf_files():
    from zemax_mcp.scattering_pages import resource_names
    obj=N(GetAvailableFileNames=lambda:['BrownVinyl.bsdf','MetalVelvet_VIS.bsdf'])
    assert resource_names(obj,'BSDF')==['BrownVinyl.bsdf','MetalVelvet_VIS.bsdf']
