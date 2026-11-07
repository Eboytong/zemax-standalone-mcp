import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir


@pytest.mark.zemax
def test_native_layout_images_over_stdio():
    async def scenario():
        folder=run_dir("layouts");events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120)as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r));assert r and r["ok"],r
                    return r["data"]
                async def complete(t):
                    for _ in range(1200):
                        if t["state"]in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.05);t=await call("get_task_status",dict(task_id=t["task_id"]))
                    r=await call("get_task_result",dict(task_id=t["task_id"]));assert t["state"]=="succeeded",r
                    return r
                await call("connect");await call("get_capabilities")
                await call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
                tasks=[]
                for kind in ["cross_section","viewer_3d","shaded_model"]:
                    result=await complete(await call("run_layout_export",dict(request=dict(kind=kind,path=str(folder/(kind+".png")),width=640,height=480))))
                    tasks.append(result["task"]["task_id"])
                await call("new_system",dict(mode="NonSequential"));await call("insert_nsc_objects",dict(request=dict(at=2,count=1)))
                await call("update_nsc_objects",dict(request=dict(changes=[dict(object=1,object_type="SourceRay",data=dict(NumberOfLayoutRays=5,ZCosine=1)),dict(object=2,object_type="DetectorRectangle",z=10,data=dict(NumberXPixels=8,NumberYPixels=8))])))
                for kind in ["nsc_3d","nsc_shaded"]:
                    result=await complete(await call("run_layout_export",dict(request=dict(kind=kind,path=str(folder/(kind+".png")),width=640,height=480))))
                    tasks.append(result["task"]["task_id"])
                report=await complete(await call("export_evaluation_report",dict(task_ids=tasks,formats=["markdown","pdf"],background=True)))
                from PIL import Image
                for kind in ["cross_section","viewer_3d","shaded_model","nsc_3d","nsc_shaded"]:
                    with Image.open(folder/(kind+".png"))as image:assert image.size==(640,480)
                import pypdfium2
                pdf=Path(next(a["path"]for a in report["artifacts"]if a["kind"]=="pdf"));document=pypdfium2.PdfDocument(str(pdf))
                for i in range(len(document)):document[i].render(scale=1).to_pil().save(pdf.with_name(f"page-{i+1}.png"))
                document.close();await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("Layout evidence:",folder,flush=True)
    asyncio.run(scenario())
