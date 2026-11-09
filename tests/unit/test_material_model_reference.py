"""Line attribution and boundary behaviour of the material solve references."""
import asyncio
import math

import pytest
from pydantic import ValidationError

from tests.support.material_reference import (
    CLASSIC_LINES, PHYSICAL_LINES, abbe, abbe_from_wavelengths, line_positions,
    snell_indices, snell_indices_from_rows, snell_rays, snell_request,
)
from zemax_mcp.models import BatchRays

# The six wavelengths used by the model-solve checks: physical and classic lines interleaved.
SIX = [.5875618, .5876, .4861327, .4861, .6562725, .6563]


def test_documented_and_classic_line_sets_stay_separate():
    assert PHYSICAL_LINES == dict(d=.5875618, F=.4861327, C=.6562725)
    assert CLASSIC_LINES == dict(d=.5876, F=.4861, C=.6563)
    for name in ("d", "F", "C"):
        assert PHYSICAL_LINES[name] != CLASSIC_LINES[name]


def test_existing_six_wavelength_list_maps_to_the_classic_lines():
    # The current checks read model[1::2], i.e. positions 1/3/5 of the six-wavelength list.
    assert line_positions(SIX, CLASSIC_LINES) == dict(d=1, F=3, C=5)
    assert line_positions(SIX, PHYSICAL_LINES) == dict(d=0, F=2, C=4)


def test_abbe_from_wavelengths_uses_the_selected_line_set():
    indices = [1.6000, 1.6001, 1.6069, 1.6070, 1.5969, 1.5970]
    assert abbe_from_wavelengths(indices, SIX, CLASSIC_LINES) == abbe((1.6001, 1.6070, 1.5970))
    assert abbe_from_wavelengths(indices, SIX, PHYSICAL_LINES) == abbe((1.6000, 1.6069, 1.5969))
    assert abbe_from_wavelengths(indices, SIX, CLASSIC_LINES) != abbe_from_wavelengths(indices, SIX, PHYSICAL_LINES)


@pytest.mark.parametrize("wavelengths", [[.5876, .4861], [.5876, .5876, .4861, .6563]])
def test_line_positions_reject_missing_or_duplicate_lines(wavelengths):
    with pytest.raises(ValueError):
        line_positions(wavelengths, CLASSIC_LINES)


def test_abbe_rejects_zero_dispersion():
    with pytest.raises(ZeroDivisionError):
        abbe((1.6, 1.6, 1.6))


def test_snell_rays_are_angle_major_with_unit_direction():
    rays = snell_rays(SIX)
    assert len(rays) == 2 * len(SIX)
    assert [r["l"] for r in rays] == [.1] * len(SIX) + [.2] * len(SIX)
    assert [r["wavelength"] for r in rays] == [1, 2, 3, 4, 5, 6] * 2
    assert all(math.isclose(r["l"] ** 2 + r["n"] ** 2, 1, rel_tol=1e-12) for r in rays)


def _rows(indices, sines=(.1, .2)):
    return [dict(error_code=0, vignette_code=0, direction=[sine / n, 0, math.sqrt(1 - (sine / n) ** 2)])
            for sine in sines for n in indices]


def test_snell_indices_from_rows_recovers_both_angles():
    indices = [1.5, 1.6, 1.7]
    recovered, angles = snell_indices_from_rows(_rows(indices), 3)
    assert recovered == indices
    assert [a["sine"] for a in angles] == [.2]
    for expected, actual in zip(indices, angles[0]["indices"]):
        assert abs(expected - actual) < 1e-12


def test_snell_indices_from_rows_rejects_bad_ray_state():
    rows = _rows([1.5, 1.6])
    rows[0]["error_code"] = 1
    with pytest.raises(AssertionError):
        snell_indices_from_rows(rows, 2)
    with pytest.raises(AssertionError):
        snell_indices_from_rows(_rows([1.5, 1.6]), 3)


def test_snell_request_body_is_the_validated_batch_ray_model():
    # The MCP tool nests this body under 'request'; Backend.dispatch validates it directly.
    body = snell_request([.55, .65])
    assert BatchRays.model_validate(body).rays
    with pytest.raises(ValidationError):
        BatchRays.model_validate({"request": body})


class _Evidence:
    def __init__(self, rows):
        self.rows = rows
        self.checks = []

    async def call(self, name, args=None):
        return dict(task_id="fake")

    async def finish(self, task):
        return dict(rows=self.rows)

    def check(self, label, actual, expected, atol=1e-8, rtol=1e-7):
        self.checks.append(dict(label=label, actual=actual, expected=expected, atol=atol, rtol=rtol))
        assert abs(actual - expected) <= atol + rtol * abs(expected), self.checks[-1]


def test_snell_indices_checks_the_second_angle_per_wavelength():
    wavelengths = [.55, .65]
    evidence = _Evidence(_rows([1.5, 1.6]))
    assert asyncio.run(snell_indices(evidence, wavelengths)) == [1.5, 1.6]
    assert [c["label"] for c in evidence.checks] == ["Snell independent angle 0.55", "Snell independent angle 0.65"]
    assert all(c["atol"] == 1e-10 and c["rtol"] == 1e-10 for c in evidence.checks)


def test_snell_indices_reports_angle_disagreement():
    wavelengths = [.55]
    rows = _rows([1.5])
    rows[1]["direction"][0] *= 1.001
    with pytest.raises(AssertionError):
        asyncio.run(snell_indices(_Evidence(rows), wavelengths))


# --- D002 probe solve-parameter readback + close-receipt contracts (no native) ---
import importlib.util as _ilu
import pathlib as _pl

_SC_PATH = (_pl.Path(__file__).resolve().parents[2]
            / "scripts" / "probes" / "D002-MODEL_GLASS" / "solve_contract.py")
_spec = _ilu.spec_from_file_location("d002_solve_contract", _SC_PATH)
sc = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(sc)


def _surface(**solve):
    base = dict(type="MaterialModel", index_nd=1.6, abbe_vd=60.0, dpgf=0.001,
                vary_index=True, vary_abbe=False, vary_dpgf=True)
    base.update(solve)
    return {"cells": {"material": {"value": "MODEL", "solve": base}}}


def test_solve_actual_extracts_all_six_fields_from_public_surface():
    actual = sc.solve_actual(_surface())
    assert actual["model_type"] == "MaterialModel"
    for key in sc.SOLVE_PARAM_KEYS:
        assert key in actual
    assert actual["index_nd"] == 1.6 and actual["abbe_vd"] == 60.0 and actual["dpgf"] == 0.001
    assert actual["vary_index"] is True and actual["vary_abbe"] is False and actual["vary_dpgf"] is True


def test_solve_readback_checks_cover_every_requested_field_and_pass_on_match():
    model = dict(mode="material_model", index_nd=1.6, abbe_vd=60, dpgf=.001,
                 vary_index=True, vary_dpgf=True)
    checks = sc.solve_readback_checks(model, sc.solve_actual(_surface()))
    assert set(checks) == {"index_nd", "abbe_vd", "dpgf", "vary_index", "vary_dpgf"}
    assert all(item["match"] for item in checks.values())


def test_solve_readback_flags_rounded_abbe_mismatch():
    model = dict(mode="material_model", abbe_vd=60)
    checks = sc.solve_readback_checks(model, sc.solve_actual(_surface(abbe_vd=59.99988524798844)))
    assert checks["abbe_vd"]["match"] is False


def test_solve_actual_handles_a_non_model_cell():
    actual = sc.solve_actual({"cells": {"material": {"value": 1.5, "solve": {"type": "Fixed"}}}})
    assert actual["model_type"] == "Fixed"
    assert all(actual[key] is None for key in sc.SOLVE_PARAM_KEYS)


def test_close_receipt_verdict_requires_native_closed_unforced_and_error_free():
    good = dict(forced=False, native=dict(attempted=True, closed=True, error=None),
                checkpoint=dict(attempted=True, ok=True))
    assert sc.close_receipt_verdict(good)["passed"] is True
    assert sc.close_receipt_verdict(None)["passed"] is False
    assert sc.close_receipt_verdict(dict(forced=True, native=dict(closed=True, error=None)))["passed"] is False
    assert sc.close_receipt_verdict(dict(forced=False, native=dict(closed=False, error=None)))["passed"] is False
    assert sc.close_receipt_verdict(dict(forced=False, native=dict(closed=True, error="boom")))["passed"] is False


def test_close_receipt_missing_forced_cannot_prove_non_forced_close():
    content = dict(native=dict(attempted=True, closed=True, error=None))
    verdict = sc.close_receipt_verdict(content)
    assert verdict["forced"] is None
    assert verdict["passed"] is False


def test_match_bool_accepts_only_real_equal_bools():
    assert sc._match(True, True) is True
    assert sc._match(False, False) is True
    assert sc._match(True, False) is False
    # 1 / 'false' must not be coerced into a boolean match.
    assert sc._match(True, 1) is False
    assert sc._match(1, True) is False
    assert sc._match(False, "false") is False
    assert sc._match("false", False) is False


def test_match_rejects_non_finite_and_unconvertible_numbers():
    assert sc._match(1.0, 1.0) is True
    assert sc._match(1.0, float("nan")) is False
    assert sc._match(1.0, float("inf")) is False
    assert sc._match("x", 1.0) is False
    assert sc._match(1.0, None) is False


def test_session_closed_requires_receipt_no_active_task_and_no_cleanup_error():
    ok = sc.session_closed(dict(passed=True), False, None)
    assert ok["closed"] is True
    assert sc.session_closed(dict(passed=True), True, None)["closed"] is False
    assert sc.session_closed(dict(passed=True), False, dict(type="X", message="boom"))["closed"] is False
    assert sc.session_closed(dict(passed=False), False, None)["closed"] is False


# --- formal physical-d convention: Nd main gate must not use the classic wavelength ---
_PROBE_PATH = (_pl.Path(__file__).resolve().parents[2]
               / "scripts" / "probes" / "D002-MODEL_GLASS" / "model_glass_control018.py")
_probe_spec = _ilu.spec_from_file_location("d002_probe_build_gates", _PROBE_PATH)
probe = _ilu.module_from_spec(_probe_spec)
_probe_spec.loader.exec_module(probe)


def test_formal_nd_gate_uses_physical_d_line_when_lines_differ():
    # SIX order: physical d (.5875618)=index 0, classic d (.5876)=index 1.
    # Give the two d wavelengths different index values so a wrong wavelength is detectable.
    direct = [1.600, 1.620, 1.610, 1.611, 1.590, 1.591]
    model = dict(mode="material_model", index_nd=1.600, abbe_vd=60)
    main, diagnostic, positions = probe.build_gates(direct, model)
    assert positions["nd"] == dict(physical=0, classic=1)
    assert main["nd"]["actual"] == 1.600 and main["nd"]["passed"] is True       # physical d
    assert diagnostic["nd_classic"]["actual"] == 1.620 and diagnostic["nd_classic"]["passed"] is False


def test_formal_nd_gate_fails_even_when_the_classic_d_value_matches():
    # Physical d value is off the request while the classic d value equals it.
    direct = [1.6001, 1.600, 1.610, 1.611, 1.590, 1.591]
    model = dict(mode="material_model", index_nd=1.600, abbe_vd=60)
    main, diagnostic, _ = probe.build_gates(direct, model)
    assert main["nd"]["actual"] == 1.6001 and main["nd"]["passed"] is False     # physical d taken
    assert diagnostic["nd_classic"]["actual"] == 1.600 and diagnostic["nd_classic"]["passed"] is True
