import asyncio
import json
import sys
import time
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir


@pytest.mark.zemax
def test_real_tools_over_stdio():
    async def scenario():
        output = run_dir("live")
        events = []
        params = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "zemax_mcp"], cwd=PROJECT_ROOT,
            env={"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "ZEMAX_OUTPUT_DIR": str(output)},
        )
        try:
            async with Client(params, read_timeout_seconds=90) as client:
                async def call(name, arguments=None, expected_error=None):
                    raw = await client.call_tool(name, arguments or {})
                    response = raw.structured_content
                    assert response is not None, raw
                    events.append({"tool": name, "arguments": arguments or {}, "response": response})
                    if expected_error:
                        assert not response["ok"] and response["error"]["code"] == expected_error, response
                    else:
                        assert response["ok"], response
                    return response["data"]

                async def run(name, arguments):
                    task = await call(name, arguments)
                    deadline = time.monotonic() + 90
                    while task["state"] not in {"succeeded", "failed", "cancelled"}:
                        assert time.monotonic() < deadline, task
                        await asyncio.sleep(0.1)
                        task = await call("get_task_status", {"task_id": task["task_id"]})
                    assert task["state"] == "succeeded", task
                    return await call("get_task_result", {"task_id": task["task_id"]})

                await call("connect")
                source = r"C:\Users\tonge\Documents\Zemax\Samples\Sequential\Objectives\Cooke 40 degree field.zos"
                original = await call("open_lens", {"path": source})
                summary = await call("get_system_summary")
                assert summary["surface_count"] == original["surface_count"]
                assert summary["first_order"]["effective_focal_length"] == pytest.approx(original["first_order"]["effective_focal_length"])
                settings = await call("update_system_settings", {"settings": {
                    "lens_units": "Centimeters", "title": "MCP 光学验收", "notes": "受控工作副本",
                    "aperture_type": "EntrancePupilDiameter", "aperture_value": 10,
                    "field_type": "Angle", "fields": [{"x": 0, "y": 0}, {"x": 0, "y": 14}],
                    "wavelengths": [{"wavelength_um": 0.55}, {"wavelength_um": 0.65, "weight": 0.8}],
                    "primary_wavelength": 1, "temperature_c": 25, "pressure_atm": 0.9,
                    "adjust_index_to_environment": True,
                }})
                assert settings["wavelengths"][0]["wavelength_um"] == 0.55
                assert settings["lens_units"] == "Centimeters" and settings["title"] == "MCP 光学验收"
                actual_settings = await call("get_system_settings")
                assert actual_settings["lens_units"] == "Centimeters"
                assert actual_settings["wavelengths"][0]["wavelength_um"] == 0.55
                assert actual_settings["title"] == "MCP 光学验收"
                await call("update_system_settings", {"settings": {"lens_units": "Millimeters"}})
                all_spots = await run("run_spot_analysis", {"reference": "Centroid"})
                native_rms_line = next(line for line in all_spots["native_header"] if "RMS光斑半径" in line)
                native_rms = float(native_rms_line.split(":", 1)[1].split()[0])
                assert all_spots["metrics"][0]["rms_radius"] == pytest.approx(native_rms, rel=1e-8)
                assert "µm" in native_rms_line
                selected = await run("run_spot_analysis", {"reference": "Centroid", "field": 2})
                assert len(selected["metrics"]) == 1
                assert selected["metrics"][0]["rms_radius"] == pytest.approx(all_spots["metrics"][1]["rms_radius"], rel=1e-8)
                chief = await run("run_spot_analysis", {"reference": "ChiefRay", "field": 2, "wavelength": 1})
                centroid = await run("run_spot_analysis", {"reference": "Centroid", "field": 2, "wavelength": 1})
                assert chief["metrics"][0]["rms_radius"] >= centroid["metrics"][0]["rms_radius"] - 1e-8
                await call("run_fft_mtf", {"frequency_unit": "CyclesPerMilliradian"}, "UNIT_MISMATCH")
                await call("update_system_settings", {"settings": {"mtf_units": "CyclesPerMilliradian"}})
                mtf = await run("run_fft_mtf", {"frequency_unit": "CyclesPerMilliradian", "sampling": "S_64x64"})
                assert mtf["task"]["settings"]["frequency_space"] == "object angular"
                assert all(len(s["x"]) == len(s["y"]) for s in mtf["series"])

                # Start an expensive analysis to exercise busy/cancel against the actual API.
                await call("update_system_settings", {"settings": {"fields": [{"x": 0, "y": i * 0.5} for i in range(30)]}})
                task = await call("run_fft_mtf", {"frequency_unit": "CyclesPerMilliradian", "sampling": "S_512x512"})
                if task["state"] == "running":
                    await call("new_system", {}, "SYSTEM_BUSY")
                    state = await call("cancel_task", {"task_id": task["task_id"]})
                    deadline = time.monotonic() + 30
                    while state["state"] not in {"succeeded", "cancelled", "failed"}:
                        assert time.monotonic() < deadline
                        await asyncio.sleep(0.1)
                        state = await call("get_task_status", {"task_id": task["task_id"]})
                    assert state["state"] in {"succeeded", "cancelled"}, state

                await call("open_lens", {"path": source})
                await call("update_merit_function", {"mode": "rms_spot_wizard", "operands": [
                    {"type": "EFFL", "target": original["first_order"]["effective_focal_length"], "parameters": {"3": 2}}
                ]})
                await call("set_variables", {"variables": [{"surface": original["surface_count"] - 2, "cell": "thickness"}]})
                variables = await call("get_variables")
                assert any(v["surface"] == original["surface_count"] - 2 and v["cell"] == "thickness" for v in variables["variables"])
                optimization = await run("run_local_optimization", {"cycles": "Fixed_1_Cycle"})
                assert optimization["after"]["merit_function"] <= optimization["before"]["merit_function"] * 1.001 + 1e-10
                await call("new_system")
                await call("update_system_settings", {"settings": {
                    "aperture_type": "EntrancePupilDiameter", "aperture_value": 10,
                    "fields": [{"x": 0, "y": 0}], "wavelengths": [{"wavelength_um": 0.55}], "primary_wavelength": 1,
                }})
                await call("insert_surfaces", {"at": 2, "count": 2})
                await call("update_surfaces", {"changes": [
                    {"surface": 2, "radius": 100, "thickness": 5, "material": "N-BK7"},
                    {"surface": 3, "radius": -100, "thickness": 50},
                ]})
                await call("update_surfaces", {"changes": [{"surface": 2, "surface_type": "EvenAspheric", "replace_solves": True, "parameters": {"1": 1e-7}}]})
                row = (await call("get_surfaces", {"start": 2, "count": 1}))["surfaces"][0]
                assert row["surface_type"] == "EvenAspheric"
                assert row["cells"]["parameter_1"]["value"] == pytest.approx(1e-7)
                await call("update_surfaces", {"changes": [{"surface": 3, "solves": {"radius": {"mode": "surface_pickup", "source_surface": 2, "scale": -1}}}]})
                await call("update_surfaces", {"changes": [{"surface": 3, "radius": -90}]}, "SOLVE_PROTECTED")
                await call("set_variables", {"variables": [{"surface": 3, "cell": "radius"}]}, "SOLVE_PROTECTED")
                await call("set_variables", {"variables": [{"surface": 3, "cell": "radius", "replace_solve": True}]})
                assert any(v["surface"] == 3 and v["cell"] == "radius" for v in (await call("get_variables"))["variables"])
                await call("set_variables", {"variables": [{"surface": 3, "cell": "radius", "variable": False}]})
                assert not any(v["surface"] == 3 and v["cell"] == "radius" for v in (await call("get_variables"))["variables"])
                await call("update_surfaces", {"changes": [{"surface": 3, "solves": {"radius": {"mode": "f_number", "f_number": 5}}, "replace_solves": True}]})
                assert (await call("get_surfaces", {"start": 3, "count": 1}))["surfaces"][0]["cells"]["radius"]["solve"]["type"] == "FNumber"
                await call("insert_surfaces", {"at": 4})
                await call("update_surfaces", {"changes": [{"surface": 4, "surface_type": "CoordinateBreak", "replace_solves": True, "parameters": {"1": 0.1}}]})
                assert (await call("get_surfaces", {"start": 4, "count": 1}))["surfaces"][0]["surface_type"] == "CoordinateBreak"
                await call("delete_surfaces", {"at": 4})
                await call("delete_surfaces", {"at": 4}, "INDEX_OUT_OF_RANGE")
                await call("update_merit_function", {"mode": "replace", "operands": [{"type": "EFFL", "target": 50, "parameters": {"3": 1}}]})
                await call("update_merit_function", {"mode": "append", "operands": [{"type": "TOTR", "target": 55}]})
                merit = await call("get_merit_function", {"start": 1, "count": 1})
                assert merit["next_start"] == 2
                await call("update_merit_function", {"mode": "update", "updates": [{"operand": 1, "target": 51, "parameters": {"3": 1}}]})
                assert (await call("get_merit_function", {"start": 1, "count": 1}))["operands"][0]["target"] == 51
                await call("update_merit_function", {"mode": "delete", "operand_numbers": [2]})
                assert (await call("get_merit_function"))["total"] == 1
                await call("evaluate_merit_function")
                await call("run_quick_focus", {"criterion": "SpotSizeRadial", "use_centroid": True})
                # Wait if focus is asynchronous on this installation.
                status = await call("get_status")
                if status["active_task"]:
                    deadline = time.monotonic() + 30
                    while (await call("get_status"))["active_task"]:
                        assert time.monotonic() < deadline
                        await asyncio.sleep(0.1)
                target = str(output / "constructed.zos")
                await call("save_lens_as", {"path": target})
                await call("save_lens_as", {"path": target}, "OUTPUT_EXISTS")
                await call("get_task_status", {"task_id": "missing"}, "TASK_NOT_FOUND")
                await call("disconnect")
                assert (await call("get_status"))["connected"] is False
        finally:
            with (output / "calls.json").open("w", encoding="utf-8") as stream:
                json.dump(events, stream, ensure_ascii=False, indent=2)
            print(f"Live MCP evidence: {output}", flush=True)
    asyncio.run(scenario())
