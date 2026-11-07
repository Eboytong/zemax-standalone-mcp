"""Task status exposes already saved products without requesting another calculation."""
import json
from types import SimpleNamespace

from zemax_mcp.backend import Backend


def test_saved_task_products_are_exposed_only_after_successful_save(tmp_path):
    backend = Backend.__new__(Backend)
    backend.directory = tmp_path
    task = {"task_id": "saved", "kind": "analysis", "state": "succeeded", "context": {}, "system_settings": {}}
    assert "result_path" not in backend._task_view(task)
    backend._save_task_result(task, {"summary": {"value": 2}})
    view = backend._task_view(task)
    assert view["result_path"] == str(tmp_path / "saved.json")
    assert view["result_artifacts"] == [{"kind": "json", "path": str(tmp_path / "saved.json")}]
    assert json.loads((tmp_path / "saved.json").read_text(encoding="utf-8"))["task"]["task_id"] == "saved"


def test_failed_save_does_not_publish_a_result_path(tmp_path):
    backend = Backend.__new__(Backend)
    backend.directory = tmp_path / "unavailable"
    task = {"task_id": "failed", "context": {}, "system_settings": {}}
    import pytest
    with pytest.raises(FileNotFoundError):
        backend._save_task_result(task, {})
    assert "result_path" not in backend._task_view(task)
    assert "result_artifacts" not in backend._task_view(task)


def test_live_result_overlays_close_outcome_after_saved_snapshot(tmp_path):
    from zemax_mcp.models import TaskResult
    backend = Backend.__new__(Backend)
    backend.directory = tmp_path
    task = {"task_id":"saved","kind":"analysis","state":"succeeded","context":{},"system_settings":{}}
    backend.tasks = {"saved":task}
    backend._save_task_result(task, {"summary":{"value":2}})
    assert "close_attempted" not in json.loads((tmp_path/"saved.json").read_text(encoding="utf-8"))["task"]
    task["close_attempted"] = True
    task["cleanup_warnings"] = ["native Close rejected"]
    result = backend.get_task_result(TaskResult(task_id="saved"))
    assert result["task"]["close_attempted"] is True
    assert result["task"]["cleanup_warnings"] == ["native Close rejected"]
