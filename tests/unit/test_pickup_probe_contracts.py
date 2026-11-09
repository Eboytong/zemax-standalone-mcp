"""Offline contracts for the ED-02 C2/C3 pickup-adoption probe.

The probe must be able to tell "the native cell never adopts SurfacePickup" from "it adopts
only after an update".  These tests drive the real probe through a FakeBackend in both
worlds, so the distinction is exercised without a native instance.
"""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from zemax_mcp.models import BatchRays, COMMAND_MODELS

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "probes" / "ED-02" / "pickup_solve_adoption018.py"


def load_probe():
    spec = importlib.util.spec_from_file_location("pickup_solve_adoption018", PROBE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Name:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class FakePickup:
    def __init__(self):
        self.Surface = 0
        self.Column = Name("None")
        self.ScaleFactor = 1.0
        self.Offset = 0.0
        self.SupportsScale = True
        self.SupportsOffset = True
        self.IsPickupFromCurrentColumn = False

    def MakePickupFromCurrentColumn(self):
        self.IsPickupFromCurrentColumn = True


class FakeSolve:
    def __init__(self):
        self._S_SurfacePickup = FakePickup()
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
    """Cell that either never adopts, or adopts only after UpdateStatus()."""

    def __init__(self, name, solve, adopts_after_update):
        self.name = name
        self.solve = solve
        self.adopts_after_update = adopts_after_update
        self.pending = False
        self.IsActive = True
        self.IsReadOnly = False
        self.Value = 0.2 if name == "chip_zone" else 5.2
        self.pickup = FakePickup()
        self.set_calls = 0

    def GetAvailableSolveTypes(self):
        return [Name("Fixed"), Name("SurfacePickup"), Name("ZPLMacro"), Name("Automatic")]

    @property
    def Solve(self):
        return Name(self.solve)

    def IsSolveTypeSupported(self, _enum):
        return True

    def GetSolveData(self):
        return FakeSolveData(self)

    def CreateSolveType(self, _enum):
        return FakeSolve()

    def SetSolveData(self, _solve):
        self.set_calls += 1
        self.pending = True
        return Name("Success")

    def MakeSolveFixed(self):
        self.solve = "Fixed"


class FakeBackend:
    def __init__(self, adopts_after_update, total_surfaces=3):
        self.active = None
        self.adopts_after_update = adopts_after_update
        self.total_surfaces = total_surfaces
        self.trace_calls = []
        self.cells = {
            (1, "chip_zone"): FakeCell("chip_zone", "Automatic", adopts_after_update),
            (2, "chip_zone"): FakeCell("chip_zone", "Automatic", adopts_after_update),
            (1, "mechanical_semi_diameter"): FakeCell("mechanical_semi_diameter", "Fixed", adopts_after_update),
            (2, "mechanical_semi_diameter"): FakeCell("mechanical_semi_diameter", "Fixed", adopts_after_update),
        }
        self.native = SimpleNamespace(
            enum=lambda *a: 42,
            api=SimpleNamespace(
                Editors=SimpleNamespace(SolveType=SimpleNamespace(SurfacePickup=1),
                                        LDE=SimpleNamespace(SurfaceColumn=object()))))
        self.system = SimpleNamespace(UpdateStatus=self._update_status)

    def _update_status(self):
        for cell in self.cells.values():
            if self.adopts_after_update and cell.pending:
                cell.solve = "SurfacePickup"
                cell.pending = False
        return "Update complete"

    def _row(self, index):
        return SimpleNamespace(SurfaceNumber=index)

    def _cell(self, row, name):
        return self.cells[(row.SurfaceNumber, name)]

    def dispatch(self, name, args):
        COMMAND_MODELS[name].model_validate(args or {})
        handler = getattr(self, "_" + name, None)
        return dict(ok=True, data=handler(**(args or {})) if handler else {})

    def _run_batch_ray_trace(self, **_kwargs):
        self.trace_calls.append(_kwargs)
        return dict(task_id="trace1", state="succeeded")

    def _get_surfaces(self, **_kwargs):
        return dict(total=self.total_surfaces,
                    surfaces=[dict(surface=i, is_image=(i == self.total_surfaces - 1))
                              for i in range(self.total_surfaces)])

    def _get_task_status(self, task_id):
        return dict(task_id=task_id, state="succeeded")

    def _get_task_result(self, task_id, **_kwargs):
        return dict(rows=[], series=[], grids=[], artifacts=[])

    def shutdown(self):
        self.active = None
        receipt = Path(os.environ["ZEMAX_STATE_DIR"]) / "close_receipt.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(dict(native=dict(closed=True))), encoding="utf-8")


@pytest.fixture
def env(monkeypatch, tmp_path):
    saved = {k: os.environ.get(k) for k in ("ZEMAX_STATE_DIR", "ZEMAX_OUTPUT_DIR")}
    monkeypatch.setattr("zemax_mcp.config.Config.from_env",
                        classmethod(lambda cls: SimpleNamespace(install_dir=tmp_path)))
    yield tmp_path
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_probe(monkeypatch, folder, fake):
    module = load_probe()
    monkeypatch.setattr(module, "Backend", lambda *a, **k: fake)
    return module.run(str(folder))


def test_probe_reports_never_adopted(env, monkeypatch, tmp_path):
    record = run_probe(monkeypatch, tmp_path / "out", FakeBackend(adopts_after_update=False))
    assert record["closed"] is True
    assert "error" not in record
    for case in record["cases"]:
        assert case["adopted"] is False
        assert case["first_adoption_step"] is None
        step = case["steps"][0]
        assert step["set_status"] == "Success"          # native said Success ...
        assert step["immediate"]["adopted"] is False    # ... but did not adopt
        assert step["adopted_at"] == []
        # every readback moment was checked, including the reload
        for label in ("immediate", "after_update_status", "after_ray_trace", "after_save_reload"):
            assert label in step
            assert step[label]["adopted"] is False
        # C3 runs only when C2 never adopted
        assert [v["bind"] for v in case["variants"]] == [
            "make_pickup_from_current_column", "make_solve_fixed_first"]
        assert all(v["adopted_at"] == [] for v in case["variants"])


def test_probe_distinguishes_adoption_after_update(env, monkeypatch, tmp_path):
    record = run_probe(monkeypatch, tmp_path / "out", FakeBackend(adopts_after_update=True))
    assert record["closed"] is True
    for case in record["cases"]:
        assert case["adopted"] is True
        assert case["first_adoption_step"] == "after_update_status"
        step = case["steps"][0]
        assert step["immediate"]["adopted"] is False
        assert step["after_update_status"]["adopted"] is True
        assert step["after_update_status"]["cell_solve"] == "SurfacePickup"
        assert step["after_update_status"]["solve_data_type"] == "SurfacePickup"
        assert case["variants"] == []  # C3 skipped once C2 adopted


def test_probe_records_three_way_readback_and_activity(env, monkeypatch, tmp_path):
    record = run_probe(monkeypatch, tmp_path / "out", FakeBackend(adopts_after_update=False))
    step = record["cases"][0]["steps"][0]
    reading = step["immediate"]
    assert reading["cell_solve"] == "Automatic"
    assert reading["solve_data_type"] == "Automatic"
    assert reading["is_active"] is True
    assert reading["is_read_only"] is False
    assert reading["value"] == 0.2
    assert step["supported"] == ["Fixed", "SurfacePickup", "ZPLMacro", "Automatic"]
    assert step["is_solve_type_supported"] is True
    assert step["solve_valid"] is True


def test_probe_covers_both_cells(env, monkeypatch, tmp_path):
    record = run_probe(monkeypatch, tmp_path / "out", FakeBackend(adopts_after_update=False))
    assert [c["cell"] for c in record["cases"]] == ["chip_zone", "mechanical_semi_diameter"]
    mech = record["cases"][1]
    assert mech["before"]["target"]["cell_solve"] == "Fixed"


def test_probe_keeps_cleanup_and_error_separate(env, monkeypatch, tmp_path):
    fake = FakeBackend(adopts_after_update=False)

    def boom():
        raise RuntimeError("simulated shutdown failure")

    fake.shutdown = boom
    folder = tmp_path / "out"
    record = run_probe(monkeypatch, folder, fake)
    assert record["closed"] is True
    assert record["cleanup_error"]["type"] == "RuntimeError"
    saved = json.loads((folder / "anchors.json").read_text(encoding="utf-8"))
    assert saved["cleanup_error"]["message"] == "simulated shutdown failure"
    assert "error" not in saved


def test_probe_traces_to_image_surface_not_surface_one(env, monkeypatch, tmp_path):
    """insert_surfaces changes the layout, so the target must come from get_surfaces.total."""
    fake = FakeBackend(adopts_after_update=False, total_surfaces=3)
    record = run_probe(monkeypatch, tmp_path / "out", fake)
    layout = record["surface_layout"]
    assert layout["total"] == 3
    assert layout["image_surface"] == 2
    assert layout["target_surface"] == 2
    assert layout["target_reaches_pickup"] is True
    # every trace must have aimed past the pickup cell on surface 2
    assert fake.trace_calls
    assert {call["target_surface"] for call in fake.trace_calls} == {2}
    assert all(call["start_surface"] == 0 for call in fake.trace_calls)
    for case in record["cases"]:
        assert case["ray_trace"]["target_surface"] == 2
        assert case["ray_trace"]["reaches_pickup"] is True


def test_probe_refuses_layout_without_room_for_pickup(env, monkeypatch, tmp_path):
    fake = FakeBackend(adopts_after_update=False, total_surfaces=2)
    folder = tmp_path / "out"
    with pytest.raises(RuntimeError):
        run_probe(monkeypatch, folder, fake)
    saved = json.loads((folder / "anchors.json").read_text(encoding="utf-8"))
    assert saved["surface_layout"]["target_reaches_pickup"] is False
    assert saved["error"]["type"] == "RuntimeError"
    assert fake.trace_calls == []


def test_batch_rays_target_surface_contract():
    """The real request model accepts the layout-derived target."""
    request = BatchRays(input_mode="Normalized", start_surface=0, target_surface=2,
                        rays=[dict(hx=0, hy=0, px=0, py=0, wavelength=1)])
    assert request.target_surface == 2
    assert request.input_mode == "Normalized"


def test_probe_marks_scope_as_mode_adoption_only(env, monkeypatch, tmp_path):
    record = run_probe(monkeypatch, tmp_path / "out", FakeBackend(adopts_after_update=True))
    scope = record["acceptance_scope"]
    assert scope["mode_adoption"] is True
    assert scope["value_linkage"] is False
    assert scope["full_save_reload"] is False
    for case in record["cases"]:
        assert case["linkage_checked"] is False
        assert "not verified" in case["save_reload_scope"]
