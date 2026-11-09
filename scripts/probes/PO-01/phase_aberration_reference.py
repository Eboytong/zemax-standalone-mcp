"""N3 - compare the native PhaseAberration table (401 points per pupil direction)
against polarized batch ray tracing under the same conditions.

Corrections in this revision:
  * the table is 401 points per pupil direction (the earlier 201-point assumption
    silently mis-mapped the two section tables);
  * the two section tables (弧矢/子午) are read through the real parser contract
    ``parse_phase_aberration_text`` so the column order follows the report header;
  * zero-amplitude components are recorded explicitly as ``indeterminate`` and
    counted per component instead of being dropped silently;
  * the phase threshold stays at 1e-6 degrees (not relaxed).

The probe is task-based: it issues the kind-only ``phase_aberration`` request and
a polarized ``run_batch_ray_trace`` at the same 401x2 pupil points, pages both
results through ``get_task_result``, and restores nothing but closes/disconnects
in ``finally`` with restore failures listed separately.
"""
from __future__ import annotations

import cmath
import json
import math
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_ROOT = next(p for p in _HERE.parents if (p / "pyproject.toml").is_file())
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from probe_common import (ProbeFailure, paged_result, poll_task, record_cleanup,  # noqa: E402
                          record_disconnect, write_json)
from zemax_mcp.analysis_models import RunAnalysis  # noqa: E402
from zemax_mcp.polarization_topics import parse_phase_aberration_text  # noqa: E402,F401

POINTS_PER_SECTION = 401
PHASE_ATOL_DEG = 1e-6
WAVE_ATOL = PHASE_ATOL_DEG / 360.0  # same angular gate expressed in waves
AMPLITUDE_EPS = 1e-12
DEFAULT_MODEL = "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"


def native_points(result):
    """Read the parsed phase contract into 401 points per section, order-aware."""
    rows = result.get("rows") or []
    if len(rows) != POINTS_PER_SECTION:
        raise ProbeFailure("native_points", {"point_count": len(rows), "expected": POINTS_PER_SECTION})
    order = result.get("section_order") or ["sagittal", "tangential"]
    points = []
    for fan, section in enumerate(order):
        for row in rows:
            points.append({"fan": fan, "section": section, "pupil": row["pupil"],
                           "x_phase": row[section]["x_phase"], "y_phase": row[section]["y_phase"]})
    return order, points


def batch_request(points, wavelength_number):
    """Same 401x2 pupil points as the native table, linear Jx=0/Jy=1 polarization."""
    rays = []
    for point in points:
        rays.append({"hx": 0.0, "hy": 0.0,
                     "px": point["pupil"] if point["section"] == "sagittal" else 0.0,
                     "py": point["pupil"] if point["section"] == "tangential" else 0.0,
                     "wavelength": wavelength_number})
    return {"rays": rays, "polarization": {"jx": 0.0, "jy": 1.0}}


def compare(order, points, trace_rows, threshold_deg=PHASE_ATOL_DEG, eps=AMPLITUDE_EPS):
    """Compare native phases (report units) against arg(E/E_chief) in rad/waves/deg."""
    if len(trace_rows) != len(points):
        raise ProbeFailure("compare", {"trace_rows": len(trace_rows), "points": len(points)})
    chief_index = min(range(POINTS_PER_SECTION), key=lambda i: abs(points[i]["pupil"]))
    comparisons = []
    for fan, section in enumerate(order):
        chief = trace_rows[fan * POINTS_PER_SECTION + chief_index]["electric_field"]
        for component in ("x", "y"):
            ref = complex(chief[f"e{component}_real"], chief[f"e{component}_imag"])
            values, indeterminate = [], []
            for offset in range(POINTS_PER_SECTION):
                point = points[fan * POINTS_PER_SECTION + offset]
                field = trace_rows[fan * POINTS_PER_SECTION + offset]["electric_field"]
                z = complex(field[f"e{component}_real"], field[f"e{component}_imag"])
                native = point[f"{component}_phase"]
                if abs(z) <= eps or abs(ref) <= eps:
                    indeterminate.append({"pupil": point["pupil"], "field_abs": abs(z),
                                          "chief_abs": abs(ref), "native": native,
                                          "reason": "zero_amplitude_component"})
                    continue
                delta = cmath.phase(z / ref)
                values.append({"pupil": point["pupil"], "native": native, "radians": delta,
                               "waves": delta / (2 * math.pi), "degrees": math.degrees(delta)})
            errors = {unit: (max((abs(v[unit] - v["native"]) for v in values), default=None))
                      for unit in ("radians", "waves", "degrees")}
            passes_waves = None if errors["waves"] is None else bool(errors["waves"] <= WAVE_ATOL)
            passes_degrees = None if errors["degrees"] is None else bool(errors["degrees"] <= threshold_deg)
            if errors["waves"] is None:
                verdict = None
            elif passes_waves:
                verdict = "waves"
            elif passes_degrees:
                verdict = "degrees"
            else:
                verdict = "none"
            comparisons.append({
                "section": section, "component": component,
                "compared": len(values), "indeterminate": len(indeterminate),
                "indeterminate_points": indeterminate,
                "status": "indeterminate" if not values else "compared",
                "maximum_errors": errors,
                "threshold_deg": threshold_deg,
                "wave_atol": WAVE_ATOL,
                "passes_degrees": passes_degrees,
                "passes_waves": passes_waves,
                "unit_verdict": verdict,
            })
    return comparisons


def primary_wavelength_number(settings, target_um=0.55):
    wavelengths = (settings or {}).get("wavelengths") or []
    for entry in wavelengths:
        if entry.get("number") is not None and abs(float(entry.get("wavelength_um", 0)) - target_um) < 1e-6:
            return int(entry["number"])
    return int(wavelengths[0]["number"]) if wavelengths else 1


def probe(folder, call, model=None, timeout_s=120.0, receipts=None):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    record = {"probe": "N3", "purpose": "phase unit and chief-ray reference against batch complex fields",
              "points_per_section": POINTS_PER_SECTION, "phase_atol_deg": PHASE_ATOL_DEG,
              "restore_failures": []}
    try:
        call("connect", {})
        if model:
            call("open_lens", {"path": str(model)})
        record["baseline"] = call("get_system_settings", {})
        wavelength_number = primary_wavelength_number(record["baseline"])
        record["wavelength_number"] = wavelength_number

        task = call("run_analysis", {"request": RunAnalysis(request={"kind": "phase_aberration"}).request.model_dump()})
        task = poll_task(call, task, record, timeout_s)
        record["phase_task_state"] = task.get("state")
        if task.get("poll_timed_out"):
            record["phase_poll_timed_out"] = True
            record["phase_terminated_after_cancel"] = task.get("terminated_after_cancel")
        if task.get("state") != "succeeded":
            return record
        native = paged_result(call, task["task_id"], record)
        order, points = native_points(native)
        record["section_order"] = order

        trace = call("run_batch_ray_trace", {"request": batch_request(points, wavelength_number)})
        trace = poll_task(call, trace, record, timeout_s)
        record["trace_task_state"] = trace.get("state")
        if trace.get("poll_timed_out"):
            record["trace_poll_timed_out"] = True
            record["trace_terminated_after_cancel"] = trace.get("terminated_after_cancel")
        if trace.get("state") != "succeeded":
            return record
        traced = paged_result(call, trace["task_id"], record)
        record["comparisons"] = compare(order, points, traced["rows"])
    finally:
        try:
            returned = call("disconnect", {})
            record_disconnect(record, returned, receipts)
        except Exception as exc:
            record_cleanup(record["restore_failures"], "disconnect", exc)
        write_json(folder / "probe.json", record)
    return record


if __name__ == "__main__":
    from probe_common import adapter
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    out = Path(sys.argv[1]).resolve()
    os.environ['ZEMAX_STATE_DIR'] = str(out / 'state')
    model = sys.argv[2] if len(sys.argv) > 2 else str(Path.home() / DEFAULT_MODEL)
    backend = Backend(Config(Config.from_env().install_dir, out / "native"))
    receipts = []
    record = probe(out, adapter(backend, receipts), model=model, receipts=receipts)
    print(json.dumps({"folder": str(out),
                      "phase_task_state": record.get("phase_task_state"),
                      "trace_task_state": record.get("trace_task_state"),
                      "comparisons": [{k: v for k, v in c.items() if k != "indeterminate_points"}
                                      for c in record.get("comparisons", [])],
                      "restore_failures": record["restore_failures"]}, ensure_ascii=False))
