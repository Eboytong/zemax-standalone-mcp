"""Typed solve boundaries, native adoption and post-application parameter checks."""
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.models import SurfacePatch,SystemResources
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.modeling import SOLVES,SOLVE_FIELDS,ModelingMixin

VALID=[dict(mode="marginal_ray_angle",angle=-.1),dict(mode="chief_ray_angle",angle=.2),
 dict(mode="marginal_ray_normal"),dict(mode="chief_ray_normal"),dict(mode="aplanatic"),
 dict(mode="element_power",power=.02),dict(mode="concentric_surface",source_surface=0),
 dict(mode="concentric_radius",source_surface=1),dict(mode="center_of_curvature",source_surface=1),
 dict(mode="compensator",source_surface=1,sum=-10),dict(mode="optical_path_difference",opd=0,pupil_zone=-.7),
 dict(mode="pupil_position"),dict(mode="material_model",index_nd=1.5,abbe_vd=60),
 dict(mode="material_offset"),dict(mode="material_substitute"),dict(mode="automatic"),dict(mode="maximum"),
 dict(mode="zpl_macro",macro="test")]

def spec(data):return SurfacePatch(surface=3,solves={"radius":data}).solves["radius"]

@pytest.mark.parametrize("data",VALID)
def test_new_solve_typed_requests(data):
 assert spec(data).model_dump(exclude_unset=True)==data

@pytest.mark.parametrize("data",VALID)
def test_new_solves_reject_cross_type_parameters(data):
 with pytest.raises(ValidationError):spec(dict(data,**({"power":.1} if "power"not in data else {"angle":.1})))

@pytest.mark.parametrize("data",[
 dict(mode="marginal_ray_angle"),dict(mode="chief_ray_angle",angle=float("nan")),
 dict(mode="compensator",source_surface=-1,sum=2),dict(mode="concentric_surface",source_surface=True),
 dict(mode="element_power",power=float("inf")),dict(mode="optical_path_difference",opd=0,pupil_zone=1.1),
 dict(mode="material_model",index_nd=0,abbe_vd=60),dict(mode="material_model",index_nd=1.5,abbe_vd=0),
 dict(mode="material_offset",nd_offset=None),dict(mode="zpl_macro",macro=""),dict(mode="automatic",source_surface=1)])
def test_new_solve_invalid_bounds(data):
 with pytest.raises(ValidationError):spec(data)


@pytest.mark.parametrize('name',['A'*31,'宏'*31,'M'+'😀'*15])
def test_zpl_macro_native_name_boundary_accepts_31_utf16_units(name):
 assert spec(dict(mode='zpl_macro',macro=name)).macro==name


@pytest.mark.parametrize('name',['A'*32,'宏'*32,'😀'*16])
def test_zpl_macro_native_name_boundary_rejects_32_utf16_units(name):
 with pytest.raises(ValidationError):spec(dict(mode='zpl_macro',macro=name))

@pytest.mark.parametrize("data",VALID)
def test_post_apply_readback_must_match(data):
 s=spec(data);native=SOLVES[s.mode];fields=SOLVE_FIELDS[native]
 values={attr:getattr(s,key) for key,attr in fields.items()}
 obj=N(**values);holder=N(IsValid=True,**{"_S_"+native:obj})
 c=N(Solve=native,CreateSolveType=lambda _:holder,GetSolveData=lambda:holder,SetSolveData=lambda _:"Success")
 b=N(_cell=lambda *_:c,_validate_hologram2_mode=lambda *_:None,
  native=N(enum=lambda _,x:x,api=N(Editors=N(SolveType=N()))),_checked_set_solve=Backend._checked_set_solve)
 Backend._set_solve(b,None,"radius",s)
 if fields:
  field=next(iter(fields.values()));value=getattr(obj,field)
  def ignored(_):
   setattr(obj,field,not value if isinstance(value,bool) else value+1 if isinstance(value,(float,int)) else value+"bad")
   return "Success"
  c.SetSolveData=ignored
  with pytest.raises(ZemaxError)as err:Backend._set_solve(b,None,"radius",s)
  assert err.value.code=="SETTING_REJECTED"


def test_solve_alias_uses_canonical_parameter_interface():
 s=spec(dict(mode="concentric_surface",source_surface=1));obj=N(AboutSurface=1)
 holder=N(IsValid=True,_S_CocentricSurface=obj)
 c=N(Solve="ConcentricSurface",CreateSolveType=lambda _:holder,GetSolveData=lambda:holder,SetSolveData=lambda _:"Success")
 b=N(_cell=lambda *_:c,_validate_hologram2_mode=lambda *_:None,native=N(enum=lambda _,x:x,api=N(Editors=N(SolveType=N()))),_checked_set_solve=Backend._checked_set_solve)
 Backend._set_solve(b,None,"radius",s)

@pytest.mark.parametrize("mode",["concentric_surface","concentric_radius","center_of_curvature","compensator"])
def test_reference_must_precede_target(mode):
 s=spec(dict(mode=mode,source_surface=3,**({"sum":1}if mode=="compensator"else{})))
 c=N(IsSolveTypeSupported=lambda _:True)
 b=N(_cell=lambda *_:c,_row=lambda _:None,native=N(enum=lambda _,x:x,api=N(Editors=N(SolveType=N()))))
 with pytest.raises(ZemaxError)as err:Backend._validate_solve(b,N(SurfaceNumber=3),"radius",s)
 assert err.value.code=="INVALID_SOLVE"

@pytest.mark.parametrize("cell",["mechanical_semi_diameter","chip_zone"])
def test_mechanical_cells_in_public_request(cell):
 assert cell in SurfacePatch(surface=1,solves={cell:dict(mode="automatic")}).solves


def test_macro_resources_paginate_and_filter():
 holder=N(_S_ZPLMacro=N(GetAvailableMacros=lambda:["A1","A2","B"]))
 cell=N(IsSolveTypeSupported=lambda _:True,CreateSolveType=lambda _:holder)
 b=N(system=N(SystemData=N()),_cell=lambda *_:cell,_row=lambda _:None,native=N(api=N(Editors=N(SolveType=N(ZPLMacro="ZPLMacro")))))
 r=ModelingMixin.get_system_resources(b,SystemResources(kind="solve_macros",query="a",count=1))
 assert r["items"]==["A1"] and r["next_start"]==1 and r["total"]==2


def test_maximum_rejects_single_configuration():
    b=N(_cell=lambda *_:N(IsSolveTypeSupported=lambda _:True),system=N(MCE=N(NumberOfConfigurations=1)),
        native=N(enum=lambda _,x:x,api=N(Editors=N(SolveType=N()))))
    with pytest.raises(ZemaxError)as err:Backend._validate_solve(b,N(SurfaceNumber=3),"semi_diameter",spec(dict(mode="maximum")))
    assert err.value.code=="INVALID_SOLVE"

@pytest.mark.parametrize("mode",["zpl_macro","material_substitute"])
def test_missing_solve_resource_is_explicit(mode):
    holder=N(_S_ZPLMacro=N(GetAvailableMacros=lambda:["known"]))
    c=N(IsSolveTypeSupported=lambda _:True,CreateSolveType=lambda _:holder)
    b=N(_cell=lambda *_:c,system=N(SystemData=N(MaterialCatalogs=N(GetCatalogsInUse=lambda:["SCHOTT"]))),
        native=N(enum=lambda _,x:x,api=N(Editors=N(SolveType=N(ZPLMacro="ZPLMacro")))))
    s=spec(dict(mode=mode,**({"macro":"missing"}if mode=="zpl_macro"else{"catalog":"missing"})))
    with pytest.raises(ZemaxError)as err:Backend._validate_solve(b,N(SurfaceNumber=3),"material",s)
    assert err.value.code=="INVALID_RESOURCE"
