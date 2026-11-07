from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean, dotnet_array
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import COMMAND_MODELS, FftMtf, SurfacePatch, SystemPatch


@pytest.mark.parametrize("command,args", [
    ("get_surfaces", {"start": -1}), ("get_surfaces", {"count": 0}),
    ("get_surfaces", {"start": True}), ("get_merit_function", {"start": 0}),
    ("run_fft_mtf", {"maximum_frequency": 0}), ("run_fft_mtf", {"maximum_frequency": float("nan")}),
    ("run_spot_analysis", {"reference": "not-a-reference"}),
    ("run_quick_focus", {"criterion": "SpotSizeRadial"}),
    ("run_local_optimization", {"cycles": "Infinite"}),
    ("update_system_settings", {"wavelengths": [{"wavelength_um": -0.55}]}),
    ("update_system_settings", {"title": None}),
    ("update_surfaces", {"changes": [{"surface": 1}]}),
    ("update_surfaces", {"changes": [{"surface": 1, "radius": 1}, {"surface": 1, "radius": 2}]}),
])
def test_invalid_requests_rejected_before_native_access(tmp_path, command, args):
    backend = Backend(Config(Path("unused"), tmp_path))
    result = backend.dispatch(command, args)
    assert not result["ok"]
    assert result["error"]["code"] == "INVALID_ARGUMENT"
    assert backend.revision == 0


def test_wavelength_in_micrometers_and_primary_bounds():
    req = SystemPatch(wavelengths=[{"wavelength_um": 0.55}], primary_wavelength=1)
    assert req.wavelengths[0].wavelength_um == 0.55
    with pytest.raises(ValidationError):
        SystemPatch(wavelengths=[{"wavelength_um": 0.55}], primary_wavelength=2)
    with pytest.raises(ValidationError):
        SystemPatch(fields=[{"x": 0, "y": 0, "weight": 0}])


def test_infinite_radius_is_explicit_json_string():
    assert SurfacePatch(surface=1, radius="Infinity").radius == "Infinity"
    with pytest.raises(ValidationError):
        SurfacePatch(surface=1, radius=float("inf"))
    assert clean({"x": float("inf"), "y": float("nan")}) == {"x": "Infinity", "y": "NaN"}


def test_solves_guarded_without_replacing_variable(tmp_path):
    backend = Backend(Config(Path("unused"), tmp_path))
    cell = SimpleNamespace(IsReadOnly=False, IsActive=True, Solve="SurfacePickup", Header="Thickness")
    with pytest.raises(ZemaxError, match="solve/pickup"):
        backend._guard_cell(cell)
    backend._guard_cell(cell, replace=True)
    cell.Solve = "Variable"
    backend._guard_cell(cell)
    cell.IsReadOnly = True
    with pytest.raises(ZemaxError):
        backend._guard_cell(cell, replace=True)


def test_non_square_dotnet_arrays_preserve_rows_and_columns():
    class Array:
        Rank = 2
        def GetLength(self, axis):
            return (2, 3)[axis]
        def __getitem__(self, item):
            row, col = item
            return 10 * row + col
    assert dotnet_array(Array()) == [[0, 1, 2], [10, 11, 12]]


class Analysis:
    def __init__(self):
        self.running = True
        self.closed = False
        self.waits = 0
    def IsRunning(self):
        return self.running
    def WaitForCompletion(self):
        self.waits += 1
    def Close(self):
        self.closed = True
    def Terminate(self):
        self.running = False


def task_backend(tmp_path):
    backend = Backend(Config(Path("unused"), tmp_path))
    analysis = Analysis()
    task = {"task_id": "test", "kind": "fft_mtf", "state": "running", "native": analysis,
            "analysis": True, "cancel_requested": False, "before": {}, "context": {"checkpoint": "saved.zos"},
            "settings": {}, "system_settings": {}, "can_cancel": True, "result": None}
    backend.tasks["test"] = task
    backend.active = task
    backend._collect = lambda t: {"value": 1}
    backend._save_task_result = lambda t, result: t.update(result=result)
    return backend, analysis, task


def test_analysis_running_is_a_method_and_resources_close(tmp_path):
    backend, native, task = task_backend(tmp_path)
    backend.tick()
    assert task["state"] == "running" and not native.closed
    native.running = False
    backend.tick()
    assert task["state"] == "succeeded"
    assert task["result"] == {"value": 1}
    assert native.closed and native.waits == 1 and backend.active is None


def test_busy_mutation_is_rejected_and_cancel_is_confirmed(tmp_path):
    backend, native, task = task_backend(tmp_path)
    response = backend.dispatch("new_system", {})
    assert response["error"]["code"] == "SYSTEM_BUSY"
    response = backend.dispatch("cancel_task", {"task_id": "test"})
    assert response["ok"] and task["state"] == "cancelled"
    assert task["result"]["completed"] is False
    assert native.closed and backend.active is None


def test_failure_closes_native_and_keeps_checkpoint(tmp_path):
    backend, native, task = task_backend(tmp_path)
    native.running = False
    def failure(_):
        raise ZemaxError("NO_RESULT_DATA", "no result")
    backend._collect = failure
    backend.last_checkpoint = "saved.zos"
    backend.tick()
    assert task["state"] == "failed" and task["error"]["code"] == "NO_RESULT_DATA"
    assert task["result"]["checkpoint"] == "saved.zos" and native.closed


def test_terminal_task_cancel_cannot_change_success(tmp_path):
    backend, native, task = task_backend(tmp_path)
    native.running = False
    backend.tick()
    assert backend.dispatch("cancel_task", {"task_id": "test"})["data"]["state"] == "succeeded"


def test_task_not_found_is_explicit(tmp_path):
    backend = Backend(Config(Path("unused"), tmp_path))
    assert backend.dispatch("get_task_status", {"task_id": "missing"})["error"]["code"] == "TASK_NOT_FOUND"


def test_failed_native_release_blocks_new_mutations(tmp_path):
    backend, native, task = task_backend(tmp_path)
    native.running = False
    native.Close = lambda: False
    backend.tick()
    assert backend.requires_reconnect
    assert backend.dispatch("new_system", {})["error"]["code"] == "RECONNECT_REQUIRED"
    assert "释放未确认" in task["cleanup_warnings"][0]
    view = backend.dispatch("get_task_status", {"task_id":"test"})["data"]
    assert view["close_attempted"] is True
    assert view["cleanup_warnings"] == task["cleanup_warnings"]


@pytest.mark.parametrize("args", [
    {"mode": "update", "updates": []},
    {"mode": "delete", "operand_numbers": [1, 1]},
    {"mode": "append", "updates": [{"operand": 1, "target": 0}]},
])
def test_merit_edit_modes_do_not_silently_ignore_parameters(args):
    with pytest.raises(ValidationError):
        COMMAND_MODELS["update_merit_function"].model_validate(args)


def test_large_results_are_bounded_and_keep_their_original_context(tmp_path):
    backend = Backend(Config(Path("unused"), tmp_path))
    backend.revision = 8
    series = {"series": 0, "description": "test", "labels": ["T", "S"], "x_label": "frequency",
              "x": list(range(2001)), "y": [[0.1, 0.2] for _ in range(2001)]}
    backend.tasks["done"] = {"state": "succeeded", "result": {
        "series": [series], "context": {"model_revision": 2}, "artifacts": [{"kind": "json", "path": "full.json"}],
    }}
    response = backend.dispatch("get_task_result", {"task_id": "done"})
    assert response["ok"] and response["data"]["inline_data_truncated"]
    assert response["data"]["series"][0]["point_count"] == 2001
    assert "y" not in response["data"]["series"][0]
    assert response["data"]["context"]["model_revision"] == 2
    assert response["context"]["model_revision"] == 8
    assert len(backend.tasks["done"]["result"]["series"][0]["y"]) == 2001
