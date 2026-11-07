import asyncio,json,sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir

@pytest.mark.zemax
def test_cad_and_pdf_over_stdio():
    async def scenario():
        folder=run_dir("exports");events=[]
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
                await call("connect");await call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
                await complete(await call("run_cad_export",{"request":{"path":str(folder/"design.step"),"end":2}}))
                geometry=await complete(await call("run_cad_export",{"request":{"path":str(folder/"visualization.json"),"format":"VisualizationJSON","end":2}}))
                assert geometry["triangles"]>0,geometry
                psf=await complete(await call("run_analysis",{"request":{"kind":"fft_psf"}}))
                mtf=await complete(await call("run_fft_mtf",dict(sampling="S_64x64")))
                report=await complete(await call("export_evaluation_report",dict(task_ids=[psf["task"]["task_id"],mtf["task"]["task_id"]],formats=["markdown","pdf"],background=True,include_charts=True)))
                pdf=next(a["path"]for a in report["artifacts"]if a["kind"]=="pdf")
                import pypdfium2
                document=pypdfium2.PdfDocument(pdf)
                for i in range(len(document)):
                    document[i].render(scale=1).to_pil().save(Path(pdf).with_name(f"page-{i+1}.png"))
                document.close()
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("Export evidence:",folder,flush=True)
    asyncio.run(scenario())
