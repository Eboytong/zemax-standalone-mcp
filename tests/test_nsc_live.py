import asyncio,json,sys
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
import pytest
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir

@pytest.mark.zemax
def test_nsc_over_stdio():
    async def scenario():
        folder=run_dir("nsc");events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r));assert r and r["ok"],r
                    return r["data"]
                async def complete(t):
                    for _ in range(2000):
                        if t["state"] in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.05);t=await call("get_task_status",dict(task_id=t["task_id"]))
                    r=await call("get_task_result",dict(task_id=t["task_id"]));assert t["state"]=="succeeded",r
                    return r
                await call("connect");await call("new_system",dict(mode="NonSequential"))
                await call("get_nsc_objects",{"request":{}})
                await call("insert_nsc_objects",{"request":{"at":1}})
                await call("update_nsc_objects",{"request":{"changes":[{"object":1,"object_type":"SourceRay","data":{"NumberOfAnalysisRays":10,"ZCosine":1}},{"object":2,"object_type":"DetectorRectangle","z":10,"data":{"NumberXPixels":8,"NumberYPixels":8}}]}})
                rows=await call("get_nsc_objects",{"request":{}})
                zrd=str(folder/"trace.zrd")
                await call("clear_detectors",{"request":{}})
                await complete(await call("run_nsc_ray_trace",{"request":{"save_zrd":zrd,"random_seed":42}}))
                first=await call("get_detector_data",{"request":{"detector":2}})
                assert first["total_flux"]==pytest.approx(1,rel=1e-7,abs=1e-8)
                await complete(await call("run_nsc_ray_trace",{"request":{"detector_policy":"accumulate","random_seed":42}}))
                second=await call("get_detector_data",{"request":{"detector":2}})
                assert second["total_flux"]==pytest.approx(first["total_flux"]*2,rel=1e-7,abs=1e-8)
                await complete(await call("read_zrd",{"request":{"path":zrd,"max_segments":3}}))
                replay=await complete(await call("run_zrd_replay",{"request":{"path":zrd,"detector":2,"filter":"H2"}}))
                replay_full=json.loads(Path(next(a["path"]for a in replay["artifacts"]if a["kind"]=="json")).read_text(encoding="utf-8"))
                grid=replay_full["grids"][0]
                # Native irradiance is W/cm^2; this fixture uses millimeter pixels.
                replay_power=sum(v for row in grid["values"]for v in row)*grid["dx"]*grid["dy"]/100
                assert replay_power==pytest.approx(1,rel=1e-7,abs=1e-8),replay_full
                assert(await call("get_detector_data",{"request":{"detector":2}}))["total_flux"]==pytest.approx(2,rel=1e-7,abs=1e-8)
                await call("copy_nsc_objects",{"request":{"start":2,"at":3}})
                await call("delete_nsc_objects",{"request":{"at":3}})
                await call("insert_nsc_objects",{"request":{"at":3}})
                updated=await call("update_nsc_objects",{"request":{"changes":[{"object":3,"object_type":"StandardLens","z":20,"material":"N-BK7","data":{"Thickness":1},"volume":{"model":"AngleScattering","settings":{"MeanPath":10,"Angle":5}},"faces":[{"face":0,"scatter_model":"Lambertian","settings":{"ScatterFraction":.1}}]},{"object":1,"spectrum":{"mode":"UniformPowerSpectrum","settings":{"SpectrumCount":5,"WavelengthFrom":.5,"WavelengthTo":.6}}}]}})
                assert updated["rows"][2]["volume"]["model"]=="AngleScattering"
                assert updated["rows"][0]["spectrum"]["settings"]["SpectrumCount"]==5
                await call("set_variables",dict(variables=[dict(object=3,cell="ZPosition",variable=True)]))
                assert any(v.get("object")==3 for v in (await call("get_variables"))["variables"])
                await call("set_variables",dict(variables=[dict(object=3,cell="ZPosition",variable=False)]))
                await call("delete_nsc_objects",{"request":{"at":3}})
                await call("save_lens_as",dict(path=str(folder/"nsc.zos")))
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("NSC evidence:",folder,flush=True)
    asyncio.run(scenario())
