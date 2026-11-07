from tests.support.evaluation import fake_backend, finish, start
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.evaluation import interpolate
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import COMMAND_MODELS, TaskResult


@pytest.mark.parametrize("command,args", [
    ("run_batch_ray_trace", {"rays": []}),
    ("run_batch_ray_trace", {"rays": [{"wavelength": 0}]}),
    ("run_parameter_scan", {"surface": 1, "cell": "material", "values": [1], "evaluation": {"merit": True}}),
    ("run_parameter_scan", {"surface": 1, "cell": "thickness", "values": [1]*201, "evaluation": {"merit": True}}),
    ("run_batch_evaluation", {"paths": [], "evaluation": {"merit": True}}),
    ("run_batch_evaluation", {"paths": ["x.zos"], "evaluation": {}}),
    ("run_batch_evaluation", {"paths": ["x.zos"], "evaluation": {"merit": True, "frequencies": [10]}}),
    ("get_task_result", {"task_id": "t", "start": -1}),
    ("get_task_result", {"task_id": "t", "count": 1001}),
])
def test_invalid_evaluation_requests(command, args):
    with pytest.raises(ValidationError):
        COMMAND_MODELS[command].model_validate(args)


def test_interpolation_boundaries_and_range():
    assert interpolate([0, 10], [1, .5], 5)==.75
    assert interpolate([0, 10], [1, .5], 0)==1
    assert interpolate([0, 10], [1, .5], 10)==.5
    for x,y,f in [([], [], 0), ([0, 0], [1,1], 0), ([0, 10], [1,.5], 11)]:
        with pytest.raises(ZemaxError):
            interpolate(x,y,f)








def test_scan_independent_points_failure_continue_restore_pagination(tmp_path):
    b, system = fake_backend(tmp_path)
    task_id = start(b, [5, -1, 8])
    finish(b)
    result = b.get_task_result(TaskResult(task_id=task_id, count=2))
    assert result["summary"]=={"requested": 3, "processed": 3, "succeeded": 2, "failed": 1}
    assert result["rows"][0]["metrics"][0]["value"]==5
    assert result["rows"][1]["state"]=="failed"
    assert result["next_start"]==2 and result["total"]==3
    assert b.get_task_result(TaskResult(task_id=task_id, start=100))["rows"]==[]
    assert system.value==4 and b.source_path=="source.zos" and b.work_path==tmp_path/"original.zos"
    assert result["restoration"]["restored"] and b.revision>0


@pytest.mark.parametrize("advance", [0, 2])
def test_cancel_restores_baseline(tmp_path, advance):
    b, system = fake_backend(tmp_path)
    task_id = start(b, [5,6,7])
    for _ in range(advance):
        b.tick()
    b.dispatch("cancel_task", {"task_id": task_id})
    finish(b)
    assert b.tasks[task_id]["state"]=="cancelled"
    assert system.value==4
    assert b._full_result(task_id)["restoration"]["restored"]


def test_restore_failure_blocks_mutations(tmp_path):
    b, system = fake_backend(tmp_path)
    task_id = start(b, [5])
    b.tick()
    system.fail_restore = True
    finish(b)
    assert b.tasks[task_id]["state"]=="failed" and b.requires_reconnect
    assert b.dispatch("new_system", {})["error"]["code"]=="RECONNECT_REQUIRED"
    assert not b._full_result(task_id)["restoration"]["restored"]


def test_incompatible_comparison_and_report(tmp_path):
    b, system = fake_backend(tmp_path)
    left = start(b, [5]); finish(b)
    right = start(b, [6]); finish(b)
    req = COMMAND_MODELS["compare_results"](left_task_id=left, right_task_id=right)
    assert b.compare_results(req)["metrics"][0]["delta"]==1
    result = b._full_result(right)
    result["rows"][0]["conditions"] = {"focus": "different"}
    b.tasks[right].pop("result_path")
    b.tasks[right]["result"] = result
    assert not b.compare_results(req)["compatible"]
    report = b.export_evaluation_report(COMMAND_MODELS["export_evaluation_report"](task_ids=[left,right]))
    assert len(report["artifacts"])==5


def merit_backend(tmp_path, invalid=None):
    b, system = fake_backend(tmp_path)
    b._evaluate = Backend._evaluate.__get__(b)
    b.evaluate_merit_function = lambda _: {"merit_function": invalid if system.value < 0 else system.value}
    b.get_merit_function = lambda _: {"next_start": None, "operands": [{
        "operand": 1, "type": "EFFL", "target": 50., "weight": 1.,
        "parameters": {"3": {"header": "Wave", "value": 1}},
        "value": system.value, "contribution": system.value / 10,
        "future_runtime_field": system.value * 2}]}
    return b, system


def test_independent_merit_results_compare_despite_dynamic_contributions(tmp_path):
    b, _ = merit_backend(tmp_path)
    left = start(b, [5]); finish(b)
    right = start(b, [8]); finish(b)
    x, y = b._full_result(left)["rows"][0], b._full_result(right)["rows"][0]
    assert x["merit_operands"][0]["value"] == 5
    assert y["merit_operands"][0]["contribution"] == .8
    assert x["conditions"]["merit_definition"] == y["conditions"]["merit_definition"]
    assert set(x["conditions"]["merit_definition"][0]) == {"operand", "type", "target", "weight", "parameters"}
    response = b.dispatch("compare_results", {"left_task_id": left, "right_task_id": right})
    assert response["ok"] and response["data"]["compatible"]
    assert response["data"]["metrics"][0]["delta"] == 3


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_merit_fails_point_and_restores_model(tmp_path, invalid):
    b, system = merit_backend(tmp_path, invalid)
    task_id = start(b, [5, -1, 8]); finish(b)
    result = b._full_result(task_id)
    assert result["summary"]["succeeded"] == 2 and result["summary"]["failed"] == 1
    failed = result["rows"][1]
    assert failed["state"] == "failed" and "metrics" not in failed
    assert failed["error"]["code"] == "INVALID_METRIC_VALUE"
    assert failed["error"]["details"]["metric"] == "merit_function"
    assert result["restoration"]["restored"] and system.value == 4


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity", "-Infinity", True, None])
@pytest.mark.parametrize("side", ["left", "right"])
def test_comparison_rejects_invalid_stored_metrics_explicitly(tmp_path, invalid, side):
    b, _ = fake_backend(tmp_path)
    for task_id, value in (("left", 1.), ("right", 2.)):
        b.tasks[task_id] = {"state": "succeeded", "result": {"rows": [{
            "state": "succeeded", "conditions": {},
            "metrics": [{"key": "merit_function", "value": invalid if task_id == side else value, "unit": "merit function"}]}]}}
    response = b.dispatch("compare_results", {"left_task_id": "left", "right_task_id": "right"})
    assert not response["ok"] and response["error"]["code"] == "INVALID_METRIC_VALUE"
    assert response["error"]["details"]["task_id"] == side
    assert response["error"]["details"]["row"] == 0
    assert response["error"]["details"]["metric"] == "merit_function"


def test_comparison_rejects_overflow_of_finite_metric_difference(tmp_path):
    b, _ = fake_backend(tmp_path)
    for task_id, value in (("left", -1e308), ("right", 1e308)):
        b.tasks[task_id] = {"state": "succeeded", "result": {"rows": [{
            "conditions": {}, "metrics": [{"key": "value", "value": value, "unit": "mm"}]}]}}
    response = b.dispatch("compare_results", {"left_task_id": "left", "right_task_id": "right"})
    assert response["error"]["code"] == "INVALID_METRIC_VALUE"
    assert response["error"]["details"]["operation"] == "difference"
