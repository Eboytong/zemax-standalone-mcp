"""E2 radius-magnitude sweep for the zero-EFL question (single variable: radius).

Records native Power/EFL against the analytic reference EFL=n*R/(n-1) at four radii.
This only bounds where a zero could appear; it does not define the zero seen on a
plane surface, and it cannot exclude a threshold below the smallest tested power.
No gate is asserted here: values are recorded for later judgement.

Two request-contract requirements are honoured explicitly:
  * the field list keeps field 1 on axis as the pupil/centre reference but adds an
    off-axis field with both X and Y non-zero, because `run_power_map` rejects a field
    grid whose normalisation scale is zero (`power_maps.py:71`);
  * task results are read from the full JSON artifact (as `Evidence.finish` does), with
    an explicit grid page as the fallback, because `get_task_result` strips
    `grids[].values` by default (`backend.py:1617`).
"""
import sys
from pathlib import Path

_workspace = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(_workspace), str(_workspace / "src")]

import json
import os
import time

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean

N_GLASS = 1.5168000345005883  # N-BK7 at 0.5875618 um (native material tool, power-maps.md:11)
WAVELENGTH = .5875618
RADII = [50, 1e3, 1e6, 1e9]
FIELDS = [dict(x=0, y=0), dict(x=2, y=2)]  # field 1 on axis; field 2 gives non-zero X and Y scale
GRID_POINTS = 3
CENTER = 1  # centre index of a 3x3 grid
ATOL, RTOL = 2e-4, 2e-5
TASK_TIMEOUT_SECONDS = 180


class TaskFailure(RuntimeError):
    def __init__(self, state, task, result):
        super().__init__("原生任务未成功：" + str(state))
        self.state = state
        self.task = task
        self.result = result


def gate(actual, expected):
    return dict(actual=actual, expected=expected, atol=ATOL, rtol=RTOL,
                error=None if actual is None else actual - expected,
                passed=actual is not None and abs(actual - expected) <= ATOL + RTOL * abs(expected))


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ["ZEMAX_STATE_DIR"] = str(folder / "state")
    os.environ["ZEMAX_OUTPUT_DIR"] = str(folder)
    backend = Backend(Config(Config.from_env().install_dir, folder / "native"))
    record = dict(
        item_ids=["CV-02.PowerFieldMapSettings", "CV-02.PowerPupilMapSettings"],
        probe="E2 radius-magnitude sweep", single_variable="surface 1 radius",
        evidence_only=True,
        conclusion="not asserted; bounds the zero/threshold location only",
        index_reference=dict(value=N_GLASS, source="native material tool at 0.5875618 um",
                             formula="EFL = n*R/(n-1); Power = 1000/EFL[mm]"),
        tolerance=dict(atol=ATOL, rtol=RTOL, source="test_power_map_value_states_live.py:47-48"),
        wavelengths=[WAVELENGTH], fields=FIELDS, radii=RADII,
        writes=[], cases=[], calls=[], closed=False)

    def save():
        (folder / "anchors.json").write_text(json.dumps(clean(record), ensure_ascii=False, indent=2),
                                             encoding="utf-8")

    def call(name, args=None):
        body = args or {}
        # Direct Backend dispatch uses the flat SystemPatch body.
        if name == "update_system_settings" and "settings" in body:
            body = body["settings"]
        response = backend.dispatch(name, body)
        record["calls"].append(dict(tool=name, arguments=args, backend_arguments=body, response=response))
        save()
        assert response["ok"], response
        return response["data"]

    def finish(task, timeout_seconds=TASK_TIMEOUT_SECONDS):
        deadline = time.monotonic() + timeout_seconds
        while task["state"] not in ("succeeded", "failed", "cancelled"):
            if time.monotonic() > deadline:
                raise TimeoutError("任务轮询超时，最后状态：" + str(task["state"]))
            time.sleep(.03)
            task = call("get_task_status", dict(task_id=task["task_id"]))
        result = call("get_task_result", dict(task_id=task["task_id"]))
        if task["state"] != "succeeded":
            raise TaskFailure(task["state"], task, result)
        return task, result

    def full_result(task, paged):
        """Prefer the task's own JSON artifact; default paging drops grids[].values."""
        for artifact in paged.get("artifacts") or []:
            if artifact.get("kind") == "json" and Path(artifact["path"]).stem == task["task_id"]:
                return json.loads(Path(artifact["path"]).read_text(encoding="utf-8")), "artifact_json"
        return paged, "paged_inline"

    def centre(task, result, source):
        """Centre value and row, from the artifact or from an explicit grid page."""
        rows = result["rows"]
        row = next(r for r in rows if r["grid_x"] == CENTER and r["grid_y"] == CENTER)
        if source == "artifact_json":
            grid = result["grids"][0]
            return dict(source=source, value=grid["values"][CENTER][CENTER], row=row,
                        native_ring_validity=grid.get("native_ring_validity"),
                        valid_mask_scope=grid.get("valid_mask_scope"))
        page = call("get_task_result", dict(task_id=task["task_id"], grid=0,
                                           x_start=CENTER, y_start=CENTER, width=1, height=1))
        grid = page["grid"]  # paged form uses the singular key
        return dict(source=source + "+grid_page", value=grid["values"][0][0], row=row,
                    native_ring_validity=grid.get("native_ring_validity"),
                    valid_mask_scope=grid.get("valid_mask_scope"))

    def analyse(request):
        task, paged = finish(call("run_analysis", dict(request=request)))
        result, source = full_result(task, paged)
        picked = centre(task, result, source)
        row = picked["row"]
        return dict(result_source=picked["source"], raw_value=row["raw_value"],
                    value=row["value"], state=row["state"],
                    native_query_status=row["native_query_status"],
                    zero_interpretation=row.get("zero_interpretation"),
                    native_ring_validity=row.get("native_ring_validity"),
                    grid_center=picked["value"], grid_center_matches_row=picked["value"] == row["value"],
                    valid_mask_scope=picked["valid_mask_scope"])

    try:
        call("connect")
        call("new_system")
        call("insert_surfaces", dict(at=1))
        call("update_system_settings", dict(settings=dict(
            aperture_value=10, primary_wavelength=1,
            wavelengths=[dict(wavelength_um=WAVELENGTH)],
            fields=FIELDS)))
        settings = call("get_system_settings")
        record["settings_readback"] = dict(
            fields=settings["fields"], field_type=settings["field_type"],
            field_normalization=settings["field_normalization"],
            fields_match_request=settings["fields"] == FIELDS)
        for radius in RADII:
            record["writes"].append(dict(kind="surface", radius=radius))
            call("update_surfaces", dict(changes=[dict(
                surface=1, radius=radius, thickness=50, material="N-BK7",
                semi_diameter=8, is_stop=True, replace_solves=True)]))
            surface = call("get_surfaces", dict(start=1, count=1))["surfaces"][0]
            efl_ref = N_GLASS * radius / (N_GLASS - 1)
            power_ref = 1000 / efl_ref
            case = dict(radius_mm=radius, radius_readback=surface["cells"]["radius"]["value"],
                        analytic_efl_mm=efl_ref, analytic_power_d=power_ref)
            for name, request in (
                    ("field_power", dict(kind="power_field_map", surface=1, quantity="Power",
                                         x_points=GRID_POINTS, y_points=GRID_POINTS,
                                         x_field_width=2, y_field_width=2)),
                    ("field_efl", dict(kind="power_field_map", surface=1, quantity="EFL",
                                       x_points=GRID_POINTS, y_points=GRID_POINTS,
                                       x_field_width=2, y_field_width=2)),
                    ("pupil_power", dict(kind="power_pupil_map", surface=1, quantity="Power",
                                         x_points=GRID_POINTS, y_points=GRID_POINTS)),
                    ("pupil_efl", dict(kind="power_pupil_map", surface=1, quantity="EFL",
                                       x_points=GRID_POINTS, y_points=GRID_POINTS))):
                case[name] = analyse(request)
                save()
            case["gate_power"] = gate(case["pupil_power"]["raw_value"], power_ref)
            case["gate_efl"] = gate(case["pupil_efl"]["raw_value"], efl_ref)
            case["zero_observed"] = (case["pupil_power"]["raw_value"] == 0
                                     or case["pupil_efl"]["raw_value"] == 0)
            record["cases"].append(case)
            save()
        record["summary"] = dict(
            zero_radii=[c["radius_mm"] for c in record["cases"] if c["zero_observed"]],
            smallest_power_tested_d=min(c["analytic_power_d"] for c in record["cases"]),
            note="a finite result here bounds the tested magnitudes only; no threshold below is excluded")
        call("disconnect")
        record["closed"] = True
    except BaseException as exc:
        entry = dict(type=type(exc).__name__, message=str(exc))
        if isinstance(exc, TaskFailure):
            entry.update(task_state=exc.state, task=exc.task, task_result=exc.result)
        record["error"] = entry
        try:
            save()
        except BaseException as write_error:
            print("无法写入 anchors.json：" + str(write_error), file=sys.stderr)
        raise
    finally:
        try:
            backend.shutdown()
        except BaseException as exc:
            record["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc))
        record["active_task_after_shutdown"] = bool(getattr(backend, "active", None))
        receipt = Path(os.environ["ZEMAX_STATE_DIR"]) / "close_receipt.json"
        record["close_receipt"] = dict(path=str(receipt), exists=receipt.is_file(), content=None, error=None)
        try:
            if receipt.is_file():
                record["close_receipt"]["content"] = json.loads(receipt.read_text(encoding="utf-8"))
        except BaseException as exc:
            record["close_receipt"]["error"] = type(exc).__name__ + ": " + str(exc)
        try:
            save()
        except BaseException as write_error:
            print("无法写入 anchors.json：" + str(write_error), file=sys.stderr)
    print(json.dumps(dict(cases=len(record["cases"]), closed=record["closed"],
                          zero_radii=record.get("summary", {}).get("zero_radii"),
                          cleanup_error=record.get("cleanup_error"), error=record.get("error")),
                     ensure_ascii=False))
    return record


if __name__ == "__main__":
    run(sys.argv[1])
