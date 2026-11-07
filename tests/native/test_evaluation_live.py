import asyncio
import json
import sys
import time
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_evaluation_over_stdio():
    async def scenario():
        output = run_dir("evaluation")
        events = []
        params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "zemax_mcp"], cwd=PROJECT_ROOT,
            env={"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "ZEMAX_OUTPUT_DIR": str(output)})
        try:
            async with Client(params, read_timeout_seconds=120) as client:
                async def call(tool, args=None):
                    raw = await client.call_tool(tool, args or {})
                    result = raw.structured_content
                    events.append({"tool": tool, "arguments": args, "response": result})
                    assert result and result["ok"], result
                    return result["data"]
                async def wait(task):
                    deadline = time.monotonic()+120
                    while task["state"] not in {"succeeded", "cancelled", "failed"}:
                        assert time.monotonic()<deadline
                        await asyncio.sleep(.05)
                        task = await call("get_task_status", {"task_id": task["task_id"]})
                    assert task["state"] in {"succeeded", "cancelled"}, task
                    return await call("get_task_result", {"task_id": task["task_id"]})
                await call("connect")
                source = str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
                model = await call("open_lens", {"path": source})
                index = model["surface_count"]-2
                original = (await call("get_surfaces", {"start": index, "count": 1}))["surfaces"][0]
                thickness = original["cells"]["thickness"]["value"]
                rays = await wait(await call("run_batch_ray_trace", {"request": {"rays": [
                    {"hy": .5, "py": -.5}, {"hy": .5}, {"hy": .5, "py": .5}], "opd": True}}))
                assert len(rays["rows"])==3 and rays["summary"]["succeeded"]==3, rays
                spec = {"spot": {"reference": "Centroid"}, "mtf": {"sampling": "S_32x32"}, "frequencies": [10, 25], "merit": True}
                request = {"surface": index, "cell": "thickness", "values": [thickness, thickness+.1], "evaluation": spec}
                scan = await wait(await call("run_parameter_scan", {"request": request}))
                assert scan["summary"]["succeeded"]==2 and scan["restoration"]["restored"], scan
                restored = (await call("get_surfaces", {"start": index, "count": 1}))["surfaces"][0]
                assert restored["cells"]["thickness"]["value"]==pytest.approx(thickness)
                assert restored["cells"]["thickness"]["solve"]==original["cells"]["thickness"]["solve"]
                direct = await wait(await call("run_spot_analysis", {"reference": "Centroid"}))
                assert scan["rows"][0]["metrics"][0]["value"]==pytest.approx(direct["metrics"][0]["rms_radius"], rel=1e-7, abs=1e-8)
                paged = await call("get_task_result", {"task_id": scan["task"]["task_id"], "start": 0, "count": 1})
                assert len(paged["rows"])==1 and paged["next_start"]==1
                batch = await wait(await call("run_batch_evaluation", {"request": {"paths": [source, str(output/"missing.zos")], "evaluation": spec}}))
                assert batch["summary"]["succeeded"]==1 and batch["summary"]["failed"]==1, batch
                comp = await call("compare_results", {"left_task_id": scan["task"]["task_id"], "right_task_id": scan["task"]["task_id"]})
                assert comp["compatible"] and all(m["delta"]==0 for m in comp["metrics"])
                independent = await wait(await call("run_parameter_scan", {"request": {
                    **request, "values": [thickness+.2, thickness+.3]}}))
                assert independent["summary"]["succeeded"]==2
                comp = await call("compare_results", {"left_task_id": scan["task"]["task_id"], "right_task_id": independent["task"]["task_id"]})
                assert comp["compatible"] and any(abs(m["delta"])>1e-10 for m in comp["metrics"]), comp
                assert scan["rows"][0]["conditions"]["merit_definition"]==independent["rows"][0]["conditions"]["merit_definition"]
                report = await call("export_evaluation_report", {"task_ids": [scan["task"]["task_id"], batch["task"]["task_id"]]})
                assert all(Path(a["path"]).is_file() for a in report["artifacts"])
                focus_request = {**request, "values": [thickness], "evaluation": {
                    "spot": {"reference": "Centroid"}, "focus": {"criterion": "SpotSizeRadial", "use_centroid": True}}}
                focus = await wait(await call("run_parameter_scan", {"request": focus_request}))
                assert focus["summary"]["succeeded"]==1 and focus["restoration"]["restored"]
                mismatch = await call("compare_results", {"left_task_id": scan["task"]["task_id"], "right_task_id": focus["task"]["task_id"]})
                assert not mismatch["compatible"] and mismatch["differences"]
                outside = {**request, "values": [thickness], "evaluation": {"mtf": {"maximum_frequency": 10}, "frequencies": [1000]}}
                failed_point = await wait(await call("run_parameter_scan", {"request": outside}))
                assert failed_point["summary"]["failed"]==1 and failed_point["restoration"]["restored"]
                assert failed_point["rows"][0]["error"]["code"]=="FREQUENCY_OUT_OF_RANGE"
                request["values"] = [thickness]*200
                task = await call("run_parameter_scan", {"request": request})
                task = await call("cancel_task", {"task_id": task["task_id"]})
                cancelled = await wait(task)
                assert cancelled["task"]["state"]=="cancelled" and cancelled["restoration"]["restored"]
                await call("disconnect")
        finally:
            (output/"calls.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Evaluation evidence:", output, flush=True)
    asyncio.run(scenario())


@pytest.mark.zemax
def test_native_ray_reference_and_diagnostic(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.models import BatchRays, Ray, Connect, OpenLens
    from zemax_mcp.native import NativeSession
    from types import SimpleNamespace
    native = NativeSession()
    backend = Backend(Config.from_env(), native)
    print("DIAG connect", file=sys.stderr, flush=True)
    try:
        backend.connect(Connect())
        source = str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
        backend.open_lens(OpenLens(path=source))
        target = backend.system.LDE.NumberOfSurfaces-1
        request = BatchRays(rays=[Ray(hy=.5, py=.4)]*1025)
        task = backend.run_batch_ray_trace(request)
        deadline = time.monotonic()+60
        while backend.active:
            assert time.monotonic()<deadline
            backend.tick()
            time.sleep(.01)
        result = backend._full_result(task["task_id"])
        assert result["task"]["state"]=="succeeded", result
        assert len(result["rows"])==1025 and result["summary"]["succeeded"]==1025
        mfe = backend.system.MFE
        for coordinate, operand in enumerate(("REAX", "REAY")):
            reference = mfe.GetOperandValue(native.enum(native.api.Editors.MFE.MeritOperandType, operand), target, 1, 0, .5, 0, .4, 0, 0)
            assert result["rows"][0]["position"][coordinate]==pytest.approx(reference, rel=1e-7, abs=1e-8)
        print("DIAG before merit wizard", file=sys.stderr, flush=True)
        backend.update_merit_function(__import__('zemax_mcp.models', fromlist=['MeritPatch']).MeritPatch(mode="rms_spot_wizard"))
        print("DIAG after merit wizard", file=sys.stderr, flush=True)
        for _ in range(2):
            print("DIAG before CalculateMeritFunction", file=sys.stderr, flush=True)
            backend.evaluate_merit_function(None)
            print("DIAG after CalculateMeritFunction", file=sys.stderr, flush=True)
        for ray_type in ("Paraxial", "Real"):
            task = backend.run_batch_ray_trace(BatchRays(rays=[Ray(py=2)], ray_type=ray_type))
            while backend.active:
                backend.tick()
                time.sleep(.01)
            result = backend._full_result(task["task_id"])
            assert result["task"]["state"]=="succeeded", result
            assert result["rows"][0]["state"] in {"error", "vignetted", "succeeded"}
    finally:
        print("DIAG disconnect", file=sys.stderr, flush=True)
        backend.shutdown()
