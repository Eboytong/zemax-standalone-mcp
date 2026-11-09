"""Consumer lifecycle coverage for the two default text report kinds.

These drive the *shared* task lifecycle (``_start_task`` / ``cancel_task`` / ``tick`` /
``_close_task_native``) instead of stubbing ``_start_task``, so a cancel or a failure is
only reported as verified when the native analysis tool was actually closed.
"""
from types import SimpleNamespace
import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import TaskRequest
from zemax_mcp.native_text_reports import PrescriptionDataReport, SurfaceDataReport, run_text_report

REQUESTS = [SurfaceDataReport(kind='surface_data'),
            PrescriptionDataReport(kind='prescription_data', sections=['index_data'])]


class ReportTool:
    """Minimal native analysis stand-in for the shared lifecycle."""

    def __init__(self, *, running=True, close_ok=True, wait_error=None):
        self.running = running
        self.close_ok = close_ok
        self.wait_error = wait_error
        self.terminated = 0
        self.closes = 0
        self.applied = 0

    def GetSettings(self):
        return SimpleNamespace()

    def Apply(self):
        self.applied += 1

    def Terminate(self):
        self.terminated += 1

    def IsRunning(self):
        return self.running

    def WaitForCompletion(self):
        if self.wait_error is not None:
            raise self.wait_error

    def Close(self):
        self.closes += 1
        return self.close_ok


def backend_for(tmp_path, tool, monkeypatch):
    """Real Backend and real lifecycle; only the native tool and its settings are faked."""
    backend = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace())
    backend._require_work = lambda: None
    backend.get_system_settings = lambda req: {}
    monkeypatch.setattr("zemax_mcp.imaging.new_analysis", lambda backend, name: tool)
    monkeypatch.setattr("zemax_mcp.analyses.scalar_settings", lambda settings: {"Base": "value"})
    return backend


@pytest.mark.parametrize('report_request', REQUESTS)
def test_cancel_terminates_then_closes_through_the_shared_lifecycle(tmp_path, monkeypatch, report_request):
    tool = ReportTool()
    backend = backend_for(tmp_path, tool, monkeypatch)

    view = run_text_report(backend, report_request)
    assert view["state"] == "running"
    assert tool.applied == 1          # analysis tasks are started with Apply()
    task_id = view["task_id"]

    cancelled = backend.cancel_task(TaskRequest(task_id=task_id))
    assert cancelled["state"] == "cancelling"
    assert tool.terminated == 1       # analysis tasks are stopped with Terminate()
    assert tool.closes == 0           # nothing is closed while the native tool still runs

    tool.running = False
    backend.tick()

    task = backend.tasks[task_id]
    assert task["state"] == "cancelled"
    assert task["close_attempted"] is True
    assert tool.closes == 1           # the native tool really was closed
    assert not task.get("cleanup_warnings")
    assert backend.active is None
    assert backend.requires_reconnect is False


@pytest.mark.parametrize('report_request', REQUESTS)
def test_failure_after_start_closes_the_native_tool(tmp_path, monkeypatch, report_request):
    tool = ReportTool(wait_error=RuntimeError("native wait failed"))
    backend = backend_for(tmp_path, tool, monkeypatch)

    view = run_text_report(backend, report_request)
    tool.running = False
    backend.tick()

    task = backend.tasks[view["task_id"]]
    assert task["state"] == "failed"
    assert task["error"]["code"] == "NATIVE_ERROR"
    assert task["close_attempted"] is True
    assert tool.closes == 1
    assert backend.active is None


@pytest.mark.parametrize('report_request', REQUESTS)
def test_close_failure_keeps_warnings_and_requires_reconnect(tmp_path, monkeypatch, report_request):
    tool = ReportTool(close_ok=False, wait_error=RuntimeError("native wait failed"))
    backend = backend_for(tmp_path, tool, monkeypatch)

    view = run_text_report(backend, report_request)
    tool.running = False
    backend.tick()

    task = backend.tasks[view["task_id"]]
    assert task["state"] == "failed"
    assert task["cleanup_warnings"] == ["原生 Close 返回 false；资源释放未确认。"]
    assert backend.requires_reconnect is True
    assert backend.active is None


@pytest.mark.parametrize('report_request', REQUESTS)
def test_cancel_is_not_reported_before_the_native_stop_is_confirmed(tmp_path, monkeypatch, report_request):
    """A cancel request alone must not be reported as a finished close."""
    tool = ReportTool()
    backend = backend_for(tmp_path, tool, monkeypatch)

    view = run_text_report(backend, report_request)
    backend.cancel_task(TaskRequest(task_id=view["task_id"]))

    task = backend.tasks[view["task_id"]]
    assert task["state"] == "cancelling"
    assert task.get("close_attempted") is None
    assert tool.closes == 0
    assert backend.active is task
