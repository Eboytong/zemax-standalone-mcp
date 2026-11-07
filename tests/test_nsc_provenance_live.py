"""Serial stdio references for accumulated trace options and offline history."""
import asyncio
import json
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,detector


async def model(e):
    await setup(e,2)
    await update(e,[
        dict(object=1,object_type="SourceRay",x=0,y=0,z=0,tilt_x=0,tilt_y=0,tilt_z=0,
             ref_object=0,inside_of=0,comment="controlled source",
             data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
        dict(object=2,object_type="DetectorRectangle",z=5,material="ABSORB",comment="controlled detector",
             data=dict(NumberXPixels=8,NumberYPixels=8)),
    ])


@pytest.mark.zemax
def test_nsc_trace_option_history_native():
    async def work(e):
        await model(e)
        first=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42))))
        baseline=await detector(e,2)
        assert baseline["complete"] and baseline["trace_options_known"]
        for index,options in enumerate((
            dict(use_polarization=True),
            dict(use_polarization=True,split_rays=True),
            dict(use_polarization=True,split_rays=True,scatter_rays=True),
        )):
            latest=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(
                detector_policy="accumulate",random_seed=42,**options))))
            d=await detector(e,2)
            assert d["mixed_conditions"] and d["model_matches_history"] and not d["complete"]
            assert d["trace_options_known"]
            e.check("same-model accumulated power W",d["total_flux"],index+2)
            row=latest["rows"][0]
            assert row["mixed_conditions"] and not row["complete"]
            assert len(row["trace_conditions"])==index+2
            assert all(t["state"]=="succeeded" and t["error"] is None for t in row["trace_conditions"])
        report=await e.call("export_evaluation_report",dict(task_ids=[latest["task"]["task_id"]]))
        saved=json.loads(Path(next(a["path"] for a in report["artifacts"] if a["kind"]=="json")).read_text(encoding="utf-8"))
        assert len(saved)==4 and first["task"]["task_id"] in {i["task_id"] for i in saved}
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42,use_polarization=True))))
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42,use_polarization=True,detector_policy="accumulate"))))
        d=await detector(e,2)
        assert d["complete"] and not d["mixed_conditions"]
        e.check("identical-options accumulated power W",d["total_flux"],2)
        await e.call("save_lens_as",dict(path=str(e.folder/"trace_options.zos")))
    asyncio.run(execute("nsc_trace_options",work))


@pytest.mark.zemax
def test_nsc_cancelled_history_offline_native():
    async def work(e):
        await model(e)
        await update(e,[dict(object=1,data=dict(NumberOfAnalysisRays=10000000))])
        task=await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42)))
        old=task["task_id"]
        task=await e.call("cancel_task",dict(task_id=old))
        for _ in range(2000):
            if task["state"] in {"succeeded","failed","cancelled"}:break
            await asyncio.sleep(.02)
            task=await e.call("get_task_status",dict(task_id=old))
        assert task["state"]=="cancelled"
        await update(e,[dict(object=1,data=dict(NumberOfAnalysisRays=1))])
        result=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42,detector_policy="accumulate"))))
        row=result["rows"][0]
        assert row["trace_conditions"][0]["task_id"]==old
        assert row["trace_conditions"][0]["state"]=="cancelled" and not row["complete"]
        report=await e.call("export_evaluation_report",dict(task_ids=[result["task"]["task_id"]]))
        saved=json.loads(Path(next(a["path"] for a in report["artifacts"] if a["kind"]=="json")).read_text(encoding="utf-8"))
        previous=next(i for i in saved if i["task_id"]==old)
        assert previous["result"]["task"]["state"]=="cancelled"
        markdown=Path(next(a["path"] for a in report["artifacts"] if a["kind"]=="markdown")).read_text(encoding="utf-8")
        assert '"state": "cancelled"' in markdown
    asyncio.run(execute("nsc_cancelled_report",work))
