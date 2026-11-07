"""JSON transport, task lifecycle and shutdown regressions."""
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean


def test_json_boundary_normalizes_signed_zero_without_replacing_valid_data():
    raw = {"series": [[-0.0, 0.0, -1e-200, 1e-200]], "special": [float("nan"), float("inf"), -float("inf")]}
    result = clean(raw)
    assert result["special"] == ["NaN", "Infinity", "-Infinity"]
    assert all(math.copysign(1, v) == 1 for v in result["series"][0][:2])
    assert result["series"][0][2:] == [-1e-200, 1e-200]
    assert math.copysign(1, raw["series"][0][0]) == -1
    json.dumps(result, allow_nan=False)






class Hammer:
    IsRunning = True
    IsFiniteDuration = False
    CanCancel = True
    Status = "Waiting"
    cancels = 0

    @property
    def Progress(self):
        raise RuntimeError("optional telemetry unavailable")

    def Cancel(self):
        self.cancels += 1
        return True


def backend_task(tmp_path, tool=None):
    b = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace())
    task = {"task_id": "child", "kind": "optimization_native", "state": "running", "native": tool or Hammer(),
            "analysis": False, "progress": None, "cancel_requested": False, "started_monotonic": 100,
            "budget_seconds": 90, "budget_deadline": 190}
    b.active = task
    b.tasks["child"] = task
    return b, task


def test_budget_stop_is_checked_even_when_progress_is_unavailable(tmp_path, monkeypatch):
    b, task = backend_task(tmp_path)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 191)
    b.tick()
    assert task["state"] == "running"
    assert task["budget_stop_requested"] is True
    assert task["native"].cancels == 1
    assert task["progress"] is None
    b.tick()
    assert task["native"].cancels == 1
    view = b._task_view(task)
    assert view["elapsed_seconds"] == 91
    assert view["budget_remaining_seconds"] == 0
    assert view["budget_expired"] is True


def test_budget_waits_for_native_safe_boundary_without_claiming_stopped(tmp_path, monkeypatch):
    tool = Hammer(); tool.CanCancel = False
    b, task = backend_task(tmp_path, tool)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 191)
    b.tick()
    assert task["state"] == "running"
    assert not task.get("budget_stop_requested")
    assert tool.cancels == 0
    assert "安全边界" in task["status"]


def test_73_seconds_is_not_a_90_second_overrun_and_parent_exposes_child(tmp_path, monkeypatch):
    b, child = backend_task(tmp_path)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 173)
    parent = {"task_id": "parent", "kind": "hammer_optimization", "state": "running", "started_monotonic": 100,
              "progress": 0, "child": child, "phase": "optimization", "cancel_requested": False}
    view = b._task_view(parent)
    assert view["elapsed_seconds"] == 73
    assert view["progress"] is None
    assert view["active_step"]["budget_remaining_seconds"] == 17
    assert not view["active_step"]["budget_expired"]


def test_hammer_cancel_reports_retained_candidate_not_automatic_rollback(tmp_path):
    b, child = backend_task(tmp_path)
    parent = {"task_id": "parent", "kind": "hammer_optimization", "state": "running", "composite": True,
              "child": child, "cancellation_effect": "retain_candidate", "cancel_requested": False}
    b.tasks["parent"] = parent
    view = b.cancel_task(SimpleNamespace(task_id="parent"))
    assert view["state"] == "cancelling"
    assert "不会自动恢复基线" in view["status"]
    assert child["cancel_requested"] is True
    assert child["native"].cancels == 1


@pytest.mark.parametrize("cancel_outcome", ["false", "raise"])
def test_budget_cancel_failure_retains_active_native_until_actual_stop(tmp_path, monkeypatch, cancel_outcome):
    class UnstoppableHammer(Hammer):
        def __init__(self):
            self.cancels = 0
            self.closes = 0
            self.waits = 0
            self.IsRunning = True

        def Cancel(self):
            self.cancels += 1
            if cancel_outcome == "raise":
                raise RuntimeError("budget stop transport failed")
            return False

        def Close(self):
            self.closes += 1
            assert not self.IsRunning, "must not close a still-running native tool"
            return True

        def WaitForCompletion(self):
            self.waits += 1
            assert not self.IsRunning

    tool = UnstoppableHammer()
    b, task = backend_task(tmp_path, tool)
    task.update(before={}, context={"checkpoint": None}, system_settings={})
    b._collect = lambda _: {"completed": True}
    b._save_task_result = lambda task, result: task.update(result=result)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 191)

    b.tick()
    assert task["state"] == "running"
    assert b.active is task and task["native"] is tool
    assert task["budget_stop_attempted"] is True and task.get("budget_stop_error")
    assert not task.get("budget_stop_requested")
    assert tool.cancels == 1 and tool.closes == tool.waits == 0
    view = b._task_view(task)
    assert view["state"] == "running"
    assert view["budget_stop_attempted"] is True and view.get("budget_stop_error")

    b.tick()
    assert task["state"] == "running" and b.active is task
    assert tool.cancels == 1 and tool.closes == tool.waits == 0

    tool.IsRunning = False
    b.tick()
    assert task["state"] == "succeeded"
    assert b.active is None and task["native"] is None
    assert tool.cancels == 1 and tool.closes == tool.waits == 1


def test_can_cancel_read_error_preserves_running_tool_and_exposes_telemetry_error(tmp_path, monkeypatch):
    class NoCancelTelemetry(Hammer):
        closes = 0
        @property
        def CanCancel(self):
            raise RuntimeError("CanCancel transport read failed")
        def Close(self):
            self.closes += 1
            return True

    tool = NoCancelTelemetry()
    b, task = backend_task(tmp_path, tool)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 191)
    b.tick()
    assert task["state"] == "running" and b.active is task and task["native"] is tool
    assert task["can_cancel"] is False and task.get("telemetry_error")
    assert b._task_view(task).get("telemetry_error")
    assert tool.closes == 0 and not task.get("budget_stop_requested")
    b.tick()
    assert task["state"] == "running" and tool.closes == 0


def test_status_lists_every_running_task_and_indexes_all_tasks_for_reconciliation(tmp_path):
    b = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(application=None))
    for index in range(12):
        b.tasks[f"t{index:02d}"] = {"task_id": f"t{index:02d}", "kind": "spot", "state": "running" if index > 6 else "succeeded",
                                    "finished_at": None if index > 6 else "2026-10-28T09:40:32Z"}
    status = b.get_status(None)
    # Only the last ten tasks fit in recent_tasks; the poll also needs the rest.
    assert len(status["recent_tasks"]) == 10
    assert [view["task_id"] for view in status["running_tasks"]] == [f"t{index:02d}" for index in range(11, 6, -1)]
    assert set(status["task_index"]) == set(b.tasks)
    assert status["task_index"]["t00"]["state"] == "succeeded"
    assert status["task_index"]["t11"]["state"] == "running"
    json.dumps(status, allow_nan=False, ensure_ascii=False)


def test_shutdown_writes_a_receipt_naming_the_generation_and_native_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ZEMAX_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ZEMAX_GENERATION", "generation-under-test")
    closed = {"value": False}

    class Native:
        application = object()

        def disconnect(self):
            closed["value"] = True
            self.application = None

    b = Backend(Config(tmp_path, tmp_path), native=Native())
    b.shutdown()
    receipt = json.loads((tmp_path / "close_receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema_version"] == 1
    assert receipt["generation"] == "generation-under-test"
    assert receipt["native"] == {"attempted": True, "closed": True, "error": None}
    assert receipt["was_connected"] is True
    assert receipt["closed_at"]
    assert closed["value"] is True
    assert not list(tmp_path.glob("close_receipt.*.tmp"))


def test_shutdown_receipt_is_honest_when_the_native_close_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("ZEMAX_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("ZEMAX_GENERATION", "generation-under-test")

    class Native:
        application = object()

        def disconnect(self):
            raise RuntimeError("COM release failed")

    b = Backend(Config(tmp_path, tmp_path), native=Native())
    b.shutdown()
    receipt = json.loads((tmp_path / "close_receipt.json").read_text(encoding="utf-8"))
    assert receipt["native"]["attempted"] is True
    assert receipt["native"]["closed"] is False
    assert "COM release failed" in receipt["native"]["error"]


def test_shutdown_without_a_state_directory_neither_writes_nor_claims_a_receipt(tmp_path, monkeypatch):
    monkeypatch.delenv("ZEMAX_STATE_DIR", raising=False)
    b = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace())
    b.shutdown()
    assert not (tmp_path / "close_receipt.json").exists()


def test_unknown_is_running_retains_handle_busy_lock_and_requires_reconnect(tmp_path, monkeypatch):
    class UnknownRunning(Hammer):
        closes = 0
        @property
        def IsRunning(self):
            raise RuntimeError("IsRunning transport read failed")
        def Close(self):
            self.closes += 1
            return True

    tool = UnknownRunning()
    b, task = backend_task(tmp_path, tool)
    monkeypatch.setattr("zemax_mcp.backend.time.monotonic", lambda: 191)
    b.tick()
    assert task["state"] == "running" and b.active is task and task["native"] is tool
    assert b.requires_reconnect is True and task.get("poll_error")
    assert b._task_view(task).get("poll_error")
    assert tool.closes == 0
    # The uncertain task must remain readable, not disappear into a false terminal state.
    response = b.dispatch("get_task_status", {"task_id": "child"})
    assert response["ok"] and response["data"]["state"] == "running"
    assert response["context"]["requires_reconnect"] is True
    assert b.active is task and task["native"] is tool and tool.closes == 0
