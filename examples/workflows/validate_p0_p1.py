"""Execute a real P0/P1 optical workflow on a working copy of an official lens."""

import asyncio
import json
import time
from pathlib import Path

from zemax_mcp.bridge import Bridge
from zemax_mcp.config import PROJECT_ROOT


SAMPLE = Path(r"C:\Users\tonge\Documents\Zemax\Samples\Sequential\Objectives\Cooke 40 degree field.zos")


async def validate():
    bridge = Bridge()
    evidence = []

    async def call(command, args=None):
        result = await bridge.request(command, args)
        evidence.append({"command": command, "arguments": args or {}, "response": result})
        if not result["ok"]:
            raise RuntimeError(f"{command}: {result['error']}")
        return result["data"]

    async def run(command, args):
        started = await call(command, args)
        task_id = started["task_id"]
        deadline = time.monotonic() + 180
        while True:
            status = await call("get_task_status", {"task_id": task_id})
            if status["state"] in {"failed", "cancelled"}:
                raise RuntimeError(f"{command}: {status}")
            if status["state"] == "succeeded":
                return await call("get_task_result", {"task_id": task_id})
            if time.monotonic() > deadline:
                await call("cancel_task", {"task_id": task_id})
                raise TimeoutError(command)
            await asyncio.sleep(0.15)

    from datetime import datetime
    output = PROJECT_ROOT / ".local" / "runs" / ("acceptance_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    output.mkdir(parents=True, exist_ok=True)
    try:
        print("connect", flush=True)
        await call("connect")
        await call("get_capabilities")
        summary = await call("open_lens", {"path": str(SAMPLE)})
        assert summary["mode"] == "Sequential"
        assert summary["lens_units"] == "Millimeters"
        await call("get_surfaces", {"start": 0, "count": 50})
        print("baseline analyses", flush=True)
        baseline_mtf = await run("run_fft_mtf", {"maximum_frequency": 50, "sampling": "S_64x64"})
        baseline_spot = await run("run_spot_analysis", {"reference": "Centroid"})
        index = summary["surface_count"] - 2
        surfaces = await call("get_surfaces", {"start": index, "count": 1})
        thickness = surfaces["surfaces"][0]["cells"]["thickness"]["value"]
        await call("update_surfaces", {"changes": [{"surface": index, "thickness": thickness + 0.2, "replace_solves": True}]})
        print("focus", flush=True)
        focus = await run("run_quick_focus", {"criterion": "SpotSizeRadial", "use_centroid": True, "replace_solve": True})
        await call("update_merit_function", {"mode": "rms_spot_wizard", "reference": "Centroid", "rings": 3,
                                            "operands": [{"type": "EFFL", "target": summary["first_order"]["effective_focal_length"], "weight": 1,
                                                          "parameters": {"3": 2}}]})
        await call("set_variables", {"variables": [{"surface": index, "cell": "thickness", "variable": True}]})
        initial = await call("evaluate_merit_function")
        print("local optimization", flush=True)
        optimization = await run("run_local_optimization", {"cycles": "Fixed_5_Cycles", "number_of_cores": 1})
        final_mtf = await run("run_fft_mtf", {"maximum_frequency": 50, "sampling": "S_64x64"})
        final_spot = await run("run_spot_analysis", {"reference": "Centroid"})
        await call("save_lens_as", {"path": str(output / "optimized_cooke.zos"), "overwrite": True})
        comparison = {
            "source": str(SAMPLE), "focus": focus,
            "initial_merit": initial["merit_function"],
            "final_merit": optimization["after"]["merit_function"],
            "baseline_spot": baseline_spot["metrics"], "final_spot": final_spot["metrics"],
            "baseline_mtf_context": baseline_mtf["context"], "final_mtf_context": final_mtf["context"],
            "gui_comparison": "not_performed",
        }
        with (output / "comparison.json").open("w", encoding="utf-8") as stream:
            json.dump(comparison, stream, ensure_ascii=False, indent=2)
        print(json.dumps({"initial_merit": comparison["initial_merit"], "final_merit": comparison["final_merit"],
                          "baseline_spot": comparison["baseline_spot"], "output": str(output)}, ensure_ascii=False), flush=True)
        await call("disconnect")
        return comparison
    finally:
        await bridge.close()
        with (output / "calls.json").open("w", encoding="utf-8") as stream:
            json.dump(evidence, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(validate())
