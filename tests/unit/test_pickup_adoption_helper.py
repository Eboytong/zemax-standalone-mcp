"""Offline contracts for the pickup adoption helper (v3: strict layered acceptance).

The real helper is driven through a FakeBackend that speaks the same tool layer as production and
that keeps/restores checkpointed state, so rollback is exercised for real.  The fake proves the
*flow* only; it never proves native behaviour.  Coverage matches the review: missing restore,
forced/error/missing receipt, unexpected probe success still rolled back, and empty/mismatched ray
rows, plus the earlier five-moment / never-adopted / parameter-loss / error-recovery cases.
"""
import importlib.util
import json
import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from zemax_mcp.models import UpdateSurfaces

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "probes" / "ED-02" / "pickup_adoption_helper.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("pickup_adoption_helper", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


helper = load_helper()


@pytest.mark.parametrize('mode', ['Fixed', 'Automatic', 'SurfacePickup'])
def test_readback_preserves_mode_when_native_pickup_payload_is_null(mode):
    cell = SimpleNamespace(Solve=mode, Value=.2, IsActive=True, IsReadOnly=False,
                           GetSolveData=lambda: SimpleNamespace(Type=mode, _S_SurfacePickup=None))
    backend = SimpleNamespace(_row=lambda index: index, _cell=lambda row, name: cell)
    actual = helper.readback(backend, 2, 'chip_zone')
    assert actual['mode'] == actual['data_type'] == mode
    assert actual['pickup'] is None
    assert bool(actual['pickup_error']) == (mode == 'SurfacePickup')

SPEC = dict(item="ED-02.SurfacePickup.ChipZone", cell="chip_zone", column="ChipZone",
            source=0.5, target=0.2, source_after=0.7, scale=1.25, offset=0.05, source_surface=1)


class Name:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class FakePickup:
    def __init__(self, supports_scale=True, supports_offset=True):
        self.Surface = 0
        self.Column = Name("None")
        self.ScaleFactor = 1.0
        self.Offset = 0.0
        self.SupportsScale = supports_scale
        self.SupportsOffset = supports_offset
        self.IsPickupFromCurrentColumn = False


class FakeSolve:
    def __init__(self, pickup):
        self._S_SurfacePickup = pickup
        self.IsValid = True


class FakeSolveData:
    def __init__(self, cell):
        self.cell = cell

    @property
    def Type(self):
        return Name(self.cell.solve)

    @property
    def IsValid(self):
        return True

    @property
    def _S_SurfacePickup(self):
        return self.cell.pickup


class FakeCell:
    def __init__(self, name, solve="Automatic", value=0.0, supports_scale=True, supports_offset=True):
        self.name = name
        self.solve = solve
        self.value = value
        self.pickup = FakePickup(supports_scale, supports_offset)
        self.pending = None
        self.IsActive = True
        self.IsReadOnly = False

    def GetAvailableSolveTypes(self):
        return [Name("Fixed"), Name("SurfacePickup"), Name("Automatic")]

    @property
    def Solve(self):
        return Name(self.solve)

    @property
    def Value(self):
        return self.value

    def IsSolveTypeSupported(self, _enum):
        return True

    def GetSolveData(self):
        return FakeSolveData(self)

    def CreateSolveType(self, _enum):
        return FakeSolve(self.pickup)


class FakeBackend:
    def __init__(self, world="adopt_immediate", probe_reject=False, close="normal",
                 close_receipt=True, ray_world="ok", total_surfaces=3,
                 supports_scale=True, supports_offset=True):
        self.world = world
        self.probe_reject = probe_reject
        self.close = close
        self.close_receipt = close_receipt
        self.ray_world = ray_world
        self.total_surfaces = total_surfaces
        self.active = None
        self.revision = 0
        self.system_ready = False
        self.last_checkpoint = None
        self.calls = []
        self._states = {}
        self.cell = FakeCell("chip_zone", value=0.2, supports_scale=supports_scale,
                             supports_offset=supports_offset)
        self.source_cell = FakeCell("chip_zone", value=0.5)
        self.native = SimpleNamespace(
            enum=lambda *a: 42,
            api=SimpleNamespace(Editors=SimpleNamespace(
                SolveType=SimpleNamespace(SurfacePickup=1),
                LDE=SimpleNamespace(SurfaceColumn=object()))))
        self.system = SimpleNamespace(UpdateStatus=self._update_status)

    # -- state capture/restore (so checkpoint rollback is real) ---------
    def _capture(self):
        return {"solve": self.cell.solve, "value": self.cell.value,
                "source": self.source_cell.value,
                "surface": self.cell.pickup.Surface, "column": str(self.cell.pickup.Column),
                "scale": self.cell.pickup.ScaleFactor, "offset": self.cell.pickup.Offset}

    def _apply(self, state):
        self.cell.solve = state["solve"]
        self.cell.value = state["value"]
        self.source_cell.value = state["source"]
        self.cell.pickup.Surface = state["surface"]
        self.cell.pickup.Column = Name(state["column"])
        self.cell.pickup.ScaleFactor = state["scale"]
        self.cell.pickup.Offset = state["offset"]

    def _update_status(self):
        cell = self.cell
        if cell.pending is not None:
            cell.solve = cell.pending
            cell.pending = None
        if cell.solve == "SurfacePickup":
            cell.value = self.source_cell.value * cell.pickup.ScaleFactor + cell.pickup.Offset
        return "Update complete"

    def _apply_pickup(self, spec):
        cell = self.cell
        pickup = cell.pickup
        pickup.Surface = int(spec["source_surface"])
        pickup.Column = Name(spec.get("source_column") or spec.get("column", "ChipZone"))
        if pickup.SupportsScale:
            pickup.ScaleFactor = float(spec.get("scale", 1.0))
        if pickup.SupportsOffset:
            pickup.Offset = float(spec.get("offset", 0.0))
        if self.world == "adopt_after_update":
            cell.pending = "SurfacePickup"
        else:
            cell.solve = "SurfacePickup"
        cell.value = self.source_cell.value * pickup.ScaleFactor + pickup.Offset

    def _checkpoint(self):
        path = Path(os.environ["ZEMAX_STATE_DIR"]) / ("checkpoint_r%d.zos" % self.revision)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("checkpoint", encoding="utf-8")
        self._states[str(path)] = self._capture()
        self.last_checkpoint = str(path)
        return str(path)

    # -- tool layer -----------------------------------------------------
    def dispatch(self, name, args=None):
        args = args or {}
        self.calls.append({"tool": name, "arguments": args})
        handler = getattr(self, "_" + name, None)
        return handler(**args) if handler else {"ok": True, "data": {}}

    def _connect(self, **_):
        return {"ok": True, "data": {"connected": True}}

    def _new_system(self, **_):
        self.system_ready = True
        return {"ok": True, "data": {"mode": "Sequential"}}

    def _insert_surfaces(self, at=1, count=1, **_):
        return {"ok": True, "data": {"inserted_at": at, "count": count}}

    def _update_system_settings(self, settings=None, **_):
        return {"ok": True, "data": settings or {}}

    def _get_surfaces(self, **_):
        return {"ok": True, "data": {"total": self.total_surfaces}}

    def _save_lens_as(self, path, **_):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("saved", encoding="utf-8")
        return {"ok": True, "data": {"path": path}}

    def _open_lens(self, path, **_):
        name = Path(path).name
        if str(path) in self._states:
            self._apply(self._states[str(path)])
            if self.world == "dirty_restore":
                self.cell.value = 999.0  # deliberate restore corruption
        if self.world == "lose_scale_on_reload" and name == "reload-after_save_reload.zos":
            self.cell.pickup.ScaleFactor = 1.0
        return {"ok": True, "data": {"path": path}}

    def _run_batch_ray_trace(self, **_):
        return {"ok": True, "data": {"task_id": "trace1", "state": "succeeded"}}

    def _get_task_status(self, task_id, **_):
        return {"ok": True, "data": {"task_id": task_id, "state": "succeeded"}}

    def _rows(self):
        if self.ray_world == "error":
            return [{"index": 0, "state": "error", "error_code": 2, "vignette_code": 0, "position": None}]
        if self.ray_world == "empty":
            return []
        if self.ray_world == "mismatch":
            return [{"index": 5, "state": "succeeded", "error_code": 0, "vignette_code": 0,
                     "position": [0.0, 0.0, 1.0]}]
        if self.ray_world == "nan":
            return [{"index": 0, "state": "succeeded", "error_code": 0, "vignette_code": 0,
                     "position": [float("nan"), 0.0, 1.0]}]
        return [{"index": 0, "state": "succeeded", "error_code": 0, "vignette_code": 0,
                 "position": [0.0, 0.0, 1.0]}]

    def _get_task_result(self, task_id, **_):
        rows = self._rows()
        return {"ok": True, "data": {"rows": rows, "summary": {"requested": len(rows)}}}

    def _disconnect(self, **_):
        return {"ok": True, "data": {"connected": False}}

    def _update_surfaces(self, changes, **_):
        change = changes[0]
        solves = change.get("solves") or {}
        spec = solves.get("chip_zone") or solves.get("mechanical_semi_diameter") or None
        if spec is not None:
            if spec.get("source_surface") == change["surface"]:
                return {"ok": False, "error": {"code": "INVALID_SOLVE", "message": "禁止自引用 pickup。"}}
            self.revision += 1
            checkpoint = self._checkpoint()
            is_probe = "source_column" in spec
            fail = (self.world == "reject_native") or (is_probe and (self.probe_reject or self.world == "dirty_restore"))
            if fail:
                return {"ok": False, "error": {
                    "code": "PARTIAL_UPDATE", "message": "原生未采用",
                    "details": {"checkpoint": checkpoint, "failed_surface": change["surface"],
                                "completed_surfaces": [],
                                "cause": {"code": "SOLVE_UPDATE_FAILED",
                                          "details": {"requested": "SurfacePickup", "actual": "Automatic"}},
                                "failed_surface_state": {"surface": change["surface"]}}}}
            self._apply_pickup(spec)
            return {"ok": True, "data": {"surfaces": [change["surface"]]}}
        cell = self.cell
        value = change.get("chip_zone")
        if change["surface"] == 1:
            if value is not None:
                self.source_cell.value = float(value)
                if self.world == "revert_on_source_change" and cell.solve == "SurfacePickup":
                    cell.solve = "Automatic"
                elif cell.solve == "SurfacePickup":
                    cell.value = (self.source_cell.value * cell.pickup.ScaleFactor + cell.pickup.Offset)
            return {"ok": True, "data": {"surfaces": [1]}}
        if value is not None:
            cell.value = float(value)
        return {"ok": True, "data": {"surfaces": [change["surface"]]}}

    def _row(self, index):
        if not self.system_ready:
            raise RuntimeError("readback before new_system")
        return SimpleNamespace(SurfaceNumber=index)

    def _cell(self, row, name):
        return self.source_cell if row.SurfaceNumber == 1 else self.cell

    def shutdown(self):
        self.active = None
        if not self.close_receipt:
            return
        native = {"attempted": True, "closed": True, "error": None}
        receipt = {"forced": False, "native": native, "active_cancelled": False}
        if self.close == "forced":
            receipt["forced"] = True
        elif self.close == "error":
            native["error"] = "disconnect boom"
        elif self.close == "no_closed":
            native.pop("closed")
        elif self.close == "cancel_error":
            receipt["cancel_error"] = "cancel boom"
        path = Path(os.environ["ZEMAX_STATE_DIR"]) / "close_receipt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt), encoding="utf-8")


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("ZEMAX_STATE_DIR", str(tmp_path / "state"))
    return tmp_path


def run(env, world, **kwargs):
    backend = FakeBackend(world=world, **kwargs)
    return helper.run_case(backend, dict(SPEC), env / ("out-" + uuid.uuid4().hex), timeout_seconds=5), backend


def test_adoption_only_after_update_completes(env):
    record, _ = run(env, "adopt_after_update", probe_reject=True)
    case = record["case"]
    assert case["moments"]["immediate"]["target"]["adopted"] is False
    assert case["moments"]["after_update_status"]["target"]["adopted"] is True
    assert case["adoption_passed"] is True
    assert case["complete"] is True, case["incomplete_reasons"]


def test_adoption_confirmed_but_recovery_not_exercised_blocks(env):
    record, _ = run(env, "adopt_immediate")  # probe succeeds -> no repeatable native failure
    case = record["case"]
    assert case["adoption_passed"] is True
    assert case["failure"]["native_partial"]["available"] is False
    # the unexpected success is still rolled back to the pre-experiment checkpoint
    assert case["failure"]["native_partial"]["temporary_change_restored"] is True
    assert "failure_recovery_not_exercised" in case["incomplete_reasons"]
    assert case["complete"] is False


def test_never_adopted_keeps_true_rejection(env):
    record, _ = run(env, "reject_native")
    case = record["case"]
    assert case["adoption_passed"] is False
    assert "adoption_unconfirmed" in case["incomplete_reasons"]
    assert case["adopted_at"] == []
    native = case["failure"]["native_partial"]
    assert native["source"] == "main_request" and native["available"] is True
    assert native["failure"]["stage"] == "native_partial_failure"
    assert native["failure"]["cause"]["details"]["actual"] == "Automatic"
    assert native["restore"]["clean"] is True


def test_revert_after_source_change_blocks_admission(env):
    record, _ = run(env, "revert_on_source_change", probe_reject=True)
    case = record["case"]
    assert case["moments"]["immediate"]["target"]["adopted"] is True
    assert case["moments"]["after_source_change"]["target"]["adopted"] is False
    assert case["adoption_passed"] is False
    assert "after_source_change:not_adopted(Automatic)" in case["adoption"]["reasons"]
    assert case["complete"] is False


def test_parameter_loss_across_reload_is_a_field_change(env):
    record, _ = run(env, "lose_scale_on_reload", probe_reject=True)
    case = record["case"]
    assert case["save_reload_diff"]["clean"] is False
    assert "pickup.scale" in {c["field"] for c in case["save_reload_diff"]["changes"]}
    assert "after_save_reload:diff_not_clean" in case["incomplete_reasons"]


def test_self_pickup_precheck_is_no_write(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True)
    precheck = record["case"]["failure"]["precheck"]
    assert precheck["stage"] == "precheck_no_write"
    assert precheck["wrote_model"] is False and precheck["checkpoint"] is None
    assert precheck["code"] == "INVALID_SOLVE"
    assert "precheck_not_no_write" not in record["case"]["incomplete_reasons"]


def test_success_path_constructs_reachable_failure_and_restores(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True)
    case = record["case"]
    native = case["failure"]["native_partial"]
    assert native["source"] == "constructed_probe" and native["available"] is True
    assert native["restore"]["clean"] is True, native["restore"]["changes"]
    assert native["temporary_change_restored"] is True
    assert case["complete"] is True, case["incomplete_reasons"]


def test_missing_restore_blocks_completion(env):
    record, _ = run(env, "dirty_restore")
    case = record["case"]
    native = case["failure"]["native_partial"]
    assert native["available"] is True
    assert native["restore"]["clean"] is False
    assert "failure_restore_not_clean" in case["incomplete_reasons"]
    assert case["complete"] is False


def test_unsupported_parameters_are_none_not_zero(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True, supports_scale=False, supports_offset=False)
    case = record["case"]
    assert case["capabilities"]["supports_scale"] is False
    assert case["expected"]["scale"] == 1.0 and case["expected"]["offset"] == 0.0
    reading = case["moments"]["after_source_change"]["target"]
    assert reading["pickup"]["scale"] is None and reading["pickup"]["offset"] is None
    assert case["complete"] is True, case["incomplete_reasons"]


@pytest.mark.parametrize("ray_world,reason", [
    ("error", "row_error"), ("empty", "rows_missing"),
    ("mismatch", "rows_index_mismatch"), ("nan", "row_position_invalid")])
def test_bad_ray_rows_block_completion(env, ray_world, reason):
    record, _ = run(env, "adopt_immediate", probe_reject=True, ray_world=ray_world)
    case = record["case"]
    assert case["adoption_passed"] is True
    assert case["ray_trace"]["all_succeeded"] is False
    assert reason in case["ray_trace"]["reasons"]
    assert "ray_not_all_succeeded" in case["incomplete_reasons"]
    assert case["complete"] is False


@pytest.mark.parametrize("close,reason", [
    ("missing", "close_receipt_missing"), ("forced", "forced_not_false"),
    ("error", "native_error"), ("no_closed", "native_closed_not_true"),
    ("cancel_error", "cancel_error")])
def test_close_variants_block_completion(env, close, reason):
    kwargs = dict(probe_reject=True)
    if close == "missing":
        kwargs["close_receipt"] = False
    else:
        kwargs["close"] = close
    record, _ = run(env, "adopt_immediate", **kwargs)
    case = record["case"]
    assert case["lifecycle"]["closed_confirmed"] is False
    assert reason in case["lifecycle"]["reason"]
    assert "close_not_confirmed" in case["incomplete_reasons"]
    assert case["complete"] is False


def test_active_task_after_shutdown_blocks(env):
    backend = FakeBackend(world="adopt_immediate", probe_reject=True)
    backend.active = SimpleNamespace(task_id="still-running")
    backend.shutdown = lambda: None  # leaves the task active
    record = helper.run_case(backend, dict(SPEC), env / ("out-" + uuid.uuid4().hex), timeout_seconds=5)
    case = record["case"]
    assert case["lifecycle"]["active_task_after_shutdown"] is True
    assert "native_task_still_active" in case["lifecycle"]["reason"]
    assert case["complete"] is False


def test_two_save_reload_use_distinct_files(env):
    record, backend = run(env, "adopt_immediate", probe_reject=True)
    reload_paths = [Path(c["arguments"]["path"]).name for c in backend.calls
                    if c["tool"] == "save_lens_as" and Path(c["arguments"]["path"]).name.startswith("reload-")]
    assert len(reload_paths) == 2 and len(set(reload_paths)) == 2
    for label in ("after_save_reload", "after_save_reload_post_linkage"):
        assert (record["case"]["moments"][label].get("target") or {}).get("adopted") is True
        assert record["case"]["moments"][label].get("diff") is not None


def test_capability_probe_runs_after_the_model_exists(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True)
    assert record["case"]["capabilities"]["supports_scale"] is True
    assert "error" not in record


def test_cli_creates_output_dir_once(monkeypatch, tmp_path):
    import zemax_mcp.backend as backend_mod
    import zemax_mcp.config as config_mod

    def factory(*_args, **_kwargs):
        return FakeBackend(world="adopt_immediate", probe_reject=True)

    class FakeConfig:
        def __init__(self, install_dir, native):
            self.install_dir = install_dir
            self.native = native

        @classmethod
        def from_env(cls):
            return SimpleNamespace(install_dir=str(tmp_path))

    monkeypatch.setattr(backend_mod, "Backend", factory)
    monkeypatch.setattr(config_mod, "Config", FakeConfig)
    monkeypatch.setenv("ZEMAX_STATE_DIR", str(tmp_path / "state"))
    out = tmp_path / "cli-out"
    record = helper.main(["--cell", "chip_zone", "--out", str(out)])
    assert out.is_dir() and (out / "anchors.json").is_file()
    assert record["case"]["complete"] is True, record["case"]["incomplete_reasons"]


def test_recorded_request_matches_the_real_request_model(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True)
    payload = record["case"]["request"]["arguments"]
    solve = UpdateSurfaces(changes=payload["changes"]).changes[0].solves["chip_zone"]
    assert solve.mode == "surface_pickup" and solve.source_surface == 1
    assert solve.scale == pytest.approx(1.25) and solve.offset == pytest.approx(0.05)


def test_three_way_readback_fields(env):
    record, _ = run(env, "adopt_immediate", probe_reject=True)
    reading = record["case"]["moments"]["after_save_reload"]["target"]
    assert reading["mode"] == reading["data_type"] == "SurfacePickup"
    assert reading["pickup"]["column"] == "ChipZone"
    assert reading["pickup_error"] is None
