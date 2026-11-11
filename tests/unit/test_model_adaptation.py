import math
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.models import GetSurfaces,SurfacePatch,Variable
from zemax_mcp.nsc_models import DetectorRead,ObjectPatch
from zemax_mcp.pupil import display_inverse,real_f_numbers
from zemax_mcp.facets import read_facet_geometry
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('i',[21,100,254])
def test_lde_high_parameter_models(i):
    p=SurfacePatch(surface=1,parameters={i:.1},solves={f'parameter_{i}':dict(mode='variable')})
    assert p.parameters[i]==.1
    assert GetSurfaces(parameter_start=i,parameter_count=1).parameter_start==i


@pytest.mark.parametrize('i',[0,255])
def test_lde_parameter_outside_installed_bounds(i):
    with pytest.raises(ValidationError):SurfacePatch(surface=1,parameters={i:.1})


def test_nce_high_parameter_model():
    assert ObjectPatch(object=1,parameters={250:1}).parameters[250]==1
    with pytest.raises(ValidationError):ObjectPatch(object=1,parameters={251:1})


def test_inverse_single_value_and_domain():
    p=display_inverse(.2,-.4,[1,1.2])
    assert p['px']==pytest.approx(.2)and p['py']==pytest.approx(-.48)
    assert p['coordinate_error']<=1e-15 and p['iterations']<=20 and p['valid']
    assert not display_inverse(1,1,[1,1])['valid']


def test_f_number_from_real_geometry():
    v=.1;z=math.sqrt(1-v*v)
    rows=[dict(error_code=0,direction=d)for d in ([0,0,1],[v,0,z],[-v,0,z],[0,v,z],[0,-v,z])]
    assert real_f_numbers(rows)==pytest.approx([5,5])
    rows[1]['error_code']=2
    with pytest.raises(ZemaxError):real_f_numbers(rows)


class Facets:
    CurrentFace=0;ConvertToGlobal=False;NumberOfFaces=1;NumberOfVertices=3;Flux=1;Irradiance=2
    def GetVertex(self,i,*_):return True,*[(0,0,0),(1,0,0),(0,1,0)][i]
    def GetVertexNormal(self,i,*_):return True,0,0,1


def test_facet_vertices_area_and_cursor_restored():
    f=Facets();r=read_facet_geometry(N(GetFacetedObjectData=lambda:f),'global')
    assert r[0]['area']==.5 and r[0]['centroid']==pytest.approx([1/3,1/3,0])
    assert f.CurrentFace==0 and not f.ConvertToGlobal


@pytest.mark.parametrize('case',['vertex_false','nonfinite','degenerate','nontriangle'])
def test_facet_failure_restores_cursor(case):
    f=Facets()
    if case=='vertex_false':f.GetVertex=lambda *_:(False,0,0,0)
    if case=='nonfinite':f.GetVertex=lambda *_:(True,float('nan'),0,0)
    if case=='degenerate':f.GetVertex=lambda *_:(True,0,0,0)
    if case=='nontriangle':f.NumberOfVertices=4
    with pytest.raises(ZemaxError):read_facet_geometry(N(GetFacetedObjectData=lambda:f),'global')
    assert not f.ConvertToGlobal and f.CurrentFace==0


def test_radius_zero_native_normalization_is_explicit():
    from zemax_mcp.backend import Backend
    cell=N(DataType='Double',IsReadOnly=False,IsActive=True,Header='Radius')
    class Radius:
        DataType='Double';IsReadOnly=False;IsActive=True;Header='Radius'
        @property
        def DoubleValue(self):return math.inf
        @DoubleValue.setter
        def DoubleValue(self,value):pass
    Backend._write_cell(Radius(),0,zero_radius=True)
    with pytest.raises(ZemaxError):Backend._write_cell(Radius(),0)


def test_geometry_option_is_not_silently_ignored(tmp_path):
    from tests.support.detectors import backend,Matrix
    b=backend(tmp_path,array=Matrix([[1,0],[0,0]]))
    response=b.dispatch('get_detector_data',dict(detector=1,include_geometry=True))
    assert response['error']['code']=='UNSUPPORTED_DETECTOR_GEOMETRY'


def test_model_capabilities_without_native_application(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    b=Backend(Config(tmp_path,tmp_path));caps=b.get_capabilities(None)
    assert not caps['connected'] and len(caps['implemented_tools'])==102
    assert {'get_star_data','run_star_operation','get_hpc_settings','run_speos_export'} <= set(caps['implemented_tools'])
    assert caps['parameter_ranges']['LDE']['last']==254 and caps['parameter_ranges']['NCE']['last']==250
    assert 'selected primary wavelength'in caps['wavefront_pupil_mapping']['scope']
    assert 'ExtendedPolynomial'in caps['validated_surface_model_scope']
    assert {'Conjugate','ABCD','RetroReflect','JonesMatrix'}<=set(caps['validated_surface_model_scope'])
    assert 'l/n' in caps['surface_numeric_reference_scopes']['ABCD']
    assert 'axial' in caps['surface_numeric_reference_scopes']['JonesMatrix']
    assert caps['detector_adapters']['ReverseRadianceDetector']['validation_status']=='removed_since_23_2'
