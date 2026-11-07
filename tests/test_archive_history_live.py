"""Restore a different NSC model and establish new detector provenance over stdio."""
import asyncio
import json
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir


@pytest.mark.zemax
def test_archive_replaces_nsc_detector_provenance_over_stdio():
    async def scenario():
        folder = run_dir("archive_history")
        events = []
        params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "zemax_mcp"],
            cwd=PROJECT_ROOT, env={"PYTHONUTF8": "1", "ZEMAX_OUTPUT_DIR": str(folder)})
        try:
            async with Client(params, read_timeout_seconds=120) as client:
                async def call(name, args=None):
                    r = (await client.call_tool(name, args or {})).structured_content
                    events.append(dict(tool=name, arguments=args, response=r))
                    assert r and r["ok"], r
                    return r["data"]

                async def complete(task):
                    for _ in range(2400):
                        if task["state"] in {"succeeded", "failed", "cancelled"}:
                            break
                        await asyncio.sleep(.05)
                        task = await call("get_task_status", dict(task_id=task["task_id"]))
                    result = await call("get_task_result", dict(task_id=task["task_id"]))
                    assert task["state"] == "succeeded", result
                    return result

                async def model(z, pixels):
                    await call("new_system", dict(mode="NonSequential"))
                    inserted = await call("insert_nsc_objects", dict(request=dict(at=1)))
                    assert inserted["inserted"] == 1 and inserted["total"] == 2
                    await call("update_nsc_objects", dict(request=dict(changes=[
                        dict(object=1, object_type="SourceRay", data=dict(NumberOfAnalysisRays=10, ZCosine=1)),
                        dict(object=2, object_type="DetectorRectangle", z=z,
                             data=dict(NumberXPixels=pixels, NumberYPixels=pixels))])))

                await call("connect")
                await model(20, 4)
                archive = str(folder / "model_b.zar")
                await complete(await call("create_archive", dict(request=dict(path=archive))))
                await model(10, 8)
                old = await complete(await call("run_nsc_ray_trace", dict(request=dict(random_seed=42))))
                old_id = old["task"]["task_id"]
                before = await call("get_detector_data", dict(request=dict(detector=2)))
                assert before["history_known"] and before["complete"]
                assert [{k:t[k]for k in ("task_id","state")}for t in before["trace_history"]] == [dict(task_id=old_id, state="succeeded")]
                await complete(await call("load_archive", dict(request=dict(path=archive,
                    output_directory=str(folder / "model_b_restored")))))
                objects = await call("get_nsc_objects", dict(request=dict(start=2, count=1)))
                assert objects["rows"][0]["z"] == pytest.approx(20)
                restored = await call("get_detector_data", dict(request=dict(detector=2)))
                assert restored["nx"] == restored["ny"] == 4
                assert restored["trace_history"] == [] and not restored["history_known"] and not restored["complete"]
                new = await complete(await call("run_nsc_ray_trace", dict(request=dict(random_seed=42))))
                after = await call("get_detector_data", dict(request=dict(detector=2)))
                assert after["history_known"] and after["complete"]
                assert [{k:t[k]for k in ("task_id","state")}for t in after["trace_history"]] == [dict(task_id=new["task"]["task_id"], state="succeeded")]
                assert after["trace_history"][0]["task_id"] != old_id
                assert after["total_flux"] == pytest.approx(1, rel=1e-7, abs=1e-8)
                await call("disconnect")
        finally:
            (folder / "calls.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Archive provenance evidence:", folder, flush=True)
    asyncio.run(scenario())
