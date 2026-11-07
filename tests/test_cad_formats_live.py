"""Record per-format native export availability; each outcome retains its reason."""
import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from zemax_mcp.exports import CAD_EXTENSIONS
from support.paths import run_dir
from support.native import server_parameters

@pytest.mark.zemax
def test_installed_cad_format_availability():
    async def scenario():
        folder=run_dir("cad_formats")
        events=[];outcomes=[]
        parameters=server_parameters(folder)
        try:
            async with Client(parameters,read_timeout_seconds=120)as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content
                    events.append(dict(tool=name,arguments=args,response=r));return r
                assert(await call("connect"))["ok"]
                assert(await call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"))))["ok"]
                for kind,extensions in CAD_EXTENSIONS.items():
                    r=await call("run_cad_export",dict(request=dict(format=kind,path=str(folder/(kind+sorted(extensions)[0])),end=2)))
                    if r["ok"]:
                        task=r["data"]
                        for _ in range(2400):
                            if task["state"]in {"succeeded","failed","cancelled"}:break
                            await asyncio.sleep(.05);task=(await call("get_task_status",dict(task_id=task["task_id"])))["data"]
                        result=(await call("get_task_result",dict(task_id=task["task_id"])))["data"]
                        if task["state"]=="succeeded" and kind!="VisualizationJSON":
                            assert task["close_attempted"] and not task.get("cleanup_warnings"),task
                            assert Path(result["path"]).is_file(),result
                            settings=task["settings"]
                            assert {"FileType","Tolerance","Configuration","FirstSurface","LastSurface"} <= set(settings["checked_fields"]),settings
                            assert settings["requested"]["format"]==kind and settings["requested"]["end"]==2,settings
                        outcomes.append(dict(format=kind,state=task["state"],error=task.get("error"),artifacts=result.get("artifacts"),settings=task.get("settings")))
                    else:outcomes.append(dict(format=kind,state="rejected",error=r["error"]))
                    print("CAD",kind,outcomes[-1]["state"],flush=True)
                assert all(o["state"]=="succeeded"for o in outcomes if o["format"]in {"STEP","VisualizationJSON"}),outcomes
                assert(await call("disconnect"))["ok"]
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            (folder/"formats.json").write_text(json.dumps(outcomes,ensure_ascii=False,indent=2),encoding="utf-8")
            print("CAD format evidence:",folder,flush=True)
    asyncio.run(scenario())


@pytest.mark.zemax
@pytest.mark.parametrize('format,options',[
    ('STEP',dict(ray_pattern='Grid',delete_vignetted=True,ray_layer=2,lens_layer=3,spline_segments='N_064')),
    ('STL',dict(angular_tolerance='High',export_dummy_surfaces=True,dummy_thickness=.1)),
    ('SAT',dict(file_version='Current',auto_name_faces=True)),
])
def test_cad_extended_settings(format,options):
    from support.native import execute
    async def scenario(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_system_settings')
        started=await e.call('run_cad_export',dict(request=dict(path=str(e.folder/('settings'+sorted(CAD_EXTENSIONS[format])[0])),
            format=format,end=2,number_of_rays=8,**options)))
        result=await e.finish(started)
        task=await e.call('get_task_status',dict(task_id=started['task_id']))
        assert task['close_attempted'] and not task.get('cleanup_warnings'),task
        assert Path(result['path']).is_file(),result
        assert task['settings']['requested']['format']==format
        assert len(task['settings']['checked_fields'])>=11+len(options)-int('export_dummy_surfaces'in options),task
        after=await e.call('get_system_settings')
        assert before==after,(before,after)
    asyncio.run(execute('cad_settings_'+format.lower(),scenario))
