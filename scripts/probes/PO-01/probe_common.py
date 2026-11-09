"""Shared helpers for the bounded PO-01 native control probes (N1/N2/N3).

Importing this module creates no OpticStudio instance.  Every probe receives a
``call(tool, args) -> data`` callable, so the same code path runs against the
real MCP tool contract in production and against an offline fake in ordinary
tests.

Contract rules enforced here:

* a tool receipt is judged by its own fields (``ok``/``success``), never by the
  truthiness of a payload dict;
* a poll that times out keeps the last observed state, requests cancellation and
  confirms the terminal state within a second bounded deadline;
* paging stops with a concrete error when the cursor does not advance;
* cleanup failures are recorded separately from the main conclusion.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

TERMINAL = {"succeeded", "failed", "cancelled"}
CANCEL_TIMEOUT_S = 5.0
PAGE_LIMIT = 1000


class ProbeFailure(RuntimeError):
    """A tool call returned ``ok == False``; keeps the raw reply for evidence."""

    def __init__(self, step: str, reply=None):
        super().__init__(f"{step} failed: {reply}")
        self.step = step
        self.reply = reply


def receipt_ok(reply):
    """Read a receipt's own success field; ``None`` when it has none."""
    if isinstance(reply, dict):
        for key in ("ok", "success"):
            if key in reply:
                return bool(reply[key])
    return None


def disconnect_ok(reply):
    """Disconnect success: explicit flag first, else ``connected is False``."""
    ok = receipt_ok(reply)
    if ok is not None:
        return ok
    if isinstance(reply, dict):
        for candidate in (reply, reply.get("data")):
            if isinstance(candidate, dict) and "connected" in candidate:
                return candidate["connected"] is False
    return None


def receipt(step, reply, arguments=None):
    return {"step": step, "arguments": dict(arguments or {}),
            "ok": receipt_ok(reply), "reply": reply}


def adapter(backend, receipts=None):
    """Wrap ``Backend.dispatch`` into a raising ``call(tool, args)``.

    ``receipts`` (a list) keeps every raw receipt so probes can record the exact
    request/response pair instead of a derived boolean.
    """

    def call(tool, args=None, **_):
        native_args = args or {}
        wrapper = {'update_system_settings': 'settings', 'run_batch_ray_trace': 'request'}.get(tool)
        if wrapper and set(native_args) == {wrapper}:
            native_args = native_args[wrapper]
        reply = backend.dispatch(tool, native_args)
        if receipts is not None:
            receipts.append(receipt(tool, reply, args))
            if native_args is not args and wrapper:
                receipts[-1]['backend_arguments'] = native_args
        if not receipt_ok(reply):
            raise ProbeFailure(tool, reply)
        return reply.get("data") if isinstance(reply, dict) and "data" in reply else reply

    return call


def dispatch_checked(backend, receipts, tool, args=None):
    """Raw receipt for CLI startup steps; records and returns it without raising."""
    reply = backend.dispatch(tool, args or {})
    entry = receipt(tool, reply, args)
    receipts.append(entry)
    return entry


def last_receipt(receipts, tool):
    for entry in reversed(list(receipts or [])):
        if entry.get("tool") == tool or entry.get("step") == tool:
            return entry
    return None


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def cancel_and_confirm(call, task_id, record, timeout_s=CANCEL_TIMEOUT_S, interval_s=0.02,
                       clock=time.monotonic, sleep=time.sleep):
    """Request cancellation and confirm the terminal state within a bounded window."""
    result = {"requested": False, "receipt": None, "terminal": False,
              "final_state": None, "error": None}
    try:
        result["receipt"] = call("cancel_task", {"task_id": task_id})
        result["requested"] = True
    except Exception as exc:
        result["error"] = repr(exc)
        record_cleanup(record.setdefault("cleanup_failures", []), "cancel_task", exc)
        return result
    deadline = clock() + timeout_s
    while True:
        try:
            status = call("get_task_status", {"task_id": task_id}) or {}
        except Exception as exc:
            result["error"] = repr(exc)
            return result
        result["final_state"] = status.get("state")
        if result["final_state"] in TERMINAL:
            result["terminal"] = True
            break
        if clock() > deadline:
            break
        sleep(interval_s)
    return result


def poll_task(call, task, record, timeout_s=120.0, interval_s=0.02, clock=time.monotonic,
              sleep=time.sleep, cancel_timeout_s=CANCEL_TIMEOUT_S):
    """Poll one task within a bounded deadline.

    On timeout the last observed state is preserved under ``record['poll_timeout']``,
    cancellation is requested, and the terminal state is confirmed within a
    second bounded deadline.  The returned task carries ``poll_timed_out`` and
    ``terminated_after_cancel`` so callers can stop before starting new work.
    """
    if not isinstance(task, dict) or "task_id" not in task:
        raise ProbeFailure("task", task)
    deadline = clock() + timeout_s
    states = [task.get("state")]
    while task.get("state") not in TERMINAL:
        if clock() > deadline:
            entry = {"task_id": task["task_id"], "seconds": timeout_s,
                     "last_state": task.get("state"), "states": states[:50]}
            entry["cancel"] = cancel_and_confirm(call, task["task_id"], record,
                                                 timeout_s=cancel_timeout_s,
                                                 interval_s=interval_s, clock=clock, sleep=sleep)
            record.setdefault("poll_timeout", []).append(entry)
            task = dict(task)
            task["poll_timed_out"] = True
            task["terminated_after_cancel"] = entry["cancel"]["terminal"]
            return task
        sleep(interval_s)
        task = call("get_task_status", {"task_id": task["task_id"]})
        states.append(task.get("state"))
    record.setdefault("poll_states", {})[task["task_id"]] = states[:50]
    return task


def paged_result(call, task_id, record, chunk=200, max_pages=PAGE_LIMIT):
    """Read a finished task through the generic ``get_task_result`` paging contract.

    ``next_start`` must be an unseen offset strictly greater than the previous
    one; a repeat, a first-time backward jump and an exceeded page limit all stop
    with a concrete :class:`ProbeFailure`, so paging can never loop or cycle.
    """
    first = call("get_task_result", {"task_id": task_id, "count": chunk})
    rows = list(first.get("rows") or [])
    pages = 1
    seen = {0}
    last = 0
    nxt = first.get("next_start")
    while nxt is not None:
        if not isinstance(nxt, int) or isinstance(nxt, bool) or nxt < 0:
            raise ProbeFailure("get_task_result", {"reason": "invalid_next_start",
                                                   "task_id": task_id, "next_start": nxt, "pages": pages})
        if nxt in seen:
            raise ProbeFailure("get_task_result", {"reason": "cursor_repeated",
                                                   "task_id": task_id, "next_start": nxt,
                                                   "previous_start": last, "pages": pages})
        if nxt <= last:
            raise ProbeFailure("get_task_result", {"reason": "cursor_not_advancing",
                                                   "task_id": task_id, "next_start": nxt,
                                                   "previous_start": last, "pages": pages})
        if pages >= max_pages:
            raise ProbeFailure("get_task_result", {"reason": "page_limit",
                                                   "task_id": task_id, "pages": pages, "rows": len(rows)})
        seen.add(nxt)
        last = nxt
        page = call("get_task_result", {"task_id": task_id, "start": nxt, "count": chunk})
        rows.extend(page.get("rows") or [])
        pages += 1
        nxt = page.get("next_start")
    merged = dict(first)
    merged["rows"] = rows
    record.setdefault("paging", {})[task_id] = {"pages": pages, "rows": len(rows)}
    return merged


def record_cleanup(failures, step, exc):
    failures.append({"step": step, "error": repr(exc), "reply": getattr(exc, "reply", None)})


def record_disconnect(record, returned, receipts):
    """Record the disconnect result from the receipt, never from dict truthiness."""
    entry = last_receipt(receipts, "disconnect")
    reply = entry["reply"] if entry else returned
    record["disconnect"] = {"ok": disconnect_ok(reply),
                            "returned": returned, "reply": reply,
                            "from_receipt": entry is not None}
    state_dir = os.environ.get("ZEMAX_STATE_DIR")
    if state_dir:
        path = Path(state_dir) / 'close_receipt.json'
        evidence = dict(path=str(path), confirmed=False)
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            native = data.get('native') or {}
            expected_session = (returned.get('last_session') or {}).get('session_id') if isinstance(returned, dict) else None
            evidence.update(content=data, confirmed=(expected_session is not None
                and data.get('session_id') == expected_session
                and native.get('closed') is True and data.get('forced') is False
                and not native.get('error')))
        except (OSError, ValueError) as exc:
            evidence['error'] = repr(exc)
        record['native_close_receipt'] = evidence
    return record["disconnect"]
