"""N2 - system polarization modify / read-back / restore, then compare the
input headers the four topic analyses report.

Bounded probe: it saves the baseline system settings, applies one documented
polarization patch (Jx=1, Jy=0, X phase 0, Y phase 90 deg) through
``update_system_settings``, runs each kind-only topic request, compares the
parsed ``input_header.jones`` against the patch, then restores the baseline and
verifies the readback.

If a poll times out and the task cannot be confirmed terminal, no further
analysis is started and the restore is skipped: the system must never be
mutated while a native task may still be running.  Cleanup failures are listed
separately, and the disconnect result is recorded from the receipt fields.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_ROOT = next(p for p in _HERE.parents if (p / "pyproject.toml").is_file())
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from probe_common import (CANCEL_TIMEOUT_S, disconnect_ok, paged_result, poll_task,  # noqa: E402
                          receipt_ok, record_cleanup, record_disconnect, write_json)
from zemax_mcp.analysis_models import RunAnalysis  # noqa: E402

KINDS = ("phase_aberration", "polarization_ray_trace", "polarization_transmission", "fiber_coupling_settings")
PATCH = {"polarization": {"unpolarized": False, "jx": 1.0, "jy": 0.0, "x_phase": 0.0, "y_phase": 90.0}}
EXPECTED = {"jx": 1.0, "jy": 0.0, "x_phase_deg": 0.0, "y_phase_deg": 90.0}
POLARIZATION_KEYS = ("unpolarized", "jx", "jy", "x_phase", "y_phase", "method", "convert_thin_film_phase")


def request(kind):
    """Validate through the real request model, then send its plain dump."""
    return RunAnalysis(request={"kind": kind}).request.model_dump(exclude_unset=True)


def header_jones(result):
    header = (result or {}).get("input_header") or {}
    jones = header.get("jones") or {}
    return {"unpolarized": header.get("unpolarized"), "jx": jones.get("jx"), "jy": jones.get("jy"),
            "x_phase_deg": jones.get("x_phase_deg"), "y_phase_deg": jones.get("y_phase_deg")}


def follows(header, expected=EXPECTED):
    return (header.get("jx") == expected["jx"] and header.get("jy") == expected["jy"]
            and header.get("x_phase_deg") == expected["x_phase_deg"]
            and header.get("y_phase_deg") == expected["y_phase_deg"])


def restore_patch(baseline):
    """Rebuild an ``update_system_settings`` payload from the baseline readback."""
    pol = (baseline or {}).get("polarization") or {}
    patch = {key: pol[key] for key in POLARIZATION_KEYS if pol.get(key) is not None}
    return {"settings": {"polarization": patch}} if patch else None


def probe(folder, call, model=None, timeout_s=120.0, receipts=None, cancel_timeout_s=CANCEL_TIMEOUT_S):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    record = {"probe": "N2", "purpose": "system polarization modify/read-back/restore and topic header comparison",
              "patch": PATCH, "expected": EXPECTED, "analyses": [], "restore_failures": []}
    baseline = None
    active = None
    try:
        call("connect", {})
        if model:
            call("open_lens", {"path": str(model)})
        baseline = call("get_system_settings", {})
        record["baseline"] = baseline
        call("update_system_settings", {"settings": PATCH})
        record["modified"] = call("get_system_settings", {})
        for kind in KINDS:
            if active is not None:
                record["analyses"].append(
                    {"kind": kind, "skipped": "previous native task not confirmed terminal"})
                continue
            entry = {"kind": kind}
            task = call("run_analysis", {"request": request(kind)})
            task = poll_task(call, task, record, timeout_s, cancel_timeout_s=cancel_timeout_s)
            entry["task_state"] = task.get("state")
            if task.get("poll_timed_out"):
                entry["poll_timed_out"] = True
                entry["terminated_after_cancel"] = task.get("terminated_after_cancel")
                if not task.get("terminated_after_cancel"):
                    active = {"task_id": task["task_id"], "last_state": task.get("state")}
            if task.get("state") == "succeeded":
                result = paged_result(call, task["task_id"], record)
                entry["header"] = header_jones(result)
                entry["follows_system"] = follows(entry["header"])
            record["analyses"].append(entry)
            if active is not None:
                record["aborted_native_task"] = active
    finally:
        target = restore_patch(baseline) if baseline is not None else None
        if target is not None and active is not None:
            record["restore_skipped"] = {
                "reason": "native task not confirmed terminal; restore must not run in parallel",
                "task": active}
        elif target is not None:
            try:
                call("update_system_settings", target)
                restored = call("get_system_settings", {})
                record["restored"] = restored
                record["restored_equal"] = restored == baseline
                if not record["restored_equal"]:
                    record["restore_failures"].append(
                        {"step": "restore", "detail": "readback differs from baseline", "restored": restored})
            except Exception as exc:
                record_cleanup(record["restore_failures"], "restore", exc)
        else:
            record["restore_skipped"] = "baseline has no explicit polarization to restore"
        try:
            returned = call("disconnect", {})
            record_disconnect(record, returned, receipts)
        except Exception as exc:
            record_cleanup(record["restore_failures"], "disconnect", exc)
        write_json(folder / "n2-system-polarization.json", record)
    return record


if __name__ == "__main__":
    import json

    from probe_common import adapter
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    out = Path(sys.argv[1]).resolve()
    os.environ['ZEMAX_STATE_DIR'] = str(out / 'state')
    backend = Backend(Config(Config.from_env().install_dir, out / "native"))
    receipts = []
    record = probe(out, adapter(backend, receipts), model=(sys.argv[2] if len(sys.argv) > 2 else None),
                   receipts=receipts)
    print(json.dumps({"folder": str(out), "analyses": [
        {"kind": a["kind"], "state": a.get("task_state"), "follows": a.get("follows_system"),
         "skipped": a.get("skipped")}
        for a in record["analyses"]], "restored_equal": record.get("restored_equal"),
        "restore_skipped": record.get("restore_skipped"),
        "disconnect_ok": record.get("disconnect", {}).get("ok"),
        "restore_failures": record["restore_failures"]}, ensure_ascii=False))
