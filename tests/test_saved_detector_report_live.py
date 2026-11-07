"""Native detector snapshots converted to reports without a second ray trace."""
import asyncio,json,csv
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_saved_color_volume_report_native():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DetectorVolume",z=3,data=dict(XHalfWidth=2,YHalfWidth=2,ZHalfWidth=1,NumberXPixels=3,NumberYPixels=5,NumberZPixels=4)),
            dict(object=3,object_type="DetectorColor",z=10,material="ABSORB",data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=3,NumberYPixels=5),type_settings=dict(UsePixelInterpolation=False))])
        await trace(e,"saved_sources")
        files=[]
        for obj,args in ((2,dict(width=3,height=5,depth=4)),(3,dict(width=3,height=5,color_channel="tristimulus_y"))):
            data=await detector(e,obj,**args)
            files.append(data["artifacts"][0]["path"])
        report=await e.finish(await e.call("export_evaluation_report",dict(detector_files=files,
            formats=["markdown","pdf"],include_charts=True,background=True,title="体素与颜色探测器离线报告")))
        result_file=next(a["path"]for a in report["artifacts"]if a["kind"]=="json")
        rows=json.loads(Path(result_file).read_text(encoding="utf-8"))
        snapshots=[r["result"]for r in rows if r["result"]["task"]["kind"]=="saved_detector_snapshot"]
        assert len(snapshots)==2 and len(snapshots[0]["rows"])==60
        assert snapshots[0]["trace_conditions"][0]["state"]=="succeeded"
        assert len(snapshots[0]["volume_values"])==4
        assert any(a["path"].endswith("coordinates.csv")for a in report["artifacts"])
        import pypdfium2
        pdf=Path(next(a["path"]for a in report["artifacts"]if a["kind"]=="pdf"))
        document=pypdfium2.PdfDocument(str(pdf))
        for i in range(len(document)):document[i].render(scale=1).to_pil().save(pdf.with_name(f"page-{i+1}.png"))
        assert len(document)>1
        (e.folder/"report_acceptance.json").write_text(json.dumps(dict(pdf=str(pdf),pages=len(document),snapshots=files),indent=2),encoding="utf-8")
        document.close()
        await e.call("save_lens_as",dict(path=str(e.folder/"detector_report.zos")))
    asyncio.run(execute("saved_detector_report",work))
