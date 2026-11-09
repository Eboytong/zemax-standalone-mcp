"""Offline contracts for the CV-02 power-map probes.

These tests import the real request models and the real result-paging method, then drive
both probe scripts through a FakeBackend so the failure paths are exercised without a
native instance.  They exist because compile/import checks cannot catch a wrong request
mode, a stripped grid, a missing EFL value or a failed ray.

Covered:
  * `RunAnalysis` / `BatchRays` model validation (including the Direct-vs-Normalized trap);
  * the zero field-normalisation precondition in the real `run_power_map`;
  * `Backend._page_task_result` both ways: default metadata (no values) and region paging;
  * probe reads through the JSON artifact and through the grid page;
  * EFL missing and a failed ray row inside E3.
"""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import BatchRays, TaskResult, COMMAND_MODELS
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.power_maps import PowerFieldMap, run_power_map

ROOT = Path(__file__).resolve().parents[2]
PROBES = ROOT / "scripts" / "probes" / "CV-02"


def load_probe(filename):
    path = PROBES / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def power_result(nx=3, ny=3, value=6.814355276657183, with_artifact=None):
    """Full task payload shaped like run_power_map's own output."""
    rows = []
    values, mask = [], []
    for iy in range(ny):
        values.append([value] * nx)
        mask.append([True] * nx)
        for ix in range(nx):
            rows.append(dict(index=len(rows), grid_x=ix, grid_y=iy, x=ix, y=iy,
                             state="native_value", raw_value=value, value=value,
                             native_query_status="returned_finite_value",
                             raw_value_state="finite_nonzero",
                             native_ring_validity="unavailable"))
    result = dict(
        rows=rows, series=[],
        grids=[dict(grid=0, nx=nx, ny=ny, min_x=-1, min_y=-1, dx=1, dy=1,
                    x=[-1, 0, 1], y=[-1, 0, 1], x_label="Field X", y_label="Field Y",
                    x_unit="degrees", y_unit="degrees", value_unit="diopters",
                    values=values, valid_mask=mask, invalid_count=0,
                    valid_mask_scope="central reference ray passed",
                    native_ring_validity="unavailable")],
        artifacts=[])
    if with_artifact is not None:
        Path(with_artifact).write_text(json.dumps(result), encoding="utf-8")
        result["artifacts"] = [dict(kind="json", path=str(with_artifact))]
    return result


class ReachedComposite(Exception):
    """Sentinel: run_power_map passed every precondition and reached the job builder."""


class StubBackend:
    """Just enough backend for the real run_power_map precondition path."""

    def __init__(self, fields, normalization="Rectangular"):
        self.fields = fields
        self.normalization = normalization
        self.native = SimpleNamespace(
            enum=lambda *a: 42,
            api=SimpleNamespace(Editors=SimpleNamespace(
                MFE=SimpleNamespace(MeritOperandType=object()))))

    def _require_sequential(self):
        return None

    def _require_work(self):
        return None

    def _row(self, index):
        return SimpleNamespace(SurfaceNumber=index)

    def get_system_settings(self, _request):
        return dict(fields=self.fields, field_type="Angle", field_normalization=self.normalization,
                    lens_units="mm", wavelengths=[dict(wavelength_um=0.5875618)])

    def _composite(self, *args):
        raise ReachedComposite


class FakeBackend:
    """Executes the probes' paths; result paging is the real Backend method."""

    def __init__(self, *_args, **_kwargs):
        self.active = None
        self.radius = 50
        self.aperture = dict(type="None")
        self.artifact_dir = None
        self.operand_calls = []
        self.native = SimpleNamespace(
            enum=lambda *a: 42,
            api=SimpleNamespace(Editors=SimpleNamespace(
                MFE=SimpleNamespace(MeritOperandType=object()))))
        self.system = SimpleNamespace(MFE=SimpleNamespace(GetOperandValue=self._operand))
        self.tasks = {}

    def _operand(self, code, *args):
        self.operand_calls.append(args)
        data, px = args[6], args[4]
        if data == 9.0 and px == -0.2:
            raise RuntimeError("simulated native query failure")
        if data == 9.0 and px == 0.2:
            return float("nan")
        return 146.7490260488084 if data == 9.0 else 6.814355276657183

    def dispatch(self, name, args):
        args = args or {}
        COMMAND_MODELS[name].model_validate(args)
        handler = getattr(self, "_" + name, None)
        if handler is None:
            return dict(ok=True, data={})
        return dict(ok=True, data=handler(**args))

    def _run_analysis(self, request):
        task_id = f"task{len(self.tasks)}"
        artifact = None
        if self.artifact_dir is not None:
            artifact = Path(self.artifact_dir) / f"{task_id}.json"
            artifact.parent.mkdir(parents=True, exist_ok=True)
        self.tasks[task_id] = power_result(with_artifact=artifact)
        return dict(task_id=task_id, state="succeeded")

    def _run_batch_ray_trace(self, **_kwargs):
        rows = []
        for px in (-1.0, -.6, -.2, 0.0, .2, .6, 1.0):
            failed = px == -1.0
            rows.append(dict(error_code=1 if failed else 0, vignette_code=0,
                             position=None if failed else [0.0, 0.0, 1.0],
                             direction=None if failed else [0.0, 0.0, 1.0],
                             surface_normal=[0.0, 0.0, -1.0]))
        task_id = f"task{len(self.tasks)}"
        self.tasks[task_id] = dict(rows=rows, series=[], grids=[], artifacts=[])
        return dict(task_id=task_id, state="succeeded")

    def _get_task_status(self, task_id):
        return dict(task_id=task_id, state="succeeded")

    def _get_task_result(self, task_id, **page):
        full = self.tasks[task_id]
        req = TaskResult(task_id=task_id, **page)
        return Backend._page_task_result(None, full, req)

    def _update_surfaces(self, changes):
        for change in changes:
            if change.get("radius") is not None:
                self.radius = change["radius"]
            if change.get("aperture") is not None:
                self.aperture = change["aperture"]
        return {}

    def _get_surfaces(self, **_kwargs):
        return dict(surfaces=[dict(surface=1, cells=dict(radius=dict(value=self.radius)),
                                   properties=dict(aperture=self.aperture))])

    def _get_system_settings(self, **_kwargs):
        return dict(fields=[dict(x=0, y=0), dict(x=2, y=2)], field_type="Angle",
                    field_normalization="Rectangular", lens_units="mm",
                    wavelengths=[dict(wavelength_um=0.5875618)])

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


def run_probe(module, monkeypatch, folder, fake):
    monkeypatch.setattr(module, "Backend", lambda *a, **k: fake)
    return module.run(str(folder))


# ---------------------------------------------------------------- request models

def test_run_analysis_accepts_power_field_map():
    request = RunAnalysis(request=dict(kind="power_field_map", surface=1, x_field_width=2,
                                       y_field_width=2, x_points=3, y_points=3))
    assert request.request.kind == "power_field_map"


def test_power_field_map_requires_positive_widths():
    with pytest.raises(ValidationError):
        PowerFieldMap(kind="power_field_map", surface=1, x_field_width=0, y_field_width=2)


def test_batch_rays_direct_mode_rejects_normalized_fields():
    """The pre-fix E3 request: Direct mode with hx/hy/px/py must be rejected."""
    with pytest.raises(ValidationError):
        BatchRays(input_mode="Direct", target_surface=1,
                  rays=[dict(hx=0, hy=0, px=0.5, py=0.0, wavelength=1)])


def test_batch_rays_normalized_mode_accepts_probe_rays():
    request = BatchRays(input_mode="Normalized", start_surface=0, target_surface=1,
                        rays=[dict(hx=0, hy=0, px=px, py=0.0, wavelength=1) for px in (-1.0, 0.0, 1.0)])
    assert len(request.rays) == 3


def test_zero_field_scale_is_rejected_by_real_run_power_map():
    """fields=[(0,0)] has zero normalisation scale; the product rejects it."""
    query = PowerFieldMap(kind="power_field_map", surface=1, x_field_width=2, y_field_width=2,
                          x_points=3, y_points=3)
    with pytest.raises(ZemaxError) as caught:
        run_power_map(StubBackend([dict(x=0, y=0)]), query)
    assert caught.value.code == "PRECONDITION_FAILED"
    assert caught.value.details["x_scale"] == 0 and caught.value.details["y_scale"] == 0


def test_off_axis_field_passes_the_precondition():
    query = PowerFieldMap(kind="power_field_map", surface=1, x_field_width=2, y_field_width=2,
                          x_points=3, y_points=3)
    with pytest.raises(ReachedComposite):
        run_power_map(StubBackend([dict(x=0, y=0), dict(x=2, y=2)]), query)


def test_scan_wider_than_field_extent_is_rejected():
    query = PowerFieldMap(kind="power_field_map", surface=1, x_field_width=8, y_field_width=8,
                          x_points=3, y_points=3)
    with pytest.raises(ZemaxError) as caught:
        run_power_map(StubBackend([dict(x=0, y=0), dict(x=2, y=2)]), query)
    assert caught.value.code == "INVALID_ARGUMENT"


# ------------------------------------------------------- real paging contract

def test_default_paging_strips_grid_values():
    full = power_result()
    paged = Backend._page_task_result(None, full, TaskResult(task_id="t"))
    assert paged["grid_data_in_artifacts"] is True
    assert "values" not in paged["grids"][0]
    with pytest.raises(KeyError):
        paged["grids"][0]["values"]


def test_region_paging_returns_single_centre_value():
    paged = Backend._page_task_result(None, power_result(), TaskResult(
        task_id="t", grid=0, x_start=1, y_start=1, width=1, height=1))
    assert "grids" not in paged
    assert paged["grid"]["values"] == [[6.814355276657183]]
    assert paged["grid"]["x_start"] == 1 and paged["grid"]["y_start"] == 1
    assert paged["grid"]["next_x"] == 2 and paged["grid"]["next_y"] == 2


def test_grid_index_out_of_range_is_explicit():
    with pytest.raises(ZemaxError) as caught:
        Backend._page_task_result(None, power_result(), TaskResult(task_id="t", grid=3))
    assert caught.value.code == "INDEX_OUT_OF_RANGE"


# --------------------------------------------------------------- E2 probe run

def test_e2_probe_reads_full_artifact(env, monkeypatch, tmp_path):
    probe = load_probe("power_radius_sweep018.py")
    fake = FakeBackend()
    fake.artifact_dir = tmp_path
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    assert record["closed"] is True
    assert record.get("cleanup_error") is None and "error" not in record
    assert record["settings_readback"]["fields"] == [dict(x=0, y=0), dict(x=2, y=2)]
    assert record["settings_readback"]["fields_match_request"] is True
    case = record["cases"][0]
    assert case["pupil_power"]["result_source"] == "artifact_json"
    assert case["pupil_power"]["grid_center"] == 6.814355276657183
    assert case["pupil_power"]["grid_center_matches_row"] is True
    assert case["gate_power"]["passed"] is True


def test_e2_probe_falls_back_to_grid_page(env, monkeypatch, tmp_path):
    probe = load_probe("power_radius_sweep018.py")
    fake = FakeBackend()  # no artifact -> default paging strips values
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    assert record["closed"] is True
    case = record["cases"][0]
    assert case["pupil_power"]["result_source"] == "paged_inline+grid_page"
    assert case["pupil_power"]["grid_center"] == 6.814355276657183
    assert case["pupil_efl"]["result_source"] == "paged_inline+grid_page"


def test_e2_probe_uses_four_radii_and_records_close_receipt(env, monkeypatch, tmp_path):
    probe = load_probe("power_radius_sweep018.py")
    fake = FakeBackend()
    fake.artifact_dir = tmp_path
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    assert [c["radius_mm"] for c in record["cases"]] == [50, 1e3, 1e6, 1e9]
    assert record["active_task_after_shutdown"] is False
    assert record["close_receipt"]["exists"] is True
    assert record["close_receipt"]["content"]["native"]["closed"] is True


# --------------------------------------------------------------- E3 probe run

def test_e3_probe_records_unavailable_efl_and_failed_ray(env, monkeypatch, tmp_path):
    probe = load_probe("power_asymmetric_aperture018.py")
    fake = FakeBackend()
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    assert record["closed"] is True
    assert "error" not in record
    base = record["cases"][0]
    assert base["id"] == "base" and base["aperture_readback"]["type"] == "CircularAperture"
    assert base["aperture_readback"]["maximum_radius"] == 8
    # a failed ray has no coordinates: the mapping must be reported, not raised
    failed = next(m for m in base["mapping"] if m["px"] == -1.0)
    assert failed["evaluable"] is False
    assert failed["reason"] == "trace_coordinates_missing"
    assert failed["case"]["error_code"] == 1
    assert base["mapping_evaluable"] is False
    assert base["mapping_unchanged"] is False
    # the healthy points stay evaluable
    assert sum(m["evaluable"] for m in base["mapping"]) == 6


def test_e3_probe_keeps_missing_efl_as_state_not_exception(env, monkeypatch, tmp_path):
    probe = load_probe("power_asymmetric_aperture018.py")
    fake = FakeBackend()
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    case = record["cases"][1]
    deltas = {d["px"]: d for d in case["versus_baseline"]}
    broken = deltas[-0.2]["efl"]
    assert broken["available"] is False
    assert broken["delta"] is None
    assert broken["case_state"] == "native_query_failed"
    nonfinite = deltas[0.2]["efl"]
    assert nonfinite["available"] is False and nonfinite["case_state"] == "non_finite"
    assert deltas[0.0]["efl"]["available"] is True
    assert deltas[0.0]["power"]["available"] is True


def test_e3_probe_reads_aperture_from_properties(env, monkeypatch, tmp_path):
    probe = load_probe("power_asymmetric_aperture018.py")
    fake = FakeBackend()
    record = run_probe(probe, monkeypatch, tmp_path / "out", fake)
    clipped = record["cases"][3]
    assert clipped["aperture_readback"]["type"] == "CircularAperture"
    assert clipped["aperture_readback"]["x_decenter"] == 3.0
    assert record["active_task_after_shutdown"] is False


def test_e3_probe_writes_anchors_with_probe_metadata(env, monkeypatch, tmp_path):
    probe = load_probe("power_asymmetric_aperture018.py")
    fake = FakeBackend()
    folder = tmp_path / "out"
    run_probe(probe, monkeypatch, folder, fake)
    saved = json.loads((folder / "anchors.json").read_text(encoding="utf-8"))
    assert saved["evidence_only"] is True
    assert saved["single_variable"] == "surface aperture decenter"
    assert [c["id"] for c in saved["cases"]] == ["base", "sym_r4", "dec_1p5", "dec_3p0"]


@pytest.mark.parametrize('filename', ['power_radius_sweep018.py', 'power_asymmetric_aperture018.py'])
def test_power_probes_record_flat_backend_settings(env, monkeypatch, tmp_path, filename):
    probe = load_probe(filename)
    fake = FakeBackend()
    fake.artifact_dir = tmp_path
    record = run_probe(probe, monkeypatch, tmp_path / 'out', fake)
    settings = next(c for c in record['calls'] if c['tool'] == 'update_system_settings')
    assert settings['backend_arguments'] == settings['arguments']['settings']
    assert 'settings' not in settings['backend_arguments']


@pytest.mark.parametrize('difference,changed', [(1e-14,False), (.1,True)])
def test_e3_distinguishes_floating_noise_from_reference_scale_change(difference, changed):
    probe = load_probe('power_asymmetric_aperture018.py')
    diagnostic = probe.change_diagnostics([dict(
        power=dict(available=True, base_raw=6.8, delta=difference),
        efl=dict(available=False, base_raw=None, delta=None))])
    assert diagnostic['power']['changed_above_reference_tolerance'] is changed
    assert diagnostic['power']['max_abs_delta'] == difference
    assert diagnostic['efl']['comparable_count'] == 0
    assert diagnostic['efl']['max_abs_delta'] is None
