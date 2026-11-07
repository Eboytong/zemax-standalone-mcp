import json,struct
from pathlib import Path
import pytest
from zemax_mcp.beam_files import read_beam
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import COMMAND_MODELS
from tests.support.detectors import backend
from types import SimpleNamespace as N


@pytest.mark.parametrize("polarized",[0,1])
@pytest.mark.parametrize("start,count",[(0,1),(1,3),(5,2),(6,1)])
def test_text_zbf_pages(polarized,start,count,tmp_path):
    path=tmp_path/"beam.zbf"
    integers=[1,3,2,polarized,0,0,0,0,0];header=[.1,.2,0,1,.1,0,1,.2,.00055,1,0,0]+[0.]*8
    fields=[float(i) for i in range(12*(1+polarized))]
    path.write_text("A\n"+"\n".join(map(str,integers+header+fields)),encoding="ascii")
    result=read_beam(path,start,count)
    assert result["format"]=="zbf_text"and result["nx"]==3 and result["ny"]==2
    for i,row in enumerate(result["rows"]):
        assert row["ex_real"]==2*(start+i)
        if polarized:assert row["ey_imag"]==12+2*(start+i)+1
    assert len(result["rows"])==min(count,6-start)


@pytest.mark.parametrize("text",["A\n","A\n99 2 2 0 0 0 0 0 0\n"+"0 "*20,"A\n1 2 2 0 0 0 0 0 0\n"+"0 "*20+"1 2"])
def test_invalid_text_zbf_is_structured(text,tmp_path):
    path=tmp_path/"bad.zbf";path.write_text(text,encoding="ascii")
    with pytest.raises(ZemaxError):read_beam(path,0,4)


@pytest.mark.parametrize("start,count",[(-1,1),(0,0),(0,True),(0,1001)])
def test_beam_reader_argument_contract(start,count,tmp_path):
    with pytest.raises(ZemaxError)as e:read_beam(tmp_path/"unused.zbf",start,count)
    assert e.value.code=="INVALID_ARGUMENT"


@pytest.mark.parametrize("failed,restore",[(False,True),(True,True),(True,False)])
def test_detector_import_state_and_restore(failed,restore,tmp_path):
    b=backend(tmp_path);b._clear_detector_records()
    path=tmp_path/"input.ddr";path.write_bytes(b"input")
    def save(index,file):Path(file).write_bytes(b"backup");return True
    b.system.NCE.SaveDetector=save
    b.system.NCE.LoadDetector=lambda index,file,append:restore if "detector_before_load_"in file else not failed
    r=b.dispatch("load_detector_data",dict(detector=1,path=str(path)))
    if not failed:
        assert r["ok"]and not r["data"]["history_known"]and not r["data"]["complete"]
    elif restore:
        assert r["error"]["code"]=="DETECTOR_LOAD_FAILED"and r["error"]["details"]["restored"]
        assert b._detector_provenance(1)["complete"]
    else:assert r["error"]["code"]=="RESTORE_FAILED"and b.requires_reconnect


def test_single_result_plot_is_offline_and_native_request_is_explicit(tmp_path):
    b=backend(tmp_path);b.tasks["t"]=dict(state="succeeded",result=dict(series=[dict(
        x=[0,1],y=[[0],[1]],labels=["power"],x_label="X",x_unit="mm",description="reference")]))
    q=COMMAND_MODELS["export_analysis_image"](task_id="t",path=str(tmp_path/"plot.png"),width=640,height=480)
    result=b.export_analysis_image(q)
    assert result["image_source"]=="data_plot"and (tmp_path/"plot.png").is_file()
    width,height=struct.unpack(">II",(tmp_path/"plot.png").read_bytes()[16:24])
    assert (width,height)==(640,480)
    with pytest.raises(ZemaxError)as failure:
        b.export_analysis_image(q.model_copy(update=dict(path=str(tmp_path/"native.png"),source="native")))
    assert failure.value.code=="UNSUPPORTED_NATIVE_IMAGE"


class Settings:
    def __init__(self,ignored=None,**values):
        object.__setattr__(self,"ignored",ignored)
        for name,value in values.items():object.__setattr__(self,name,value)
    def __setattr__(self,name,value):
        if name!=self.ignored:object.__setattr__(self,name,value)
    def GetType(self):
        def prop(name):
            value=getattr(self,name,None)
            return N(CanWrite=True,PropertyType=N(IsEnum=name in {"Model","SourceColor"},
                FullName="System.Boolean"if type(value)is bool else"System.String"if isinstance(value,str)else"System.Double"))
        return N(GetProperty=prop)


@pytest.mark.parametrize("scope",["coating","rays","scatter","volume","spectrum","diffraction"])
def test_nested_native_setting_rejection_stops_batch(tmp_path,scope):
    b=backend(tmp_path);face=Settings("Coating"if scope=="coating"else"NumberOfRays"if scope=="rays"else None,
        Coating="",NumberOfRays=1,CurrentScatterModel="None")
    face.UseCustomSettings=lambda:True;face.GetAvailableCoatings=lambda:["I.50"]
    scatter=Settings(ScatterFraction=0.)
    face.CreateScatterModelSettings=lambda _:N(_S_Lambertian=scatter)
    face.ChangeScatterModelSettings=lambda _:True
    row=N(RefObject=0,InsideOf=0,ObjectData=N(),TypeData=N(),
        CoatScatterData=N(IsCoatScatterAvailable=True,NumberOfFaces=1,GetFaceData=lambda _:face),
        SourcesData=Settings("SourceColor",IsSourcesAvailable=True,SourceColor="SystemWavelengths"),
        VolumePhysicsData=Settings("Model",IsVolumePhysicsAvailable=True,Model="None"),
        DiffractionData=Settings("Value",IsDiffractionAvailable=True,Value=0.))
    b._object=lambda _:row;b.get_nsc_objects=lambda _:dict(rows=[])
    b.native.set_enum=lambda obj,name,value:setattr(obj,name,value)
    b.native.api.Editors.NCE.ObjectScatteringTypes=None
    patches={"coating":dict(faces=[dict(face=0,coating="I.50")]),
        "rays":dict(faces=[dict(face=0,number_of_rays=10)]),
        "scatter":dict(faces=[dict(face=0,scatter_model="Lambertian",settings=dict(ScatterFraction=.5))]),
        "volume":dict(volume=dict(model="AngleScattering")),
        "spectrum":dict(spectrum=dict(mode="UniformPowerSpectrum")),"diffraction":dict(diffraction=dict(Value=3.))}
    result=b.dispatch("update_nsc_objects",dict(changes=[dict(object=1,**patches[scope]),dict(object=2,sources=dict(Unused=True))]))
    assert not result["ok"]and result["error"]["code"]=="SETTING_REJECTED"
    assert result["error"]["details"]["object"]==1 and result["error"]["details"]["partial_changes_possible"]
    assert not hasattr(row.SourcesData,"Unused")


def test_generated_pop_input_is_released_only_after_native_close(tmp_path):
    from zemax_mcp.physical_optics import OwnedInputsAnalysis
    path=tmp_path/"mcp_input.zbf";path.write_bytes(b"input")
    wrapper=OwnedInputsAnalysis(N(Close=lambda:False),[path])
    assert wrapper.Close()is False and path.is_file()
    wrapper.analysis=N(Close=lambda:None)
    wrapper.Close();assert not path.exists()


@pytest.mark.parametrize("failure",["false","ignored","range"])
def test_volume_dll_parameter_failures_stop_writes(tmp_path,failure):
    b=backend(tmp_path)
    settings=N(NumberOfParameters=1,SetParameterValue=lambda i,v:failure!="false",GetParameterValue=lambda i:0.)
    row=N(RefObject=0,InsideOf=0,ObjectData=N(),SourcesData=N(),TypeData=N(),VolumePhysicsData=Settings(IsVolumePhysicsAvailable=True,Model="None",ModelSettings=N(_S_DLLDefinedScattering=settings)))
    b._object=lambda _:row;b.native.set_enum=lambda obj,name,value:setattr(obj,name,value)
    b.get_nsc_objects=lambda _:dict(rows=[])
    result=b.dispatch("update_nsc_objects",dict(changes=[dict(object=1,volume=dict(model="DLLDefinedScattering",parameters={"2"if failure=="range"else"0":1}))]))
    assert not result["ok"]and result["error"]["code"]==("INDEX_OUT_OF_RANGE"if failure=="range"else"SETTING_REJECTED")
    assert result["error"]["details"]["partial_changes_possible"]
