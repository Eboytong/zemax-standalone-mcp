"""Cancellation preserves checkpoints and distinguishes partial detector data."""
import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir

@pytest.mark.zemax
def test_composite_and_nsc_cancellation_over_stdio():
    async def scenario():
        output=run_dir("cancellation");events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(output)})
        try:
            async with Client(params,read_timeout_seconds=120)as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r));assert r and r["ok"],r
                    return r["data"]
                async def cancel_and_finish(task):
                    task=await call("cancel_task",dict(task_id=task["task_id"]))
                    for _ in range(1200):
                        if task["state"]in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.05);task=await call("get_task_status",dict(task_id=task["task_id"]))
                    assert task["state"]=="cancelled",task
                    return await call("get_task_result",dict(task_id=task["task_id"]))
                await call("connect")
                lens=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
                await call("open_lens",dict(path=lens));await call("update_merit_function",dict(mode="rms_spot_wizard"))
                hammer=await call("run_hammer_optimization",dict(request=dict(runtime_seconds=60)))
                result=await cancel_and_finish(hammer)
                assert Path(result["summary"]["cancelled_candidate"]).is_file()
                assert not result["summary"]["independent_validation_completed"]
                await call("open_lens",dict(path=lens))
                evaluated=await call("run_configuration_evaluation",dict(request=dict(configurations=[1],evaluation=dict(spot=dict(reference="ChiefRay")))))
                assert(await cancel_and_finish(evaluated))["restoration"]["restored"]
                assert(await call("get_system_settings"))["configuration"]==1
                await call("new_system",dict(mode="NonSequential"));await call("insert_nsc_objects",dict(request=dict(at=1)))
                await call("update_nsc_objects",dict(request=dict(changes=[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=10000000,ZCosine=1)),dict(object=2,object_type="DetectorRectangle",z=10,data=dict(NumberXPixels=8,NumberYPixels=8))])))
                trace=await call("run_nsc_ray_trace",dict(request={}))
                await cancel_and_finish(trace)
                partial=await call("get_detector_data",dict(request=dict(detector=2)))
                assert not partial["complete"] and 0<=partial["total_flux"]<=1+1e-8
                await call("disconnect")
        finally:
            (output/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("Cancellation evidence:",output,flush=True)
    asyncio.run(scenario())
