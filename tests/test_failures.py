from pathlib import Path
from types import SimpleNamespace

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


class LensSystem:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []
        self.model = "old"

    def New(self, save):
        self.calls.append("new")
        self.model = "new"
        if self.failure == "new":
            raise RuntimeError("new failed after mutation")

    def MakeSequential(self):
        self.calls.append("sequential")
        if self.failure == "sequential":
            raise RuntimeError("mode failed")

    def LoadFile(self, path, save):
        self.calls.append("load")
        if self.failure == "load":
            return False
        self.model = "loaded"
        return True

    def SaveAs(self, path):
        self.calls.append(("save", path))
        if self.failure == "save":
            raise OSError("save failed")


def lens_backend(tmp_path, failure=None):
    system = LensSystem(failure)
    backend = Backend(Config(Path("unused"), tmp_path), SimpleNamespace(system=system))
    backend.directory = tmp_path
    backend.work_path = tmp_path / "old_work.zos"
    backend.source_path = str(tmp_path / "old_source.zos")
    backend.revision = 7
    backend._checkpoint = lambda label: setattr(backend, "last_checkpoint", "before.zos")
    backend.get_system_summary = lambda req: {"model": system.model}
    return backend, system


def test_load_false_keeps_source_and_does_not_save_working_copy(tmp_path):
    backend, system = lens_backend(tmp_path, "load")
    source, work = backend.source_path, backend.work_path
    requested = tmp_path / "input.zos"
    requested.touch()
    response = backend.dispatch("open_lens", {"path": str(requested)})
    assert not response["ok"] and response["error"]["code"] == "LOAD_FAILED"
    assert backend.source_path == source and backend.work_path == work
    assert system.calls == ["load"] and system.model == "old"
    assert backend.revision == 8  # A native mutation attempt invalidates old results.
    assert response["error"]["details"]["partial_changes_possible"]


@pytest.mark.parametrize("failure", ["new", "sequential", "save"])
def test_new_failure_advances_revision_without_claiming_a_working_file(tmp_path, failure):
    backend, system = lens_backend(tmp_path, failure)
    response = backend.dispatch("new_system", {})
    assert not response["ok"] and response["error"]["code"] == "NATIVE_ERROR"
    assert system.model == "new" and backend.revision == 8
    assert response["error"]["details"]["partial_changes_possible"]
    assert response["context"]["working_file"] is None
    assert response["context"]["source_file"] is None
    assert response["context"]["checkpoint"] == "before.zos"


@pytest.mark.parametrize("command", ["new_system", "open_lens"])
def test_replacement_commits_working_file_after_save_and_increments_once(tmp_path, command):
    backend, system = lens_backend(tmp_path)
    saved = []

    def save(path):
        assert backend.work_path is None
        saved.append(path)

    system.SaveAs = save
    requested = tmp_path / "input.zos"
    requested.touch()
    response = backend.dispatch(command, {"path": str(requested)} if command == "open_lens" else {})
    assert response["ok"] and backend.revision == 8
    assert saved == [str(backend.work_path)]
    assert backend.source_path == (str(requested) if command == "open_lens" else None)


def test_loaded_model_save_failure_does_not_reuse_old_working_file(tmp_path):
    backend, system = lens_backend(tmp_path, "save")
    requested = tmp_path / "input.zos"
    requested.touch()
    response = backend.dispatch("open_lens", {"path": str(requested)})
    assert not response["ok"] and response["error"]["details"]["partial_changes_possible"]
    assert system.model == "loaded" and backend.source_path == str(requested)
    assert backend.work_path is None


class FailingTask:
    ErrorMessage = "native start rejected"
    CanCancel = True

    def __init__(self, stage, close):
        self.stage = stage
        self.close = close
        self.closes = 0

    def Run(self):
        if self.stage == "run_raises":
            raise RuntimeError("run exception")
        return False

    def Apply(self):
        raise RuntimeError("apply exception")

    def Close(self):
        self.closes += 1
        if self.close == "raises":
            raise RuntimeError("close exception")
        return self.close == "success"


@pytest.mark.parametrize("stage", ["run_false", "run_raises", "apply", "settings", "can_cancel"])
@pytest.mark.parametrize("close", ["success", "false", "raises"])
def test_start_failures_keep_error_and_use_checked_release(tmp_path, stage, close):
    backend = Backend(Config(Path("unused"), tmp_path))
    backend.last_checkpoint = "before.zos"
    native = FailingTask(stage, close)

    def settings(req):
        if stage == "settings":
            raise RuntimeError("settings unavailable")
        return {"lens_units": "Millimeters"}

    if stage == "can_cancel":
        class UnavailableCancel(FailingTask):
            @property
            def CanCancel(self):
                raise RuntimeError("cancel capability unavailable")
        native = UnavailableCancel(stage, close)
    backend.get_system_settings = settings
    backend.run_quick_focus = lambda req: backend._start_task(
        "test", native, {}, analysis=stage == "apply")
    response = backend.dispatch("run_quick_focus", {"criterion": "SpotSizeRadial", "use_centroid": True}, request_id="start-request")
    assert not response["ok"] and response["error"]["code"] == "TASK_START_FAILED"
    task_id = response["error"]["details"]["task_id"]
    task = backend.tasks[task_id]
    assert task["state"] == "failed" and task["finished_at"]
    assert task["request_id"] == "start-request"
    assert task["error"]["message"] == response["error"]["message"]
    assert "close exception" not in task["error"]["message"]
    assert task["native"] is None and backend.active is None and native.closes == 1
    assert backend.requires_reconnect == (close != "success")
    result = backend.dispatch("get_task_result", {"task_id": task_id})
    status = backend.dispatch("get_task_status", {"task_id": task_id})
    assert result["ok"] and result["data"]["completed"] is False
    assert result["data"]["checkpoint"] == "before.zos"
    assert status["ok"] and status["data"]["error"]["code"] == "TASK_START_FAILED"
    if close != "success":
        assert status["data"]["cleanup_warnings"]
        assert backend.dispatch("new_system", {})["error"]["code"] == "RECONNECT_REQUIRED"
    else:
        backend.new_system = lambda req: {"created": True}
        assert backend.dispatch("new_system", {})["ok"]
