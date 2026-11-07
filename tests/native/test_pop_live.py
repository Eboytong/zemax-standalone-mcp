import asyncio,json,sys,math
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir

@pytest.mark.zemax
def test_pop_over_stdio():
    async def scenario():
        folder=run_dir("pop");events=[]
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
                await call("connect");await call("new_system")
                await call("insert_surfaces",dict(at=1))
                await call("update_system_settings",{"settings":{"aperture_value":10,"wavelengths":[{"wavelength_um":.55}]}})
                await call("update_surfaces",{"changes":[{"surface":1,"thickness":0,"semi_diameter":10,"replace_solves":True}]})
                result=await complete(await call("run_pop",{"request":{"end_surface":2,"beam_parameters":{"0":1,"1":1},"fiber_type":"GaussianWaist"}}))
                assert result["metrics"]["receiver_efficiency"]==pytest.approx(1,rel=1e-7,abs=1e-8)
                beam=next(a["path"]for a in result["artifacts"]if a["kind"]=="beam")
                await call("get_beam_file",{"request":{"path":beam,"count":2}})
                await call("get_task_result",dict(task_id=result["task"]["task_id"],grid=0,width=4,height=3))
                await complete(await call("run_pop_convergence",{"request":{"settings":{"end_surface":2,"save_output_beam":False},"samplings":["S_64x64","S_128x128"],"widths":[[8,8]],"metric":"integrated_power","absolute_tolerance":1e-6,"relative_tolerance":1e-6}}))
                await complete(await call("run_pop_convergence",{"request":{"settings":{"end_surface":2,"save_output_beam":False},"sampling_pairs":[["S_64x64","S_128x128"],["S_128x128","S_256x256"]],"widths":[[8,8]],"metric":"integrated_power","absolute_tolerance":1e-5,"relative_tolerance":1e-5}}))
                await call("update_surfaces",{"changes":[{"surface":1,"thickness":100}]})
                propagated=await complete(await call("run_pop",{"request":{"end_surface":2,"beam_parameters":{"0":.1,"1":.1},"x_sampling":"S_256x256","y_sampling":"S_256x256","x_width":2,"y_width":2,"save_all_surfaces":True}}))
                assert propagated["intermediate_beam_files"],propagated
                full=json.loads(Path(next(a["path"]for a in propagated["artifacts"]if a["kind"]=="json")).read_text(encoding="utf-8"))
                g=full["grids"][0];power=sum(v for row in g["values"]for v in row if v is not None)
                mx=sum((g["min_x"]+ix*g["dx"])**2*v for row in g["values"]for ix,v in enumerate(row)if v is not None)/power
                expected=.1*math.sqrt(1+(100/(math.pi*.1**2/.00055))**2)
                measured=2*math.sqrt(mx)
                (folder/"gaussian-reference.json").write_text(json.dumps(dict(expected_radius_mm=expected,measured_radius_mm=measured,relative_tolerance=5e-4,definition="1/e^2 irradiance radius from second moment",distance_mm=100,wavelength_um=.55,waist_mm=.1)),encoding="utf-8")
                assert measured==pytest.approx(expected,rel=5e-4)
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("POP evidence:",folder,flush=True)
    asyncio.run(scenario())
