"""Detector shape, origin and settings failure contracts without OpticStudio."""
from support.detectors import Matrix, backend, TRACE_OPTIONS
import math
from pathlib import Path
from types import SimpleNamespace as N
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.detectors import checked_setting, polar_coordinates
from zemax_mcp.errors import ZemaxError







@pytest.mark.parametrize("array", [None,N(Rank=1),Matrix([]),Matrix([[1]]),Matrix([[1,2,3],[4,5,6]])])
def test_invalid_native_detector_shape(tmp_path,array):
    b=backend(tmp_path,array=array)
    r=b.dispatch("get_detector_data",dict(detector=1))
    assert not r["ok"] and r["error"]["code"]=="INVALID_DETECTOR_DATA"


@pytest.mark.parametrize("x,y",[(2,0),(0,2),(3,0)])
def test_detector_region_start_must_be_inside(tmp_path,x,y):
    b=backend(tmp_path,array=Matrix([[1,0],[0,0]]))
    r=b.dispatch("get_detector_data",dict(detector=1,x_start=x,y_start=y))
    assert r["error"]["code"]=="INDEX_OUT_OF_RANGE"


def test_nonfinite_detector_data_and_power_units(tmp_path):
    b=backend(tmp_path,array=Matrix([[1,float("nan")],[float("inf"),0]]))
    data=b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1,width=1,height=1))
    assert data["values"]==[[1]] and data["invalid_count"]==2
    assert data["total_flux"]==1 and data["value_unit"]=="Watts" and data["value_unit_prefix"]=="Milli"
    assert data["next_x"]==1 and data["next_y"]==1


@pytest.mark.parametrize("kind",["irradiance","coherent"])
def test_polar_rejects_unsupported_data(tmp_path,kind):
    b=backend(tmp_path,"DetectorPolar",Matrix([[0]*3 for _ in range(4)]))
    r=b.dispatch("get_detector_data",dict(detector=1,kind=kind))
    assert r["error"]["code"]=="UNSUPPORTED_DETECTOR_DATA"


@pytest.mark.parametrize("kind,native_type", [("flux","Power"),("intensity","PowerSolidAngle")])
def test_polar_coordinates_paging_and_units(tmp_path,kind,native_type):
    b=backend(tmp_path,"DetectorPolar",Matrix([[0,1,2],[3,4,5],[6,7,8],[9,10,11]]))
    data=b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1,kind=kind,x_start=1,y_start=2,width=2,height=1))
    assert data["values"]==[[7,8]] and data["nx"]==3 and data["ny"]==4
    assert data["native_data_type"]==native_type
    assert data["x_axis"]["centers"]==[0,90,180]
    assert data["y_axis"]["bounds"][0]==[-45,45]
    assert data["total_flux"]==(66 if kind=="flux"else None)
    assert data["value_unit"]==("Watts"if kind=="flux"else"Watts/sr")
    assert sum(data["pixel_solid_angle_sr"])*4==pytest.approx(4*math.pi)


@pytest.mark.parametrize("np,na,angle",[(1,4,90),(3,0,90),(3,4,181),(3,4,float("nan"))])
def test_invalid_polar_geometry(np,na,angle):
    with pytest.raises(ZemaxError):polar_coordinates(np,na,angle)


@pytest.mark.parametrize("outcome",["success","false","nonfinite","short"])
def test_native_global_transform_is_checked(tmp_path,outcome):
    b=backend(tmp_path)
    data=(True,1,0,0,0,1,0,0,0,1,10,20,30)
    if outcome=="false":data=(False,*data[1:])
    elif outcome=="nonfinite":data=(*data[:-1],float("nan"))
    elif outcome=="short":data=(True,1)
    b.system.NCE.GetMatrix=lambda *_:data
    if outcome=="success":
        r=b._nsc_transform(1);assert r["translation"]==[10,20,30]and r["rotation"]==[[1,0,0],[0,1,0],[0,0,1]]
    else:
        with pytest.raises(ZemaxError):b._nsc_transform(1)


@pytest.mark.parametrize("state",["succeeded","failed","cancelled","running"])
def test_history_completion_depends_on_task_state(tmp_path,state):
    b=backend(tmp_path);b._clear_detector_records()
    b.tasks["trace"]=dict(state=state)
    b._detector_record(1)["traces"].append(dict(task_id="trace",model_revision=0,configuration=1,trace_options=TRACE_OPTIONS))
    assert b._detector_provenance(1)["complete"]==(state=="succeeded")


def test_selective_clear_and_mixed_revision(tmp_path):
    b=backend(tmp_path);b._clear_detector_records()
    for index in (1,2):
        b._detector_record(index)["traces"].append(dict(task_id="a",model_revision=0,configuration=1))
    b.tasks["a"]=dict(state="succeeded")
    b._clear_detector_records(1)
    assert b._detector_provenance(1)["trace_history"]==[]
    assert len(b._detector_provenance(2)["trace_history"])==1
    b.revision=1
    assert not b._detector_provenance(1)["complete"]
    assert not b._detector_provenance(2)["model_matches_history"]
    b.tasks["b"]=dict(state="succeeded")
    b._detector_record(2)["traces"].append(dict(task_id="b",model_revision=1,configuration=1))
    r=b._detector_provenance(2)
    assert r["mixed_conditions"]and not r["complete"]
    b._reset_detector_history()
    assert not b._detector_provenance(2)["history_known"]


def test_lazy_record_keeps_clear_revision(tmp_path):
    b=backend(tmp_path);b._clear_detector_records();b.revision+=1
    assert not b._detector_provenance(1)["model_matches_history"]


class Scalar:
    def __init__(self,ignored=False):self.ignored=ignored;self.value=0.
    def GetType(self):
        return N(GetProperty=lambda _:N(CanWrite=True,PropertyType=N(IsEnum=False,FullName="System.Double")))
    @property
    def InitialPhaseDeg(self):return self.value
    @InitialPhaseDeg.setter
    def InitialPhaseDeg(self,v):
        if not self.ignored:self.value=v


@pytest.mark.parametrize("ignored",[False,True])
def test_checked_native_setting_readback(ignored):
    s=Scalar(ignored)
    if ignored:
        with pytest.raises(ZemaxError)as failure:checked_setting(None,s,"InitialPhaseDeg",90)
        assert failure.value.code=="SETTING_REJECTED"
    else:
        checked_setting(None,s,"InitialPhaseDeg",90);assert s.value==90


def test_object_batch_stops_after_setting_rejected(tmp_path):
    b=backend(tmp_path);rows={i:N(RefObject=0,InsideOf=0,SourcesData=Scalar(i==1),ObjectData=N(),TypeData=N())for i in (1,2)}
    b._object=lambda i:rows[i];b.get_nsc_objects=lambda _:dict(rows=[])
    r=b.dispatch("update_nsc_objects",dict(changes=[dict(object=i,sources=dict(InitialPhaseDeg=90))for i in (1,2)]))
    assert not r["ok"]and r["error"]["code"]=="SETTING_REJECTED"
    assert r["error"]["details"]["object"]==1 and r["error"]["details"]["partial_changes_possible"]
    assert rows[2].SourcesData.value==0 and b.revision==1


@pytest.mark.parametrize("outcome",["succeeded","failed","cancelled","start_failure"])
def test_trace_attempt_remains_in_detector_history(tmp_path,monkeypatch,outcome):
    import zemax_mcp.nonsequential as module
    b=backend(tmp_path)
    tool=N(ClearDetectors=lambda _:"Success",SetRandomSeed=lambda _:None,ResetRandomSeed=lambda:None)
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool)
    monkeypatch.setattr(module,"scalar_settings",lambda _:dict())
    def start(*args,**kwargs):
        b.tasks["t"]=dict(state="failed"if outcome=="start_failure"else outcome)
        if outcome=="start_failure":raise ZemaxError("TASK_START_FAILED","failed",task_id="t")
        return dict(task_id="t",state=outcome)
    b._start_task=start
    if outcome=="start_failure":
        with pytest.raises(ZemaxError):b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"]())
    else:b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"]())
    r=b._detector_provenance(1)
    assert r["trace_history"][0]["task_id"]=="t"
    assert r["complete"]==(outcome=="succeeded")



@pytest.mark.parametrize("material",["-","MIRROR","ABSORB",""])
def test_catalog_dependency_skips_native_non_glass_materials(tmp_path,material):
    from zemax_mcp.models import SystemPatch
    b=backend(tmp_path)
    b.system.SystemData.MaterialCatalogs=N(
        GetAvailableCatalogs=lambda:["SCHOTT"],GetCatalogsInUse=lambda:["SCHOTT"])
    b.system.NCE.GetObjectAt=lambda _:N(Material=material,FindMaterialCatalog=lambda:"AMTIR.AGF")
    b.system.SystemData.Polarization=N();b.system.SystemData.RayAiming=N()
    b._validate_settings_extension(SystemPatch(material_catalogs=["SCHOTT"]))


def test_nsc_reference_cell_without_solve_is_writable(tmp_path):
    b=backend(tmp_path)
    b._guard_nsc_cell(N(Solve="None",IsReadOnly=False,IsActive=True))
    with pytest.raises(ZemaxError):
        b._guard_nsc_cell(N(Solve="None",IsReadOnly=True,IsActive=True))


@pytest.mark.parametrize("coherent_type",["Real","Imaginary","Amplitude","Power"])
def test_coherent_units_are_not_irradiance_units(tmp_path,coherent_type):
    b=backend(tmp_path,array=Matrix([[1,0],[0,0]]))
    r=b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1,kind="coherent",coherent_type=coherent_type))
    assert r["value_unit"]==("Watts"if coherent_type=="Power"else"sqrt(Watts)")
    assert r["value_unit_prefix"]=="Milli"
    assert r["coherence"]["normalize_coherent_power"]is False



@pytest.mark.parametrize("detector",[0,2])
def test_clear_uses_object_number_not_detector_ordinal(tmp_path,detector):
    from zemax_mcp.nsc_models import DetectorClear
    b=backend(tmp_path);calls=[]
    tool=N(ClearDetectors=lambda n:calls.append(("ordinal",n))or"Success",
           ClearDetectorObject=lambda n:calls.append(("object",n))or"Success")
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool);b._release_owned=lambda _:None
    b.clear_detectors(DetectorClear(detector=detector))
    assert calls==[("ordinal",0)if detector==0 else("object",2)]



@pytest.mark.parametrize("scalar_result",[(True,.5),(False,0),(True,float("nan"))])
def test_saved_detector_report_rows_and_async_history(tmp_path,monkeypatch,scalar_result):
    import zemax_mcp.nonsequential as module
    b=backend(tmp_path)
    tool=N(Succeeded=True,ClearDetectors=lambda _:"Success",SetRandomSeed=lambda _:None,
           ResetRandomSeed=lambda:None,GetTotalRayEnergy=lambda:1.,DeadRayErrors=0.,DeadRayThreshold=0.)
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool)
    b.system.NCE.GetDetectorData=lambda *_:scalar_result
    b._close_task_native=lambda _:True
    monkeypatch.setattr(module,"scalar_settings",lambda _:dict())
    holder={}
    def start(*args,**kwargs):
        holder["collector"]=kwargs["collector"]
        holder["settings"]=args[2]
        return dict(task_id="t",state="running")
    b._start_task=start
    b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"]())
    task=dict(task_id="t",context=b.context(),settings=holder["settings"])
    if scalar_result[0] and math.isfinite(scalar_result[1]):
        result=holder["collector"](task)
        assert result["rows"][0]["accumulated_total_flux"]==.5
        assert result["rows"][0]["metrics"][0]["key"]=="accumulated_detector_flux"
        assert len(result["rows"][0]["trace_conditions"])==1
    else:
        with pytest.raises(ZemaxError)as failure:holder["collector"](task)
        assert failure.value.code=="DETECTOR_READ_FAILED"



@pytest.mark.parametrize("units,polar_base",[("Watts","Watts"),("Lumens","Watts"),("Joules","Joules")])
@pytest.mark.parametrize("kind",["flux","intensity"])
def test_polar_unit_is_radiometric_even_for_lumen_sources(tmp_path,units,polar_base,kind):
    b=backend(tmp_path,"DetectorPolar",Matrix([[1]*3 for _ in range(4)]))
    b.system.SystemData.Units.SourceUnits=units
    r=b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1,kind=kind))
    assert r["source_units"]==units
    assert r["value_unit"]==polar_base+("/sr"if kind=="intensity"else"")
    assert r["value_unit_prefix"]=="Milli"
    if units=="Joules":assert "energy"in r["quantity"]


def test_energy_density_unit_uses_source_energy_mode(tmp_path):
    b=backend(tmp_path,array=Matrix([[1,0],[0,0]]));b.system.SystemData.Units.SourceUnits="Joules"
    r=b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1,kind="irradiance"))
    assert r["value_unit"]=="JoulesPerCMSq" and r["quantity"]=="energy density"
