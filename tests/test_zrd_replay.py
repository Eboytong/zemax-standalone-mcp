"""Printed native power is separate from an inferred integral or execution success."""
import pytest
from zemax_mcp.zrd_replay import replay_text_summary


@pytest.mark.parametrize("label,unit",[("总功率","瓦特"),("Total Power","Watts"),("Total Power","W")])
def test_explicit_watt_total_with_display_precision(label,unit):
    r=replay_text_summary(["最大极角: 180 deg, 总撞击数 = 402",f"{label}: 3.2579E-03 {unit}"])
    assert r["extraction_status"]=="available" and r["hit_count"]==402
    assert r["total_power"]["value"]==pytest.approx(.0032579)
    assert r["total_power"]["display_rounding_W"]==pytest.approx(5e-8)


def test_zero_has_no_arbitrary_large_rounding_allowance():
    r=replay_text_summary(["Total Hits = 0","Total Power: 0.0000E+00 Watts"])
    assert r["total_power"]["value"]==0 and r["total_power"]["display_rounding_W"]==0
    assert r["hit_count"]==0


@pytest.mark.parametrize("lines",[
    [],["峰光强度: 1.0 瓦特/球面度"],["总功率: 1.0 流明"],["总功率: 1.0 毫瓦特"],
    ["Total Power: NaN Watts"],["Total Power: 1e999 Watts"],["Total Power: -1 Watts"],
    ["Total Power: 1 Watts","Total Power: 2 Watts"],
    ["Total Power: 1 Watts","Total Power: 2 Lumens"],
])
def test_ambiguous_units_and_invalid_rows_remain_unavailable(lines):
    r=replay_text_summary(lines)
    assert r["extraction_status"]=="unavailable" and r["total_power"]is None
    assert r["unavailable_reason"]


def replay_backend(tmp_path,ignored=None,close=True):
    from enum import IntEnum
    from types import SimpleNamespace as N
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    class DataType(IntEnum):
        PositionSpace=0
        IncidentFlux=0
        LuminousIntensity=3
        RadiantIntensity=3
    class ShowAs(IntEnum):
        CrossSection=0
        FalseColor=1
    class Settings:
        def __init__(self):
            object.__setattr__(self,"Filter","")
            object.__setattr__(self,"RayDatabaseFilename","")
            object.__setattr__(self,"DataType",DataType.PositionSpace)
            object.__setattr__(self,"ShowAs",ShowAs.CrossSection)
            self.number=2
            object.__setattr__(self,"Detector",N(SetDetectorNumber=lambda value: setattr(self,"number",value)if ignored!="Detector"else None,
                GetDetectorNumber=lambda:self.number))
        def __setattr__(self,name,value):
            if name!=ignored:object.__setattr__(self,name,value)
        def GetType(self):return N(GetProperty=lambda name:N(PropertyType=DataType if name=="DataType"else ShowAs))
    settings=Settings();closed=[]
    tool=N(GetSettings=lambda:settings,Close=lambda:(closed.append(True),close)[1])
    native=N(system=N(Mode="NonSequential",SystemFile=str(tmp_path/"working.zos"),UpdateFileLists=lambda:None,
        Analyses=N(New_Analysis=lambda _:tool)),api=N(Analysis=N(AnalysisIDM=N(DetectorViewer="viewer"))))
    native.enum=lambda kind,name:kind.__members__[name]
    native.set_enum=lambda obj,name,value:setattr(obj,name,native.enum(obj.GetType().GetProperty(name).PropertyType,value))
    b=Backend(Config(tmp_path,tmp_path),native)
    b._object=lambda _:None
    b.started=[]
    def start(kind,tool,actual,**kwargs):
        b.started.append(actual)
        return kwargs["collector"](dict(native=tool,settings=actual))
    b._start_task=start
    b._collect_general_analysis=lambda _:dict(native_preamble=["总功率: 1.0000E+00 瓦特"],grids=[])
    path=tmp_path/"input.zrd";path.write_bytes(b"ordinary native stub only")
    return b,path,closed


def test_native_enum_alias_uses_value_identity(tmp_path,monkeypatch):
    import zemax_mcp.nonsequential as module
    monkeypatch.setattr(module,"scalar_settings",lambda _: {})
    b,path,closed=replay_backend(tmp_path)
    result=b.dispatch("run_zrd_replay",dict(path=str(path),detector=3,filter="X_WAVERANGE(3,0.5,0.6)",data_type="RadiantIntensity"))
    assert result["ok"],result
    assert b.started[0]["requested_data_type"]=="RadiantIntensity"
    assert result["data"]["native_replay_summary"]["total_power"]["value"]==1
    assert result["data"]["native_replay_summary"]["filter"]=="X_WAVERANGE(3,0.5,0.6)"
    assert not closed  # Resource ownership transferred to the native task mechanism.


@pytest.mark.parametrize("ignored",["Filter","RayDatabaseFilename","DataType","ShowAs","Detector"])
def test_replay_setting_rejected_before_start_and_closed(tmp_path,ignored):
    b,path,closed=replay_backend(tmp_path,ignored)
    result=b.dispatch("run_zrd_replay",dict(path=str(path),detector=3,filter="H3",data_type="RadiantIntensity"))
    assert result["error"]["code"]=="SETTING_REJECTED",result
    assert not b.started and len(closed)==1 and not b.requires_reconnect
    assert b.revision==0


def test_replay_close_failure_blocks_following_work(tmp_path):
    b,path,closed=replay_backend(tmp_path,"Filter",close=False)
    result=b.dispatch("run_zrd_replay",dict(path=str(path),detector=3,filter="H3"))
    assert result["error"]["code"]=="CLEANUP_FAILED" and b.requires_reconnect
    assert b.dispatch("run_zrd_replay",dict(path=str(path),detector=3))["error"]["code"]=="RECONNECT_REQUIRED"
