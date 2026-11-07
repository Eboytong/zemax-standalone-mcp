import json,struct,csv
from types import SimpleNamespace as N
import pytest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.saved_detector import saved_detector_result
from zemax_mcp.beam_files import iter_beam_samples
from zemax_mcp.models import COMMAND_MODELS
from support.detectors import backend,Matrix


def snapshot():
    return dict(detector=1,detector_type="DetectorVolume",kind="absorbed_flux",context={},
        nx=2,ny=1,nz=3,values=[[[1,2]],[[3,None]],[[5,6]]],
        x_axis=dict(name="X",unit="mm",centers=[-.5,.5],bounds=[[-1,0],[0,1]]),
        y_axis=dict(name="Y",unit="mm",centers=[0],bounds=[[-1,1]]),
        z_axis=dict(name="Z",unit="mm",centers=[-1,0,1],bounds=[[-1.5,-.5],[-.5,.5],[.5,1.5]]),
        value_unit="Watts",value_unit_prefix="None",trace_history=[dict(task_id="old",state="failed",error=dict(code="TRACE_FAILED"))])


def test_volume_snapshot_report_retains_all_voxels(tmp_path):
    p=tmp_path/"volume.json";p.write_text(json.dumps(snapshot()),encoding="utf-8")
    r=saved_detector_result(str(p))
    assert len(r["rows"])==6 and len(r["grids"])==3
    assert r["rows"][3]["state"]=="invalid" and r["rows"][4]["local_z"]==1
    assert r["trace_conditions"][0]["state"]=="failed"
    b=backend(tmp_path)
    out=b.export_evaluation_report(COMMAND_MODELS["export_evaluation_report"](detector_files=[str(p)]))
    rows=list(csv.DictReader(next(tmp_path.glob("report_*/*_rows.csv")).open(encoding="utf-8-sig")))
    assert len(rows)==6 and rows[-1]["z"]=="2"
    assert out["artifacts"]


@pytest.mark.parametrize("fault",["shape","dimension","axis","nonfinite","context","rows"])
def test_malformed_detector_snapshot_is_rejected(tmp_path,fault):
    raw=snapshot()
    if fault=="shape":raw["values"].pop()
    elif fault=="dimension":raw["nx"]=True
    elif fault=="axis":raw["z_axis"]["centers"]=[0]
    elif fault=="nonfinite":raw["values"][0][0][0]=float("inf")
    elif fault=="context":raw["context"]=[]
    else:raw={k:v for k,v in raw.items()if k not in {"values","nz"}};raw["rows"]=[7]
    p=tmp_path/"bad.json";p.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ZemaxError)as e:saved_detector_result(str(p))
    assert e.value.code=="INVALID_RESULT_DATA"


@pytest.mark.parametrize("text",[False,True])
@pytest.mark.parametrize("polarized",[False,True])
def test_complete_beam_fields_export(text,polarized,tmp_path):
    integers=[1,3,2,int(polarized),0,0,0,0,0];header=[.1,.2,0,1,.1,0,1,.2,.00055,1,0,0]+[0.]*8
    fields=list(map(float,range(12*(1+polarized))))
    path=tmp_path/"beam.zbf"
    if text:path.write_text("A\n"+"\n".join(map(str,integers+header+fields)),encoding="ascii")
    else:path.write_bytes(struct.pack("<9i20d",*integers,*header)+struct.pack("<"+str(len(fields))+"d",*fields))
    rows=list(iter_beam_samples(path))
    assert len(rows)==6 and rows[-1]["ex_imag"]==11
    if polarized:assert rows[-1]["ey_imag"]==23


@pytest.mark.parametrize("bad",[False,True])
def test_color_flat_pixel_shape_and_region(tmp_path,bad):
    b=backend(tmp_path,"DetectorColor");row=b.system.NCE.GetObjectAt(1)
    row.ObjectData=N(NumberXPixels=3,NumberYPixels=5,XHalfWidth=2,YHalfWidth=3)
    b.system.NCE.GetAllColorDetectorDataSafe=lambda *_:Matrix([[v]for v in range(14 if bad else 15)])
    out=b.dispatch("get_detector_data",dict(detector=1,x_start=1,y_start=3,width=1,height=1))
    if bad:assert out["error"]["code"]=="INVALID_DETECTOR_DATA"
    else:assert out["data"]["values"]==[[10]]and out["data"]["total_flux"]==105


@pytest.mark.parametrize("outcome",["success","false","nonfinite"])
def test_volume_scalar_index_and_3d_page(tmp_path,outcome):
    b=backend(tmp_path,"DetectorVolume");row=b.system.NCE.GetObjectAt(1)
    row.ObjectData=N(NumberXPixels=2,NumberYPixels=3,NumberZPixels=4,XHalfWidth=1,YHalfWidth=2,ZHalfWidth=3)
    b.system.NCE.GetDetectorData=lambda obj,pixel,code,_:(outcome!="false",float("nan")if outcome=="nonfinite"else pixel)
    out=b.dispatch("get_detector_data",dict(detector=1,x_start=1,y_start=1,z_start=2,width=1,height=1,depth=1,kind="absorbed_density"))
    if outcome=="false":assert out["error"]["code"]=="DETECTOR_READ_FAILED"
    else:
        r=out["data"];assert r["values"]==[[[None if outcome=="nonfinite"else 16.]]]
        assert r["nz"]==4 and r["next_z"]==3 and r["total_flux"]is None
        assert r["value_unit"]=="Watts/Millimeters^3"and r["value_unit_prefix"]=="Milli"


def test_mapping_points_follow_grid_region_pagination(tmp_path):
    b=backend(tmp_path)
    points=[[dict(px=x,py=y,valid=True,reason=None)for x in range(3)]for y in range(2)]
    b.tasks["mapped"]=dict(task_id="mapped",kind="analysis",state="succeeded",result=dict(task={},context={},artifacts=[],
        grids=[dict(nx=3,ny=2,values=[[1,2,3],[4,5,6]],pupil_mapping=dict(status="test",points=points))]))
    summary=b.get_task_result(COMMAND_MODELS["get_task_result"](task_id="mapped"))
    assert "points"not in summary["grids"][0]["pupil_mapping"]
    region=b.get_task_result(COMMAND_MODELS["get_task_result"](task_id="mapped",grid=0,x_start=1,y_start=1,width=1,height=1))
    assert region["grid"]["pupil_mapping"]["points"]==[[dict(px=1,py=1,valid=True,reason=None)]]


def test_color_report_names_actual_quantity(tmp_path):
    raw=snapshot();raw.pop("nz");raw.pop("z_axis")
    raw.update(detector_type="DetectorColor",color_channel="tristimulus_y",values=[[1,2]])
    p=tmp_path/"color.json";p.write_text(json.dumps(raw),encoding="utf-8")
    result=saved_detector_result(str(p))
    assert result["rows"][0]["metrics"][0]["key"]=="tristimulus_y"
    assert result["grids"][0]["description"]=="DetectorColor tristimulus_y"


@pytest.mark.parametrize("detector",[0,1])
@pytest.mark.parametrize("raises",[False,True])
def test_failed_clear_retains_history_but_marks_unknown(tmp_path,detector,raises):
    b=backend(tmp_path);b._clear_detector_records()
    b._detector_record(1);b._detector_record(2)
    def clear(_):
        if raises:raise RuntimeError("native clear interrupted")
        return "Failed"
    b.system.Tools=N(OpenNSCRayTrace=lambda:N(ClearDetectors=clear,ClearDetectorObject=clear,Close=lambda:None))
    result=b.dispatch("clear_detectors",dict(detector=detector))
    assert result["error"]["code"]=="DETECTOR_CLEAR_FAILED"
    assert not b._detector_provenance(1)["complete"]
    assert b._detector_provenance(2)["complete"]==(detector==1)


def test_nsc_fixed_solve_must_be_adopted(tmp_path):
    b=backend(tmp_path)
    with pytest.raises(ZemaxError)as e:b._fix_nsc_cell(N(Solve="Pickup",MakeSolveFixed=lambda:True))
    assert e.value.code=="SOLVE_UPDATE_FAILED"and e.value.details["actual"]=="Pickup"


@pytest.mark.parametrize("history",[None,{},[{}],[dict(task_id="")],[dict(task_id="t",state=1)],[dict(task_id="t",configuration=True)]])
def test_malformed_detector_history_is_rejected(tmp_path,history):
    raw=snapshot();raw["trace_history"]=history
    p=tmp_path/"bad_history.json";p.write_text(json.dumps(raw),encoding="utf-8")
    with pytest.raises(ZemaxError)as error:saved_detector_result(str(p))
    assert error.value.code=="INVALID_RESULT_DATA"


@pytest.mark.parametrize("text",[False,True])
def test_beam_coordinates_and_field_csv(text,tmp_path):
    from zemax_mcp.beam_files import read_beam
    ints=[1,4,2,0,0,0,0,0,0];header=[.1,.2]+[1.]*18;values=[1.,0.]*8
    p=tmp_path/"coordinate.zbf"
    if text:p.write_text("A\n"+"\n".join(map(str,ints+header+values)),encoding="ascii")
    else:p.write_bytes(struct.pack("<9i20d",*ints,*header)+struct.pack("<16d",*values))
    page=read_beam(p,5,1,include_coordinates=True)
    assert page["rows"][0]["ix"]==1 and page["rows"][0]["iy"]==1
    assert page["rows"][0]["x"]==-.1 and page["rows"][0]["y"]==0
    row=list(iter_beam_samples(p,include_coordinates=True))[5]
    assert row["x"]==-.1 and row["length_unit"]=="Millimeters"


@pytest.mark.parametrize("extra",[dict(color_channel="chromaticity_x"),dict(angle_space=True),dict(x_start=1),dict(width=1),dict(start=1)])
def test_spectral_statistics_reject_ignored_region_options(extra):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):COMMAND_MODELS["get_detector_data"](detector=1,kind="spectral",spectral_wavelengths_um=[.55],**extra)
