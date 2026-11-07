import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir

@pytest.mark.zemax
def test_configurations_and_global_over_stdio():
    async def scenario():
        folder=run_dir("configurations")
        events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r))
                    assert r and r["ok"],r
                    return r["data"]
                async def complete(t):
                    for _ in range(1000):
                        if t["state"] in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.05);t=await call("get_task_status",dict(task_id=t["task_id"]))
                    r=await call("get_task_result",dict(task_id=t["task_id"]))
                    assert t["state"]=="succeeded",r
                    return r
                await call("connect")
                lens=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
                await call("open_lens",dict(path=lens))
                before=await call("get_configurations",{"request":{}})
                await call("update_configurations",{"request":{"actions":[{"action":"add","copy_current":True}]}})
                await call("update_configurations",{"request":{"operands":[{"type":"THIC","parameters":{"1":1},"cells":[{"configuration":1,"value":3},{"configuration":2,"value":4}]}]}})
                mce=await call("get_configurations",{"request":{}})
                row=mce["rows"][-1]["operand"]
                await call("set_configuration",{"configuration":1})
                assert (await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]==pytest.approx(3)
                await call("set_configuration",{"configuration":2})
                assert (await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]==pytest.approx(4)
                await call("update_configurations",{"request":{"operands":[{"operand":row,"cells":[{"configuration":2,"solve":{"mode":"config_pickup","configuration":1,"operand":row}}]}]}})
                await call("get_configurations",{"request":{}})
                assert (await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]==pytest.approx(3)
                await call("get_constraint_coverage")
                await call("set_variables",{"variables":[{"operand":row,"configuration":1,"variable":True}]})
                variables=await call("get_variables")
                assert any(v.get("scope")=="configuration"for v in variables["variables"])
                await call("set_variables",{"variables":[{"operand":row,"configuration":1,"variable":False}]})
                evaluated=await complete(await call("run_configuration_evaluation",{"request":{"configurations":[1,2],"evaluation":{"spot":{"reference":"ChiefRay"}}}}))
                assert len(evaluated["rows"])==2 and evaluated["restoration"]["restored"]
                saved=str(folder/"mce.zos");await call("save_lens_as",dict(path=saved));await call("open_lens",dict(path=saved))
                assert (await call("get_configurations",{"request":{}}))["configuration_count"]==2
                await call("new_system")
                await call("update_system_settings",dict(settings=dict(aperture_value=2,adjust_index_to_environment=True)))
                await call("update_surfaces",dict(changes=[dict(surface=1,thickness=10,tce=100,semi_diameter=1,replace_solves=True),dict(surface=2,semi_diameter=1,replace_solves=True)]))
                await call("update_configurations",{"request":{"actions":[{"action":"add","copy_current":True}],"operands":[{"type":"TEMP","cells":[{"configuration":1,"value":20},{"configuration":2,"value":30}]},{"type":"PRES","cells":[{"configuration":1,"value":1},{"configuration":2,"value":.9}]},{"type":"THIC","parameters":{"1":1},"cells":[{"configuration":1,"value":10},{"configuration":2,"value":10}]}]}})
                thermal_row=(await call("get_configurations",{"request":{}}))["rows"][-1]["operand"]
                await call("update_configurations",{"request":{"operands":[{"operand":thermal_row,"cells":[{"configuration":2,"solve":{"mode":"thermal_pickup","configuration":1}}]}]}})
                await call("set_configuration",dict(configuration=2))
                thermal=(await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]
                assert thermal==pytest.approx(10*(1+100e-6*(30-20)),rel=1e-7,abs=1e-8)
                thermal_path=str(folder/"thermal.zos")
                await call("save_lens_as",dict(path=thermal_path));await call("open_lens",dict(path=thermal_path))
                assert(await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]==pytest.approx(thermal,rel=1e-7,abs=1e-8)
                await call("open_lens",dict(path=lens))
                await call("set_variables",{"variables":[{"surface":1,"cell":"radius","replace_solve":True},{"surface":6,"cell":"thickness","replace_solve":True}]})
                await call("update_merit_function",{"mode":"rms_spot_wizard"})
                for name in ("run_global_optimization","run_hammer_optimization"):
                    await call("open_lens",dict(path=lens))
                    variables=(await call("get_variables"))["variables"]
                    await call("set_variables",dict(variables=[dict(surface=v["surface"],cell=v["cell"],variable=False)for v in variables]))
                    await call("set_variables",dict(variables=[dict(surface=6,cell="thickness",variable=True,replace_solve=True)]))
                    await call("update_merit_function",{"mode":"rms_spot_wizard"})
                    optimized=await complete(await call(name,{"request":{"runtime_seconds":1}}))
                    assert optimized["summary"]["independent_validation_completed"]
                await call("open_lens",dict(path=lens))
                await call("set_variables",{"variables":[{"surface":1,"cell":"radius","replace_solve":True},{"surface":6,"cell":"thickness","replace_solve":True}]})
                await call("update_merit_function",{"mode":"rms_spot_wizard"})
                multiple=await complete(await call("run_multistart_optimization",{"request":{"starts":[[{"surface":1,"radius":50}],[{"surface":1,"radius":55}]],"optimization":{"cycles":"Fixed_1_Cycle"},"evaluation":{"merit":True}}}))
                assert multiple["summary"]["retained_best"]
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Configuration evidence:",folder,flush=True)
    asyncio.run(scenario())
