import math
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.models import COMMAND_MODELS, SystemPatch, SurfacePatch, CopySurfaces, SurfaceGeometry, SystemResources
from zemax_mcp.modeling import ModelingMixin
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize("command,args",[
    ("get_system_resources", {"kind":"materials"}),
    ("get_system_resources", {"kind":"catalogs","count":1001}),
    ("get_system_resources", {"kind":"catalogs","start":-1}),
    ("copy_surfaces", {"start":0,"at":1}),
    ("copy_surfaces", {"start":1,"at":1,"count":101}),
    ("get_surface_geometry", {"surface":1,"points":[{"x":float("nan"),"y":0}]}),
    ("update_system_settings", {"fields":[{"x":0,"y":0}],"field_updates":[{"number":1,"vdx":0}]}),
    ("update_system_settings", {"field_updates":[{"number":1},{"number":1}]}),
    ("update_surfaces", {"changes":[{"surface":1,"aperture":{"type":"CircularAperture"}}]}),
    ("update_surfaces", {"changes":[{"surface":1,"aperture":{"pickup_from":1,"type":"None"}}]}),
    ("update_surfaces", {"changes":[{"surface":1,"solves":{"thickness":{"mode":"position"}}}]}),
])
def test_invalid_modeling_requests(command,args):
    with pytest.raises(ValidationError): COMMAND_MODELS[command].model_validate(args)

class Adapter(ModelingMixin):
    def _require_sequential(self): pass
    def _row(self,i): return self.rows[i]
    def _mutate(self,label): self.mutations+=1


@pytest.mark.parametrize('name,attribute',[('chip_zone','ChipZone'),('mechanical_semi_diameter','MechanicalSemiDiameter')])
def test_mechanical_property_write_must_be_adopted(name,attribute):
    from zemax_mcp.backend import Backend
    class Ignored:
        IsReadOnly=False
        IsActive=True
        DataType='Double'
        Header=attribute
        DoubleValue=0
        def __setattr__(self,key,value):pass
    with pytest.raises(ZemaxError)as err:Backend._write_cell(Ignored(),2)
    assert err.value.code=='SETTING_REJECTED'



@pytest.mark.parametrize('replace',[False,True])
def test_automatic_mechanical_dimension_requires_explicit_fixed_transition(replace):
    from zemax_mcp.backend import Backend
    b=Adapter();b._guard_cell=Backend._guard_cell.__get__(b)
    cell=N(IsActive=True,IsReadOnly=True,Solve='Automatic',Header='Mechanical',GetAvailableSolveTypes=lambda:['Fixed','Automatic'])
    row=N(MechanicalSemiDiameterCell=cell)
    change=SurfacePatch(surface=1,mechanical_semi_diameter=3,replace_solves=replace)
    if replace:b._validate_surface_extension(row,change)
    else:
        with pytest.raises(ZemaxError):b._validate_surface_extension(row,change)
    assert cell.Solve=='Automatic'


@pytest.mark.parametrize("accepted,actual",[(False,1),(True,2)])
def test_global_reference_selection_checks_return_and_readback(accepted,actual):
    b=Adapter()
    b.system=N(SystemData=N(Aperture=N(GCRS=N(SetSelectedSurface=lambda _:accepted,GetSelectedSurface=lambda:actual))))
    with pytest.raises(ZemaxError)as error:b._apply_settings_extension(SystemPatch(global_reference_surface=1))
    assert error.value.code=="SETTING_REJECTED"


def test_resources_pagination_and_no_match():
    b=Adapter(); b.system=N(SystemData=N(MaterialCatalogs=N(GetAvailableCatalogs=lambda:["AAA","AAB","BBB"],GetCatalogsInUse=lambda:[])))
    page=b.get_system_resources(SystemResources(kind="catalogs",query="aa",count=1))
    assert page["items"]==["AAA"] and page["next_start"]==1 and page["total"]==2
    assert b.get_system_resources(SystemResources(kind="catalogs",query="zzz"))["items"]==[]


def test_catalog_dependency_checked_before_mutation():
    b=Adapter(); b.rows=[N(MaterialCatalog="SCHOTT",Material="N-BK7")]
    b.system=N(Mode="Sequential",SystemData=N(MaterialCatalogs=N(GetAvailableCatalogs=lambda:["SCHOTT","CORNING"],GetCatalogsInUse=lambda:["SCHOTT"])),LDE=N(NumberOfSurfaces=1))
    with pytest.raises(ZemaxError,match="曲面仍引用"):
        b._validate_settings_extension(SystemPatch(material_catalogs=["CORNING"]))


def test_copy_keeps_physical_stop_and_checks_count():
    b=Adapter(); b.rows=[N(IsStop=False) for _ in range(8)]; b.mutations=0
    b.system=N(LDE=N(NumberOfSurfaces=6,StopSurface=3,CopySurfaces=lambda *x:2))
    data=b.copy_surfaces(CopySurfaces(start=1,count=2,at=2))
    assert data["stop_surface"]==5 and b.rows[5].IsStop and b.mutations==1
    b.system.LDE.CopySurfaces=lambda *x:1
    with pytest.raises(ZemaxError,match="数量不符"): b.copy_surfaces(CopySurfaces(start=1,count=2,at=2))


def test_geometry_preserves_failed_points():
    b=Adapter(); b.rows=[N()]
    b.system=N(LDE=N(GetGlobalMatrix=lambda i:(True,1,0,0,0,1,0,0,0,1,0,0,10),GetSag=lambda i,x,y:(False,0,0)),SystemData=N(Units=N(LensUnits="Millimeters"),Aperture=N(GCRS=N(GetSelectedSurface=lambda:1))))
    data=b.get_surface_geometry(SurfaceGeometry(surface=0,points=[{"x":1,"y":0}]))
    assert data["global_transform"]["translation"]==[0,0,10]
    assert data["rows"][0]["sag"] is None and data["rows"][0]["error"]


@pytest.mark.parametrize("adding",[True,False])
def test_catalog_failure_is_explicit(adding):
    b=Adapter()
    catalog=N(GetAvailableCatalogs=lambda:["B"],GetCatalogsInUse=lambda:["A"],AddCatalog=lambda x:False,RemoveCatalog=lambda x:False)
    b.system=N(SystemData=N(MaterialCatalogs=catalog))
    with pytest.raises(ZemaxError,match="目录失败"):
        b._apply_settings_extension(SystemPatch(material_catalogs=["A","B"] if adding else []))


def test_aperture_pickup_guard_and_cycle():
    b=Adapter(); b.rows=[N(SurfaceNumber=0,ApertureData=N(IsPickedUp=True,PickupFrom=1)),N(SurfaceNumber=1,ApertureData=N(IsPickedUp=True,PickupFrom=0))]
    b.system=N(LDE=N(NumberOfSurfaces=2))
    with pytest.raises(ZemaxError,match="受保护"):
        b._validate_surface_extension(b.rows[0],SurfacePatch(surface=0,aperture={"type":"None"}))
    with pytest.raises(ZemaxError,match="循环"):
        b._validate_aperture_batch([SurfacePatch(surface=0,aperture={"pickup_from":1,"replace_pickup":True})])


def test_disabled_tilt_is_rejected():
    b=Adapter(); row=N(TiltDecenterData=N(BeforeAfterSurfaceEnabled=False))
    with pytest.raises(ZemaxError,match="不支持"):
        b._validate_surface_extension(row,SurfacePatch(surface=1,tilt_decenter={"before_tilt_x":5}))


def test_legacy_comparison_reports_missing_conditions(tmp_path):
    from tests.support.evaluation import fake_backend,start,finish
    from zemax_mcp.models import CompareResults
    b,_=fake_backend(tmp_path); task=start(b,[4]); finish(b)
    data=b._full_result(task)
    data["rows"][0]["conditions"]["system"]={"lens_units":"Millimeters"}
    b._full_result=lambda _:data
    result=b.compare_results(CompareResults(left_task_id=task,right_task_id=task))
    assert not result["compatible"] and any("polarization" in x for x in result["differences"])


class PickupAperture:
    def __init__(self, source=None):
        self.source = source
        self.writes = []
    @property
    def IsPickedUp(self): return self.source is not None
    @property
    def PickupFrom(self): return self.source
    @PickupFrom.setter
    def PickupFrom(self, source):
        self.source = source
        self.writes.append(source)
    def SetPickupNone(self):
        self.source = None
        self.writes.append(None)


def aperture_backend(tmp_path, edges):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    rows=[N(Type="Standard",SurfaceNumber=i, ApertureData=PickupAperture(edges.get(i))) for i in range(6)]
    b=Backend(Config(tmp_path,tmp_path),N(system=N(Mode="Sequential",LDE=N(NumberOfSurfaces=len(rows)))))
    b._row=lambda i: rows[i]
    b._mutate=lambda _: setattr(b,"revision",b.revision+1)
    b._surface_data=lambda i: {"surface":i}
    def apply(row,change):
        if change.aperture.pickup_from is not None:
            row.ApertureData.PickupFrom=change.aperture.pickup_from
        else: row.ApertureData.SetPickupNone()
    b._apply_surface_extension=apply
    return b,rows


@pytest.mark.parametrize("edges,updates",[
    ({},[(1,2),(2,1)]),
    ({},[(1,2),(2,3),(3,1)]),
    ({2:3},[(1,2),(3,1)]),
    ({},[(1,1)]),
])
@pytest.mark.parametrize("reverse",[False,True])
def test_batch_cycles_rejected_before_any_write(tmp_path,edges,updates,reverse):
    b,rows=aperture_backend(tmp_path,edges)
    changes=[{"surface":i,"aperture":{"pickup_from":source,"replace_pickup":True}} for i,source in updates]
    if reverse: changes.reverse()
    result=b.dispatch("update_surfaces",{"changes":changes})
    assert not result["ok"] and result["error"]["code"]=="INVALID_SOLVE"
    assert result["error"]["details"]["cycle"][0]==result["error"]["details"]["cycle"][-1]
    assert b.revision==0 and not result["error"]["details"]["partial_changes_possible"]
    assert all(not r.ApertureData.writes for r in rows)


@pytest.mark.parametrize("reverse",[False,True])
def test_valid_batch_can_reverse_old_edge_by_removing_it(tmp_path,reverse):
    b,rows=aperture_backend(tmp_path,{1:2})
    changes=[{"surface":2,"aperture":{"pickup_from":1}},{"surface":1,"aperture":{"type":"None","replace_pickup":True}}]
    if reverse: changes.reverse()
    result=b.dispatch("update_surfaces",{"changes":changes})
    assert result["ok"] and b.revision==1
    assert rows[1].ApertureData.source is None and rows[2].ApertureData.source==1


def test_batch_acyclic_chain_and_shared_source(tmp_path):
    b,rows=aperture_backend(tmp_path,{4:5})
    result=b.dispatch("update_surfaces",{"changes":[{"surface":i,"aperture":{"pickup_from":source}} for i,source in [(1,2),(2,4),(3,4)]]})
    assert result["ok"] and [rows[i].ApertureData.source for i in (1,2,3,4)]==[2,4,4,5]


@pytest.mark.parametrize("scale_supported,offset_supported,scale,offset", [
    (False, True, 2, 0), (True, False, 1, 1),
])
def test_unsupported_pickup_parameters_rejected(tmp_path, scale_supported, offset_supported, scale, offset):
    from zemax_mcp.models import SolveSpec
    b, rows = aperture_backend(tmp_path, {})
    pickup = N(SupportsScale=scale_supported, SupportsOffset=offset_supported)
    cell = N(IsSolveTypeSupported=lambda _: True,
             CreateSolveType=lambda _: N(_S_SurfacePickup=pickup))
    b._cell = lambda *_: cell
    b.native.api = N(Editors=N(SolveType=N(SurfacePickup="SurfacePickup"), LDE=N(SurfaceColumn=N())))
    b.native.enum = lambda _, name: name
    with pytest.raises(ZemaxError, match="不支持"):
        b._validate_solve(rows[3], "radius", SolveSpec(mode="surface_pickup", source_surface=1,
                                                     scale=scale, offset=offset))

@pytest.mark.parametrize("mode,native,adopted", [("fixed","Fixed",True),("variable","Variable",True),("variable","Fixed",False)])
def test_native_solve_must_be_adopted(mode,native,adopted):
    from zemax_mcp.backend import Backend
    from zemax_mcp.models import SolveSpec
    cell=N(Solve=native,MakeSolveFixed=lambda:True,MakeSolveVariable=lambda:True)
    backend=N(_cell=lambda row,name:cell,_set_variable_mode=Backend._set_variable_mode,
              _validate_hologram2_mode=lambda *args:None)
    if adopted:
        Backend._set_solve(backend,None,"radius",SolveSpec(mode=mode))
    else:
        with pytest.raises(ZemaxError)as exc:
            Backend._set_solve(backend,None,"radius",SolveSpec(mode=mode))
        assert exc.value.code=="SOLVE_UPDATE_FAILED"

