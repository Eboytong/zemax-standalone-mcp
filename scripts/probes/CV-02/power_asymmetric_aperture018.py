"""E3 one-sided clipping with an unchanged pupil/field mapping (single variable: aperture decenter).

The normalized coordinates (hx,hy,px,py) are kept fixed across cases; only a decentered
circular surface aperture changes which rays survive.  Field vignetting factors are NOT
used, because VCX/VCY would remap those coordinates to different real rays and a value
change could not be attributed to clipping.  Every case re-traces the same coordinates and
records the actual position/direction so the mapping invariance is checkable.

Both a change and the absence of a change are recorded as evidence only: neither proves the
internal differential-ring algorithm on its own.

Contract details honoured explicitly:
  * normalized rays require input_mode="Normalized"; "Direct" would demand DirectRay fields
    and `BatchRays` rejects hx/hy/px/py in that mode (`models.py:557`);
  * the aperture readback lives at `surface["properties"]["aperture"]`, not `surface["aperture"]`
    (`backend.py:837`, `modeling.py:255`);
  * power and EFL deltas are computed independently so a missing EFL never breaks the sweep.
"""
import sys
from pathlib import Path

_workspace = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(_workspace), str(_workspace / "src")]

import json
import math
import os
import time

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean

WAVELENGTH = .5875618
FIELD = dict(x=0, y=0)
POINTS = [(-1.0, 0.0), (-.6, 0.0), (-.2, 0.0), (0.0, 0.0), (.2, 0.0), (.6, 0.0), (1.0, 0.0)]
MAPPING_TOLERANCE = 1e-12
CHANGE_ATOL, CHANGE_RTOL = 2e-4, 2e-5  # Existing power-map numerical reference gate
TASK_TIMEOUT_SECONDS = 180
CASES = [
    dict(id="base", aperture=dict(type="CircularAperture", maximum_radius=8, x_decenter=0), note="oversized circular aperture; all controlled pupil points pass"),
    dict(id="sym_r4", aperture=dict(type="CircularAperture", maximum_radius=4, x_decenter=0), note="symmetric clip"),
    dict(id="dec_1p5", aperture=dict(type="CircularAperture", maximum_radius=4, x_decenter=1.5), note="clip negative side only"),
    dict(id="dec_3p0", aperture=dict(type="CircularAperture", maximum_radius=4, x_decenter=3.0), note="clip negative side further"),
]


class TaskFailure(RuntimeError):
    def __init__(self, state, task, result):
        super().__init__("原生任务未成功：" + str(state))
        self.state = state
        self.task = task
        self.result = result


def aperture_of(surface):
    """Aperture readback lives under properties (backend._surface_data)."""
    return surface["properties"]["aperture"]


def delta(base, row, key):
    """Difference only when both sides produced a finite raw value; state kept otherwise."""
    a, b = base[key], row[key]
    values = (a.get("raw_value"), b.get("raw_value"))
    if any(v is None or not math.isfinite(v) for v in values):
        return dict(available=False, base_state=a.get("state"), case_state=b.get("state"),
                    base_raw=a.get("raw_value"), case_raw=b.get("raw_value"), delta=None)
    return dict(available=True, base_state=a.get("state"), case_state=b.get("state"),
                base_raw=a["raw_value"], case_raw=b["raw_value"],
                delta=b["raw_value"] - a["raw_value"])


def coordinate_delta(base, row):
    """Mapping difference, or an explicit non-evaluable record when a trace lacks coordinates."""
    sides = dict(
        base=dict(error_code=base["error_code"], vignette_code=base["vignette_code"],
                  position=base["position"], direction=base["direction"]),
        case=dict(error_code=row["error_code"], vignette_code=row["vignette_code"],
                  position=row["position"], direction=row["direction"]))
    missing = [name for name, side in sides.items()
               if side["position"] is None or side["direction"] is None]
    if missing:
        return dict(px=row["px"], py=row["py"], evaluable=False, reason="trace_coordinates_missing",
                    missing=missing, max_abs_diff=None, unchanged=None, **sides)
    diff = max(abs(a - b) for a, b in zip(base["position"] + base["direction"],
                                          row["position"] + row["direction"]))
    return dict(px=row["px"], py=row["py"], evaluable=True, reason=None, missing=[], max_abs_diff=diff,
                unchanged=diff <= MAPPING_TOLERANCE, **sides)


def change_diagnostics(deltas):
    """Keep exact bit changes distinct from changes above the existing reference gate."""
    result = dict(atol=CHANGE_ATOL, rtol=CHANGE_RTOL)
    for key in ('power', 'efl'):
        available = [d[key] for d in deltas if d[key]['available']]
        result[key] = dict(
            comparable_count=len(available),
            max_abs_delta=max((abs(d['delta']) for d in available), default=None),
            changed_above_reference_tolerance=any(
                abs(d['delta']) > CHANGE_ATOL + CHANGE_RTOL*abs(d['base_raw'])
                for d in available))
    return result


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ["ZEMAX_STATE_DIR"] = str(folder / "state")
    os.environ["ZEMAX_OUTPUT_DIR"] = str(folder)
    backend = Backend(Config(Config.from_env().install_dir, folder / "native"))
    record = dict(
        item_ids=["CV-02.PowerFieldMapSettings", "CV-02.PowerPupilMapSettings"],
        probe="E3 one-sided clipping with unchanged pupil mapping",
        single_variable="surface aperture decenter",
        evidence_only=True,
        conclusion="not asserted; change and no-change are both recorded",
        why_not_vignetting_factors=("VCX/VCY remap the normalized pupil to different real rays; "
                                    "an aperture only clips, so the mapping stays fixed"),
        mapping_tolerance=MAPPING_TOLERANCE, points=POINTS, writes=[], cases=[], calls=[], closed=False)

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
        for artifact in paged.get("artifacts") or []:
            if artifact.get("kind") == "json" and Path(artifact["path"]).stem == task["task_id"]:
                return json.loads(Path(artifact["path"]).read_text(encoding="utf-8")), "artifact_json"
        return paged, "paged_inline"

    def operand(code, args):
        try:
            value = float(backend.system.MFE.GetOperandValue(code, *args))
        except BaseException as exc:
            return dict(raw_value=None, state="native_query_failed",
                        error=dict(type=type(exc).__name__, message=str(exc)))
        if value != value or value in (float("inf"), float("-inf")):
            return dict(raw_value=None, state="non_finite")
        return dict(raw_value=value, state="native_zero" if value == 0 else "finite_nonzero")

    def measure():
        task, paged = finish(call("run_batch_ray_trace", dict(
            input_mode="Normalized", start_surface=0, target_surface=1,
            rays=[dict(hx=0, hy=0, px=px, py=py, wavelength=1) for px, py in POINTS])))
        result, source = full_result(task, paged)
        trace_rows = result["rows"]
        power_code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, "POWP")
        rows = []
        if len(trace_rows) != len(POINTS):
            record["trace_row_count_mismatch"] = dict(expected=len(POINTS), actual=len(trace_rows))
        for index, (px, py) in enumerate(POINTS):
            ray = trace_rows[index] if index < len(trace_rows) else dict(
                error_code=None, vignette_code=None, position=None, direction=None, surface_normal=None)
            base = [1, 1, 0.0, 0.0, px, py]
            rows.append(dict(
                px=px, py=py, trace_result_source=source, trace_row_present=index < len(trace_rows),
                error_code=ray["error_code"], vignette_code=ray["vignette_code"],
                position=ray["position"], direction=ray["direction"], surface_normal=ray["surface_normal"],
                power_args=base + [0.0, 0.0], efl_args=base + [9.0, 0.0],
                power=operand(power_code, base + [0.0, 0.0]),
                efl=operand(power_code, base + [9.0, 0.0])))
        return rows

    try:
        call("connect")
        call("new_system")
        call("insert_surfaces", dict(at=1))
        call("update_system_settings", dict(settings=dict(
            aperture_value=10, primary_wavelength=1,
            wavelengths=[dict(wavelength_um=WAVELENGTH)],
            fields=[dict(x=FIELD["x"], y=FIELD["y"])])))
        call("update_surfaces", dict(changes=[dict(
            surface=1, radius=50, thickness=50, material="N-BK7",
            semi_diameter=8, is_stop=True, replace_solves=True)]))
        baseline_rows = None
        for case in CASES:
            record["writes"].append(dict(kind="aperture", spec=case["aperture"]))
            change = dict(surface=1)
            change["aperture"] = case["aperture"] if case["aperture"] is not None else dict(type="None")
            call("update_surfaces", dict(changes=[change]))
            surface = call("get_surfaces", dict(start=1, count=1))["surfaces"][0]
            rows = measure()
            if baseline_rows is None:
                baseline_rows = rows
                mapping = [coordinate_delta(row, row) for row in rows]
            else:
                mapping = [coordinate_delta(base, row) for base, row in zip(baseline_rows, rows)]
            record["cases"].append(dict(
                id=case["id"], note=case["note"], aperture_request=case["aperture"],
                aperture_readback=aperture_of(surface),
                mapping=mapping,
                mapping_evaluable=all(m["evaluable"] for m in mapping),
                mapping_unchanged=all(m["unchanged"] is True for m in mapping),
                rows=[dict(px=r["px"], py=r["py"], error_code=r["error_code"], vignette_code=r["vignette_code"],
                           power=r["power"], efl=r["efl"], power_args=r["power_args"], efl_args=r["efl_args"],
                           position=r["position"], direction=r["direction"]) for r in rows]))
            save()
        baseline = record["cases"][0]["rows"]
        for case in record["cases"][1:]:
            deltas = []
            for base, row in zip(baseline, case["rows"]):
                deltas.append(dict(px=row["px"],
                                   power=delta(base, row, "power"),
                                   efl=delta(base, row, "efl"),
                                   vignette_changed=row["vignette_code"] != base["vignette_code"]))
            case["versus_baseline"] = deltas
            case["value_changed"] = any(d["power"]["available"] and abs(d["power"]["delta"]) > 0
                                        for d in deltas)
            case["change_diagnostics"] = change_diagnostics(deltas)
            save()
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
    print(json.dumps(dict(cases=[c["id"] for c in record["cases"]],
                          mapping_evaluable={c["id"]: c["mapping_evaluable"] for c in record["cases"]},
                          mapping_unchanged={c["id"]: c["mapping_unchanged"] for c in record["cases"]},
                          value_changed={c["id"]: c.get("value_changed") for c in record["cases"][1:]},
                          closed=record["closed"], cleanup_error=record.get("cleanup_error"),
                          error=record.get("error")), ensure_ascii=False))
    return record


if __name__ == "__main__":
    run(sys.argv[1])
