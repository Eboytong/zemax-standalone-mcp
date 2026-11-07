import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir

@pytest.mark.zemax
def test_tolerancing_over_stdio():
    async def scenario():
        folder=run_dir("tolerancing")
        events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r))
                    assert r and r["ok"],r
                    return r["data"]
                await call("connect")
                await call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
                await call("generate_tolerances",{"request":{"surface_thickness":.01,"start_surface":1,"end_surface":2}})
                await call("update_tolerances",{"request":{"mode":"replace","operands":[{"type":"TTHI","param1":1,"param2":2,"minimum":-.01,"maximum":.01}]}})
                await call("get_tolerances",{"request":{}})
                for mode in ("sensitivity","monte_carlo","inverse_limit","inverse_increment"):
                    t=await call("run_tolerance_analysis",{"request":{"mode":mode,"samples":3,"save_samples":2 if mode=="monte_carlo"else 0,"compensation":"None","allow_tolerance_update":mode.startswith("inverse"),"maximum_criterion":.05}})
                    for _ in range(2000):
                        if t["state"] in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.05);t=await call("get_task_status",dict(task_id=t["task_id"]))
                    r=await call("get_task_result",dict(task_id=t["task_id"]))
                    assert t["state"]=="succeeded",r
                    if mode=="monte_carlo":
                        assert r["rows"],r
                        assert len(r["summary"]["saved_samples"])==2,r
                        await call("summarize_tolerance_results",{"request":{"task_id":t["task_id"],"criterion_column":0,"threshold":1,"unit":"native criterion"}})
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Tolerance evidence:",folder,flush=True)
    asyncio.run(scenario())
