import asyncio
import json
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_files_over_stdio():
    async def scenario():
        folder = run_dir("files")
        events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,
                                    env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content
                    events.append(dict(tool=name,arguments=args,response=r))
                    assert r and r["ok"],r
                    return r["data"]
                async def complete(task):
                    while task["state"] not in {"succeeded","failed","cancelled"}:
                        await asyncio.sleep(.05)
                        task=await call("get_task_status",{"task_id":task["task_id"]})
                    r=await call("get_task_result",{"task_id":task["task_id"]})
                    assert task["state"]=="succeeded",r
                    return r
                await call("connect")
                await call("open_lens",{"path":str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")})
                initial=await call("get_status")
                await call("copy_system",{"request":{"path":str(folder/"independent.zos")}})
                after=await call("get_status")
                assert initial["working_file"]==after["working_file"]
                assert initial["model_revision"]==after["model_revision"]
                original_radius=(await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["radius"]["value"]
                await call("open_lens",dict(path=str(folder/"independent.zos")))
                await call("update_surfaces",dict(changes=[dict(surface=1,radius=original_radius*1.01,replace_solves=True)]))
                await call("save_lens_as",dict(path=str(folder/"independent.zos"),overwrite=True))
                await call("open_lens",dict(path=initial["working_file"]))
                assert (await call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["radius"]["value"]==pytest.approx(original_radius,rel=1e-7,abs=1e-8)
                mf=str(folder/"design.mf")
                await call("save_merit_function",{"request":{"path":mf}})
                original=(await call("evaluate_merit_function"))["merit_function"]
                await call("load_merit_function",{"request":{"path":mf}})
                assert (await call("evaluate_merit_function"))["merit_function"]==pytest.approx(original,rel=1e-7,abs=1e-8)
                await call("get_project_settings")
                await call("get_external_dependencies",{"request":{"count":2}})
                await call("update_system_settings",{"settings":{"vignetting_action":"calculate"}})
                await call("update_system_settings",{"settings":{"vignetting_action":"clear","ray_aiming":{"advanced_convergence":False,"enhanced":False,"auto_pupil_shift":False,"pupil_shift_x":0}}})
                archive=str(folder/"design.zar")
                await complete(await call("create_archive",{"request":{"path":archive}}))
                await complete(await call("load_archive",{"request":{"path":archive,"output_directory":str(folder/"restored")}}))
                await call("get_system_summary")
                # Convert a fresh working design, then return to ordinary file mode.
                await call("new_system")
                project=await call("update_project_settings",{"request":{"operation":"convert","directory":str(folder/"project")}})
                assert project["is_project_directory"],project
                project=await call("update_project_settings",{"request":{"operation":"disable"}})
                assert not project["is_project_directory"],project
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            print("File evidence:",folder,flush=True)
    asyncio.run(scenario())
