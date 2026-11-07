import pytest
from pydantic import ValidationError
from zemax_mcp.models import SystemPatch,SurfacePatch

@pytest.mark.parametrize('value',[{}, {'advanced':{}},{'aperture_options':{'apodization_factor':float('inf')}}])
def test_invalid_system_page(value):
    with pytest.raises(ValidationError):SystemPatch.model_validate(value)

@pytest.mark.parametrize('value',[{'scattering':{'type':'Gaussian','scatter_fraction':2,'sigma':1}},{'drawing':{}},{'aperture':{'type':'Spider','number_of_arms':3}}])
def test_invalid_surface_page(value):
    with pytest.raises(ValidationError):SurfacePatch(surface=1,**value)

def test_page_roundtrip():
    p=SurfacePatch(surface=1,physical_optics={'resample_after_refraction':True,'x_sampling':'S64'})
    assert SurfacePatch.model_validate(p.model_dump(exclude_unset=True))==p
