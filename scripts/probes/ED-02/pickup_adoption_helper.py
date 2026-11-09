"""Pickup adoption helper: five readback moments x five fields, linkage, save/reload, failure.

Two layers are reported separately and never conflated:

* ``case["adoption_passed"]`` (and ``case["adoption"]``) — the admission conclusion: the final
  ``after_source_change`` state and both save/reload round-trips all read a real ``SurfacePickup``
  with the requested source/scale/offset and the linked value.  A solve adopted earlier and then
  silently reverted is a failed admission.
* ``case["complete"]`` — the full acceptance flag, computed only after shutdown.  It additionally
  requires: clean field diffs for both round-trips, a representative ray that really reached the
  image (structural rows, index/count match, finite coordinates, zero error/vignette), the failure
  recovery actually exercised and restored, a truthful close receipt (``native.closed is True``,
  ``forced is False``, empty ``native.error``, terminal tasks, no cleanup error).

Failure stages are kept apart: a request rejected by the adapter's own pre-checks (self pickup)
never writes the model and is recorded as ``precheck_no_write`` with no checkpoint; only a native
write that then fails yields ``PARTIAL_UPDATE`` with a checkpoint.  The restore diff is always
taken against the snapshot captured immediately before the failing request.  A probe that
*unexpectedly* succeeds is still rolled back to its pre-experiment checkpoint, and then reported
as ``available=False`` (no repeatable native failure) — never dressed up as a satisfied check.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

_workspace = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(_workspace), str(_workspace / "src")]

TERMINAL = {"succeeded", "failed", "cancelled"}
MOMENTS = ("immediate", "after_update_status", "after_ray_trace",
           "after_save_reload", "after_source_change")
EXTRA_MOMENTS = ("after_save_reload_post_linkage",)
PICKUP_SURFACE = 2
TASK_TIMEOUT_SECONDS = 180
PARAM_TOL = 1e-12


class TaskFailure(RuntimeError):
    def __init__(self, state, task, result):
        super().__init__("原生任务未成功：" + str(state))
        self.state = state
        self.task = task
        self.result = result


class CallFailure(RuntimeError):
    """A call that must succeed returned ``ok=false``; the raw reply is kept."""

    def __init__(self, tool, reply):
        super().__init__("工具调用失败：" + str(tool))
        self.tool = tool
        self.reply = reply


def _close(actual, expected):
    try:
        return (not isinstance(actual, bool) and math.isfinite(float(actual))
                and math.isclose(float(actual), float(expected), rel_tol=PARAM_TOL, abs_tol=PARAM_TOL))
    except (TypeError, ValueError):
        return False


def _finite_triple(position):
    if not isinstance(position, (list, tuple)) or len(position) < 3:
        return False
    for value in position[:3]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return False
    return True


def capabilities(backend, surface, name):
    """Read the cell's pickup capability without writing anything (needs a live system)."""
    row = backend._row(surface)
    cell = backend._cell(row, name)
    out = {"surface": surface, "cell": name, "supported": [str(x) for x in cell.GetAvailableSolveTypes()],
           "is_active": bool(cell.IsActive), "is_read_only": bool(cell.IsReadOnly),
           "supports_scale": False, "supports_offset": False, "solve_valid": None, "error": None}
    try:
        solve = cell.CreateSolveType(backend.native.api.Editors.SolveType.SurfacePickup)
        payload = solve._S_SurfacePickup
        out.update(supports_scale=bool(payload.SupportsScale),
                   supports_offset=bool(payload.SupportsOffset),
                   solve_valid=bool(solve.IsValid))
    except BaseException as exc:
        out["error"] = type(exc).__name__ + ": " + str(exc)
    return out


def readback(backend, surface, name):
    """Three-way readback: cell.Solve, GetSolveData().Type, and the pickup payload."""
    row = backend._row(surface)
    cell = backend._cell(row, name)
    data = cell.GetSolveData()
    out = {"surface": surface, "cell": name, "mode": str(cell.Solve), "data_type": str(data.Type),
           "value": float(cell.Value), "is_active": bool(cell.IsActive),
           "is_read_only": bool(cell.IsReadOnly), "pickup": None, "pickup_error": None}
    out["adopted"] = out["mode"] == "SurfacePickup" and out["data_type"] == "SurfacePickup"
    if out["data_type"] != "SurfacePickup":
        return out
    try:
        payload = data._S_SurfacePickup
        if payload is None:
            raise ValueError("SurfacePickup solve has no native pickup payload")
        out["pickup"] = {
            "surface": int(payload.Surface), "column": str(payload.Column),
            "scale": float(payload.ScaleFactor) if payload.SupportsScale else None,
            "scale_supported": bool(payload.SupportsScale),
            "offset": float(payload.Offset) if payload.SupportsOffset else None,
            "offset_supported": bool(payload.SupportsOffset),
            "from_current_column": bool(payload.IsPickupFromCurrentColumn)}
    except BaseException as exc:
        out["pickup_error"] = type(exc).__name__ + ": " + str(exc)
    return out


def five_fields(reading, expected):
    pickup = reading.get("pickup") or {}
    checks = {
        "mode": reading.get("mode") == "SurfacePickup",
        "data_type": reading.get("data_type") == "SurfacePickup",
        "source_surface": pickup.get("surface") == expected["source_surface"],
        "column": pickup.get("column") == expected["column"],
        "scale": (None if not pickup.get("scale_supported")
                  else _close(pickup.get("scale"), expected["scale"])),
        "offset": (None if not pickup.get("offset_supported")
                   else _close(pickup.get("offset"), expected["offset"])),
        "value": _close(reading.get("value"), expected["value"]),
    }
    return {"checks": checks, "matches": all(v for v in checks.values() if v is not None)}


def snapshot(backend, surfaces, cell):
    return {str(index): readback(backend, index, cell) for index in surfaces}


def diff(before, after):
    changes = []
    for surface, old in before.items():
        new = after.get(surface) or {}
        for field in ("mode", "data_type", "value"):
            if old.get(field) != new.get(field):
                changes.append({"surface": surface, "field": field,
                                "before": old.get(field), "after": new.get(field)})
        old_pickup = old.get("pickup") or {}
        new_pickup = new.get("pickup") or {}
        for field in ("surface", "column", "scale", "offset", "from_current_column"):
            if old_pickup.get(field) != new_pickup.get(field):
                changes.append({"surface": surface, "field": "pickup." + field,
                                "before": old_pickup.get(field), "after": new_pickup.get(field)})
    missing = sorted(set(before) - set(after))
    if missing:
        changes.append({"field": "surfaces_missing_after", "before": missing, "after": None})
    return {"clean": not changes, "changes": changes}


def classify_failure(reply, revision_before, revision_after):
    error = (reply or {}).get("error") or {}
    details = error.get("details") or {}
    code = error.get("code")
    wrote = revision_after != revision_before
    if code == "PARTIAL_UPDATE":
        return {"stage": "native_partial_failure", "code": code, "wrote_model": wrote,
                "checkpoint": details.get("checkpoint"),
                "failed_surface": details.get("failed_surface"),
                "failed_surface_state": details.get("failed_surface_state"),
                "completed_surfaces": details.get("completed_surfaces"),
                "cause": details.get("cause"), "details": details}
    return {"stage": "precheck_no_write" if not wrote else "rejected_after_write",
            "code": code, "wrote_model": wrote, "checkpoint": details.get("checkpoint"),
            "failed_surface": details.get("failed_surface"), "details": details,
            "message": error.get("message")}


def _call(backend, record, name, args=None, strict=True):
    reply = backend.dispatch(name, args or {})
    record["calls"].append({"tool": name, "arguments": args or {}, "response": reply})
    if strict and not reply.get("ok"):
        raise CallFailure(name, reply)
    return reply


def _request(backend, record, surface, name, source_surface, scale, offset, source_column=None):
    """Submit a pickup through the same tool layer production uses; keep the raw reply."""
    solve_spec = dict(mode="surface_pickup", source_surface=source_surface, scale=scale, offset=offset)
    if source_column is not None:
        solve_spec["source_column"] = source_column
    payload = dict(changes=[dict(surface=surface, replace_solves=True, solves={name: solve_spec})])
    revision_before = int(getattr(backend, "revision", 0))
    reply = backend.dispatch("update_surfaces", payload)
    revision_after = int(getattr(backend, "revision", 0))
    record["calls"].append({"tool": "update_surfaces", "arguments": payload, "response": reply})
    entry = {"arguments": payload, "reply": reply, "revision_before": revision_before,
             "revision_after": revision_after}
    if reply.get("ok"):
        entry.update(ok=True, failure=None)
    else:
        entry.update(ok=False, failure=classify_failure(reply, revision_before, revision_after))
    return entry


def inspect_rays(result, requested_count):
    """Read the real result rows; a successful task with bad rows is not success."""
    result = result if isinstance(result, dict) else {}
    rows = result.get("rows")
    reasons = []
    if not isinstance(rows, list) or not rows:
        reasons.append("rows_missing")
    rows = rows if isinstance(rows, list) else []
    if len(rows) != requested_count:
        reasons.append("rows_count_mismatch")
    indices = [row.get("index") for row in rows if isinstance(row, dict)]
    if indices != list(range(len(rows))):
        reasons.append("rows_index_mismatch")
    counts = {}
    for row in rows:
        if not isinstance(row, dict):
            reasons.append("row_not_object")
            continue
        state = row.get("state")
        counts[str(state)] = counts.get(str(state), 0) + 1
        if state != "succeeded":
            reasons.append("row_state_" + str(state))
        if row.get("error_code") != 0:
            reasons.append("row_error")
        if row.get("vignette_code") != 0:
            reasons.append("row_vignette")
        if not _finite_triple(row.get("position")):
            reasons.append("row_position_invalid")
    return {"requested": requested_count, "returned": len(rows), "states": counts,
            "all_succeeded": not reasons, "reasons": sorted(set(reasons)),
            "summary": result.get("summary")}


def _finish(backend, record, task, timeout_seconds=TASK_TIMEOUT_SECONDS):
    deadline = time.monotonic() + timeout_seconds
    states = [task.get("state")]
    while task.get("state") not in TERMINAL:
        if time.monotonic() > deadline:
            record.setdefault("task_timeouts", []).append(
                {"task_id": task.get("task_id"), "last_state": task.get("state"), "states": states[:50]})
            raise TimeoutError("任务轮询超时，最后状态：" + str(task.get("state")))
        time.sleep(0.03)
        task = (_call(backend, record, "get_task_status", dict(task_id=task["task_id"])) or {}).get("data") or {}
        states.append(task.get("state"))
    result = (_call(backend, record, "get_task_result", dict(task_id=task["task_id"])) or {}).get("data") or {}
    record.setdefault("task_states", {})[str(task.get("task_id"))] = states[:50]
    if task.get("state") != "succeeded":
        raise TaskFailure(task.get("state"), task, result)
    return result


def observe(backend, record, case, label, expected):
    reading = readback(backend, case["surface"], case["cell"])
    verdict = five_fields(reading, expected)
    case["moments"].setdefault(label, {})["target"] = reading
    case["moments"][label]["fields"] = verdict
    record.setdefault("observations", []).append(
        {"moment": label, "cell": case["cell"], "adopted": reading["adopted"],
         "mode": reading["mode"], "data_type": reading["data_type"], "value": reading["value"],
         "matches": verdict["matches"]})
    return reading


def _restore(backend, record, case, checkpoint, before):
    if not checkpoint:
        return {"clean": False, "error": "checkpoint_missing", "changes": []}
    try:
        _call(backend, record, "open_lens", dict(path=str(checkpoint)))
    except CallFailure as exc:
        return {"clean": False, "error": "open_lens_failed", "reply": exc.reply, "changes": []}
    return diff(before, snapshot(backend, case["watch_surfaces"], case["cell"]))


def _save_reload(backend, record, case, folder, label, expected):
    path = folder / ("reload-" + label + ".zos")
    before = snapshot(backend, case["watch_surfaces"], case["cell"])
    _call(backend, record, "save_lens_as", dict(path=str(path)))
    _call(backend, record, "open_lens", dict(path=str(path)))
    observe(backend, record, case, label, expected)
    changes = diff(before, snapshot(backend, case["watch_surfaces"], case["cell"]))
    case["moments"][label]["diff"] = changes
    case["save_reload_diff" if label == "after_save_reload" else "post_linkage_reload_diff"] = changes


def _failure_restore(backend, record, case):
    """Pre-check rejection (no write) plus a native partial failure with correct rollback.

    * pre-check: self pickup — rejected before any write; no checkpoint, never PARTIAL_UPDATE.
    * native partial: the main request if the native side rejected it (historical rejection,
      checkpoint = pre-request snapshot); otherwise a constructed write-then-fail probe on an
      alternate column.  A probe that unexpectedly succeeds is still rolled back to its
      pre-experiment checkpoint (``temporary_change_restored``) and reported ``available=False``.
    """
    source = case["expected"]["source_surface"]
    pre = _request(backend, record, source, case["cell"], source,
                   case["expected"]["scale"], case["expected"]["offset"])
    failure = {"precheck": pre.get("failure")}
    request_failure = (case.get("request") or {}).get("failure")
    if request_failure and request_failure.get("stage") == "native_partial_failure":
        checkpoint = request_failure.get("checkpoint")
        restore = _restore(backend, record, case, checkpoint, case["before"])
        failure["native_partial"] = {
            "source": "main_request", "available": True, "failure": request_failure,
            "original_error": request_failure, "checkpoint": checkpoint,
            "restore": restore,
            "restore_error": restore.get("error"),
            "temporary_change_restored": bool(restore.get("clean"))}
        case["failure"] = failure
        return
    before = snapshot(backend, case["watch_surfaces"], case["cell"])
    alt_column = "SemiDiameter" if case["expected"]["column"] == "ChipZone" else "ChipZone"
    probe = _request(backend, record, PICKUP_SURFACE, case["cell"], source,
                     case["expected"]["scale"], case["expected"]["offset"], source_column=alt_column)
    failure_probe = probe.get("failure") or {}
    checkpoint = (failure_probe.get("checkpoint") if failure_probe else None) \
        or getattr(backend, "last_checkpoint", None)
    restore = _restore(backend, record, case, checkpoint, before)
    available = failure_probe.get("stage") == "native_partial_failure"
    entry = {"source": "constructed_probe", "available": available,
             "failure": failure_probe or None, "original_error": failure_probe or None,
             "checkpoint": checkpoint, "restore": restore,
             "restore_error": restore.get("error"),
             "temporary_change_restored": bool(restore.get("clean"))}
    if not available:
        entry["reason"] = "no_repeatable_native_failure"
    failure["native_partial"] = entry
    case["failure"] = failure


def lifecycle(backend, record, folder):
    """Strict close judgement from the real receipt and task/cleanup state."""
    state_dir = Path(os.environ.get("ZEMAX_STATE_DIR") or (folder / "state"))
    receipt = state_dir / "close_receipt.json"
    out = {"receipt_path": str(receipt), "exists": receipt.is_file(), "content": None,
           "error": None, "native_closed": None, "forced": None, "native_error": "<missing>",
           "active_task_after_shutdown": bool(getattr(backend, "active", None)),
           "task_states": record.get("task_states", {}),
           "all_tasks_terminal": all(
               state in TERMINAL for states in record.get("task_states", {}).values()
               for state in states[-1:]),
           "closed_confirmed": False, "reason": []}
    if out["exists"]:
        try:
            out["content"] = json.loads(receipt.read_text(encoding="utf-8"))
        except BaseException as exc:
            out["error"] = type(exc).__name__ + ": " + str(exc)
    content = out["content"] if isinstance(out["content"], dict) else {}
    native = content.get("native") if isinstance(content.get("native"), dict) else {}
    if "closed" in native:
        out["native_closed"] = native["closed"]
    if "forced" in content:
        out["forced"] = content["forced"]
    if "error" in native:
        out["native_error"] = native["error"]
    reasons = out["reason"]
    if not out["exists"]:
        reasons.append("close_receipt_missing")
    else:
        if out["error"]:
            reasons.append("close_receipt_unreadable")
        if out["native_closed"] is not True:
            reasons.append("native_closed_not_true")
        if out["forced"] is not False:
            reasons.append("forced_not_false")
        if out["native_error"] not in (None, "", {}, []):
            reasons.append("native_error")
        if content.get("cancel_error"):
            reasons.append("cancel_error")
        if content.get("active_cancelled") is True and out["forced"] is True:
            reasons.append("active_cancelled_forced")
    if out["active_task_after_shutdown"]:
        reasons.append("native_task_still_active")
    if record.get("task_timeouts"):
        reasons.append("task_poll_timeout")
    if not out["all_tasks_terminal"]:
        reasons.append("task_not_terminal")
    out["closed_confirmed"] = not reasons
    return out


def evaluate_adoption(case):
    """Admission/linkage conclusion from the FINAL states only."""
    expected = case["expected"]
    linked = dict(expected)
    if case.get("linkage") and "expected_value" in case["linkage"]:
        linked["value"] = case["linkage"]["expected_value"]
    reasons = []

    def check(reading, label, expectation):
        if not reading:
            reasons.append(label + ":missing")
            return
        if not reading.get("adopted"):
            reasons.append(label + ":not_adopted(" + str(reading.get("mode")) + ")")
        for field, passed in five_fields(reading, expectation)["checks"].items():
            if passed is False:
                reasons.append(label + ":" + field + "_mismatch")

    check((case["moments"].get("after_source_change") or {}).get("target"),
          "after_source_change", linked)
    check((case["moments"].get("after_save_reload") or {}).get("target"),
          "after_save_reload", expected)
    check((case["moments"].get("after_save_reload_post_linkage") or {}).get("target"),
          "after_save_reload_post_linkage", linked)
    if not case.get("linkage", {}).get("passed"):
        reasons.append("linkage_failed")
    case["adopted_at"] = [label for label, moment in case["moments"].items()
                          if (moment.get("target") or {}).get("adopted")]
    case["adoption"] = {"confirmed": not reasons, "reasons": reasons}
    case["adoption_passed"] = not reasons
    return case["adoption_passed"]


def finalize(record, case):
    """Full acceptance flag, only after shutdown.  Every applicable check must pass."""
    reasons = list((case.get("adoption") or {}).get("reasons") or [])
    if not (case.get("adoption") or {}).get("confirmed"):
        reasons.append("adoption_unconfirmed")
    for key, label in (("save_reload_diff", "after_save_reload"),
                       ("post_linkage_reload_diff", "after_save_reload_post_linkage")):
        entry = case.get(key)
        if not entry:
            reasons.append(label + ":diff_missing")
        elif not entry.get("clean"):
            reasons.append(label + ":diff_not_clean")
    trace = case.get("ray_trace") or {}
    if not trace.get("all_succeeded"):
        reasons.append("ray_not_all_succeeded")
    native_partial = (case.get("failure") or {}).get("native_partial") or {}
    if "available" not in native_partial:
        reasons.append("failure_stage_missing")
    elif not native_partial.get("available"):
        reasons.append("failure_recovery_not_exercised")
    elif not (native_partial.get("restore") or {}).get("clean"):
        reasons.append("failure_restore_not_clean")
    precheck = (case.get("failure") or {}).get("precheck") or {}
    if precheck.get("stage") != "precheck_no_write":
        reasons.append("precheck_not_no_write")
    lifecycle_out = case.get("lifecycle") or {}
    if not lifecycle_out.get("closed_confirmed"):
        reasons.append("close_not_confirmed")
        reasons.extend("close:" + item for item in (lifecycle_out.get("reason") or []))
    if record.get("cleanup_error"):
        reasons.append("cleanup_error")
    if record.get("error"):
        reasons.append("run_error")
    case["complete"] = not reasons
    case["incomplete_reasons"] = reasons
    return case["complete"]


def run_case(backend, spec, folder, timeout_seconds=TASK_TIMEOUT_SECONDS):
    """Run one cell through the five moments, linkage, persistence and failure/restore."""
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)  # the single owner of directory creation
    os.environ.setdefault("ZEMAX_STATE_DIR", str(folder / "state"))
    record = {"probe": "pickup adoption helper", "cell": spec["cell"], "item": spec["item"],
              "moments": list(MOMENTS) + list(EXTRA_MOMENTS), "calls": [],
              "conclusion": "recorded, not asserted"}
    case = {"cell": spec["cell"], "surface": PICKUP_SURFACE, "capabilities": None,
            "expected": None, "moments": {}, "adoption": None, "adoption_passed": False,
            "watch_surfaces": [spec.get("source_surface", 1), PICKUP_SURFACE]}
    record["case"] = case

    def save():
        (folder / "anchors.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    try:
        _call(backend, record, "connect")
        _call(backend, record, "new_system")
        _call(backend, record, "insert_surfaces", dict(at=1))
        _call(backend, record, "update_system_settings", dict(
            aperture_value=10, primary_wavelength=1,
            wavelengths=[dict(wavelength_um=0.5875618)], fields=[dict(x=0, y=0)]))
        _call(backend, record, "update_surfaces", dict(changes=[dict(
            surface=1, radius=50, thickness=50, material="N-BK7",
            semi_diameter=(min(spec["source"], spec["target"]) * .8
                           if spec["cell"] == "mechanical_semi_diameter" else 8),
            is_stop=True, replace_solves=True)]))
        layout = (_call(backend, record, "get_surfaces", dict(start=0, count=1)) or {}).get("data") or {}
        total = int(layout.get("total", 0))
        image = total - 1
        record["surface_layout"] = dict(total=total, image_surface=image, pickup_surface=PICKUP_SURFACE,
                                        target_reaches_pickup=image >= PICKUP_SURFACE)
        if image < PICKUP_SURFACE:
            raise RuntimeError("追迹目标面未覆盖拾取单元格所在的 surface 2。")

        caps = capabilities(backend, PICKUP_SURFACE, spec["cell"])
        scale = spec.get("scale") if caps["supports_scale"] else 1.0
        offset = spec.get("offset") if caps["supports_offset"] else 0.0
        case["capabilities"] = caps
        case["expected"] = {"source_surface": spec.get("source_surface", 1), "scale": scale,
                            "offset": offset, "column": spec["column"],
                            "value": spec["source"] * scale + offset}

        _call(backend, record, "update_surfaces", dict(changes=[
            dict(surface=1, **{spec["cell"]: spec["source"]}, replace_solves=True),
            dict(surface=2, **{spec["cell"]: spec["target"]}, replace_solves=True)]))
        case["before"] = snapshot(backend, case["watch_surfaces"], spec["cell"])

        entry = _request(backend, record, PICKUP_SURFACE, spec["cell"],
                         case["expected"]["source_surface"], scale, offset)
        case["request"] = entry
        observe(backend, record, case, "immediate", case["expected"])

        _call(backend, record, "update_system_settings", dict(aperture_value=10))
        record["update_status_text"] = str(backend.system.UpdateStatus())
        observe(backend, record, case, "after_update_status", case["expected"])

        rays = [dict(hx=0, hy=0, px=0, py=0, wavelength=1)]
        trace_task = (_call(backend, record, "run_batch_ray_trace", dict(
            input_mode="Normalized", start_surface=0, target_surface=image, rays=rays)) or {}).get("data") or {}
        result = _finish(backend, record, trace_task, timeout_seconds)
        case["ray_trace"] = dict(target_surface=image, reaches_pickup=image >= PICKUP_SURFACE,
                                 **inspect_rays(result, len(rays)))
        observe(backend, record, case, "after_ray_trace", case["expected"])

        _save_reload(backend, record, case, folder, "after_save_reload", case["expected"])

        source_after = spec["source_after"]
        _call(backend, record, "update_surfaces", dict(changes=[
            dict(surface=1, **{spec["cell"]: source_after}, replace_solves=True)]))
        record["update_status_text"] = str(backend.system.UpdateStatus())
        linked = dict(case["expected"])
        linked["value"] = source_after * scale + offset
        case["linkage"] = {"source_before": spec["source"], "source_after": source_after,
                           "expected_value": linked["value"],
                           "tolerance": {"rel": PARAM_TOL, "abs": PARAM_TOL}}
        reading = observe(backend, record, case, "after_source_change", linked)
        case["linkage"].update(actual_value=reading["value"],
                               passed=_close(reading["value"], linked["value"])
                               and reading.get("adopted") is True)

        _save_reload(backend, record, case, folder, "after_save_reload_post_linkage", linked)
        evaluate_adoption(case)
        _failure_restore(backend, record, case)
    except BaseException as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        if isinstance(exc, CallFailure):
            record["error"]["reply"] = exc.reply
        if isinstance(exc, TaskFailure):
            record["error"].update(task_state=exc.state, task=exc.task, task_result=exc.result)
    finally:
        try:
            backend.shutdown()
        except BaseException as exc:
            record["cleanup_error"] = {"type": type(exc).__name__, "message": str(exc)}
        case["lifecycle"] = lifecycle(backend, record, folder)
        if case.get("expected") and case.get("adoption") is None:
            evaluate_adoption(case)
        finalize(record, case)
        save()
    return record


DEFAULT_SPECS = {
    "chip_zone": dict(item="ED-02.SurfacePickup.ChipZone", cell="chip_zone", column="ChipZone",
                      source=0.5, target=0.2, source_after=0.7, scale=1.25, offset=0.05,
                      source_surface=1),
    "mechanical_semi_diameter": dict(item="ED-02.SurfacePickup.MechanicalSemiDiameter",
                                     cell="mechanical_semi_diameter", column="MechanicalSemiDiameter",
                                     source=5.5, target=5.2, source_after=6.0, scale=1.25, offset=0.05,
                                     source_surface=1),
}


def _summary(record):
    case = record.get("case", {})
    return {"cell": record.get("cell"),
            "adoption_passed": case.get("adoption_passed"),
            "complete": case.get("complete"), "adopted_at": case.get("adopted_at"),
            "reasons": case.get("incomplete_reasons"),
            "lifecycle_closed": (case.get("lifecycle") or {}).get("closed_confirmed"),
            "error": record.get("error")}


def main(argv=None):
    parser = argparse.ArgumentParser(description="pickup adoption helper")
    parser.add_argument("--cell", required=True, choices=sorted(DEFAULT_SPECS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=TASK_TIMEOUT_SECONDS)
    args = parser.parse_args(argv)
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    folder = Path(args.out).resolve()
    os.environ["ZEMAX_STATE_DIR"] = str(folder / "state")
    os.environ["ZEMAX_OUTPUT_DIR"] = str(folder)
    backend = Backend(Config(Config.from_env().install_dir, folder / "native"))
    record = run_case(backend, DEFAULT_SPECS[args.cell], folder, args.timeout)
    print(json.dumps(_summary(record), ensure_ascii=False))
    return record


if __name__ == "__main__":
    main()
