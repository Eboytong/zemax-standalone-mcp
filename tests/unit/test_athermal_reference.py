"""Checks for the independent athermal reference module.

The catalog records below are copied verbatim from
``~/Documents/Zemax/Glasscat/SCHOTT.AGF`` (December 2023 header) so the
checks stay hermetic; the native values are the ones the retained 364-row
OpticStudio 24.2.0 report displays.  Both the reference formulas and the
display resolution (thermal power is printed with two decimals and an
``xE-6`` scale) come from the official Release 2024 R2 help, so the
acceptance band is half of the displayed least significant digit, 5e-9.
"""
import math

import pytest

from tests.support import athermal_reference as reference
from tests.support.finite_reference import sellmeier

DISPLAY_HALF_LSB = 5e-9

BK7G18 = dict(
    name="BK7G18", formula=2, nd=1.51975, vd=63.58,
    cd=[1.265385420e+00, 8.131040780e-03, 1.441910730e-02,
        5.433032260e-02, 1.003230280e+00, 1.028211660e+02],
    td=[1.520000e-06, 1.370000e-08, -1.260000e-11, 4.360000e-07, 4.170000e-10, 1.940000e-01, 2.0e+01],
    ed=[7.000000, 8.220000, 2.520000, 0.000700, 0],
)
N_BK7 = dict(
    name="N-BK7", formula=2, nd=1.5168, vd=64.17,
    cd=[1.039612120e+00, 6.000698670e-03, 2.317923440e-01,
        2.001791440e-02, 1.010469450e+00, 1.035606530e+02],
    td=[1.860000e-06, 1.310000e-08, -1.370000e-11, 4.340000e-07, 6.270000e-10, 1.700000e-01, 2.0e+01],
    ed=[7.100000, 8.300000, 2.510000, -0.000900, 0],
)
F2 = dict(
    name="F2", formula=2, nd=1.62004, vd=36.37,
    cd=[1.345333590e+00, 9.977438710e-03, 2.090731760e-01,
        4.704507670e-02, 9.373571620e-01, 1.118867640e+02],
    td=[1.510000e-06, 1.560000e-08, -2.780000e-11, 9.340000e-07, 1.040000e-09, 2.500000e-01, 2.0e+01],
    ed=[8.200000, 9.200000, 3.599000, 0.000200, 0],
)
B270 = dict(
    name="B270", formula=1, nd=1.523080, vd=58.571369,
    cd=[2.286575000e+00, -8.733458200e-03, 1.174288400e-02, 2.904175600e-04,
        -1.250669500e-05, 9.264625300e-07, 0.0, 0.0, 0.0, 0.0],
    td=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0e+01],
    ed=[8.100000000, 9.500000000, 2.540000000, 0.0, 0],
)


def test_air_index_and_derivative_match_reference_values():
    """Kohlrausch air index at 0.55 um / 20 C is close to 1.000273."""
    assert reference.air_index(0.55, 20.0) == pytest.approx(1.0002731, abs=1e-6)
    assert reference.air_dn_dt(0.55, 20.0) == pytest.approx(-9.3e-7, abs=5e-8)
    assert reference.air_dn_dt(0.55, 20.0) < 0


def test_air_index_scales_with_pressure_and_temperature():
    assert reference.air_index(0.55, 20.0, pressure=0.0) == 1.0
    assert reference.air_index(0.55, 30.0) < reference.air_index(0.55, 20.0)


def test_tce_is_multiplied_by_1e_6():
    """Description of Catalog Data: the TCE is dimensionless and needs 1e-6."""
    with_tce = reference.catalog_thermal_power(BK7G18, 0.55)
    without_tce = reference.thermal_power(
        reference.refractive_index(0.55, BK7G18["cd"]), BK7G18["td"], 0.0, 0.55)
    assert with_tce - without_tce == pytest.approx(-7.0e-6, abs=1e-12)


def test_reference_temperature_defaults_to_the_catalog_value():
    implicit = reference.catalog_thermal_power(BK7G18, 0.55)
    explicit = reference.catalog_thermal_power(BK7G18, 0.55, temperature_c=20.0)
    assert implicit == explicit


def test_absolute_index_change_vanishes_at_the_reference_temperature():
    for glass in (BK7G18, N_BK7, F2, B270):
        index = reference.refractive_index(0.55, glass["cd"], glass["formula"])
        assert reference.absolute_index_change(index, glass["td"], 0.55, 0.0) == 0.0


def test_absolute_index_change_is_linear_in_small_temperature_steps():
    index = reference.refractive_index(0.55, BK7G18["cd"])
    small = reference.absolute_index_change(index, BK7G18["td"], 0.55, 0.001)
    derivative = reference.absolute_dn_dt(index, BK7G18["td"], 0.55)
    assert small == pytest.approx(derivative * 0.001, rel=1e-5)


def test_relative_dn_dt_subtracts_the_air_derivative():
    """psi needs dn_rel/dT, so the (negative) air derivative adds a term."""
    index = reference.refractive_index(0.55, BK7G18["cd"])
    n_air = reference.air_index(0.55, 20.0)
    dn_abs = reference.absolute_dn_dt(index, BK7G18["td"], 0.55)
    dn_air = reference.air_dn_dt(0.55, 20.0)
    assert reference.relative_dn_dt(index, BK7G18["td"], 0.55, 20.0) == pytest.approx(
        dn_abs / n_air - index * dn_air / n_air, rel=1e-12)
    absolute_only = dn_abs / (index - 1) - 7.0e-6
    relative = reference.catalog_thermal_power(BK7G18, 0.55)
    assert abs(absolute_only - relative) > 1e-6


def test_lambda_tk_sign_switches_the_resonance_denominator():
    """S_tk = sign(Ltk): lam^2 - Ltk^2 when positive, lam^2 + Ltk^2 when negative."""
    index = reference.refractive_index(0.55, BK7G18["cd"])
    squared = 0.55 ** 2
    scale = (index ** 2 - 1) / (2 * index)
    d0, e0, magnitude = BK7G18["td"][0], BK7G18["td"][3], abs(BK7G18["td"][5])
    positive = list(BK7G18["td"])
    negative = list(BK7G18["td"])
    negative[5] = -magnitude
    assert reference.absolute_dn_dt(index, positive, 0.55) == pytest.approx(
        scale * (d0 + e0 / (squared - magnitude ** 2)), rel=1e-12)
    assert reference.absolute_dn_dt(index, negative, 0.55) == pytest.approx(
        scale * (d0 + e0 / (squared + magnitude ** 2)), rel=1e-12)
    assert reference.absolute_dn_dt(index, positive, 0.55) != pytest.approx(
        reference.absolute_dn_dt(index, negative, 0.55), rel=1e-6)


def test_sellmeier_agrees_with_the_existing_finite_reference():
    assert reference.refractive_index(0.55, BK7G18["cd"]) == pytest.approx(
        sellmeier(0.55, tuple(BK7G18["cd"])), rel=1e-15)


@pytest.mark.parametrize("glass", [BK7G18, N_BK7, F2], ids=lambda g: g["name"])
def test_sellmeier_reproduces_the_catalog_nd(glass):
    assert reference.refractive_index(0.5876, glass["cd"]) == pytest.approx(glass["nd"], abs=5e-6)


def test_schott_series_reproduces_the_catalog_nd():
    """Formula 1 (B270) must match the NM record, which OpticStudio does not use."""
    assert reference.refractive_index(0.5876, B270["cd"], B270["formula"]) == pytest.approx(1.523080, abs=5e-6)


def test_chromatic_power_is_zero_at_equal_wavelengths():
    for glass in (BK7G18, N_BK7, F2, B270):
        assert reference.catalog_chromatic_power(glass, (0.55, 0.55, 0.55)) == 0.0


def test_chromatic_power_at_f_d_c_tracks_the_catalog_vd():
    """The AGF page marks Nd/Vd as unused, so only the magnitude is checked."""
    phi = reference.catalog_chromatic_power(BK7G18, (0.4861, 0.5876, 0.6563))
    assert 1 / phi == pytest.approx(BK7G18["vd"], abs=0.05)


@pytest.mark.parametrize("glass,native", [
    (BK7G18, -1.65e-06), (N_BK7, -1.51e-06), (F2, -1.41e-06), (B270, -5.39e-06),
], ids=[glass["name"] for glass in (BK7G18, N_BK7, F2, B270)])
def test_thermal_power_matches_the_retained_native_report(glass, native):
    """Values printed by OpticStudio 24.2.0 at 0.55 um, 20 C, 1 atm."""
    assert reference.catalog_thermal_power(glass, 0.55) == pytest.approx(native, abs=DISPLAY_HALF_LSB)


def test_incomplete_catalog_records_are_rejected():
    placeholder = dict(F2, cd=[None, *F2["cd"][1:]])
    with pytest.raises(ValueError, match="placeholder"):
        reference.catalog_thermal_power(placeholder, 0.55)
    without_thermal = dict(F2, td=[])
    with pytest.raises(ValueError, match="thermal coefficients"):
        reference.catalog_thermal_power(without_thermal, 0.55)
    with pytest.raises(ValueError, match="TCE"):
        reference.catalog_thermal_power(dict(F2, ed=[]), 0.55)


def test_invalid_arguments_are_rejected():
    index = reference.refractive_index(0.55, BK7G18["cd"])
    with pytest.raises(ValueError):
        reference.chromatic_power(1.5, 1.0, 1.6)
    with pytest.raises(ValueError):
        reference.refractive_index(0.0, BK7G18["cd"])
    with pytest.raises(ValueError):
        reference.refractive_index(0.55, BK7G18["cd"], formula=42)
    with pytest.raises(ValueError):
        reference.thermal_power(index, [1.0, 2.0], 7.0, 0.55)
    assert math.isfinite(reference.thermal_power(index, BK7G18["td"], 7.0, 0.55))


@pytest.mark.parametrize("formula", [reference.FORMULA_SELLMEIER_1, reference.FORMULA_SCHOTT_SERIES])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_dispersion_coefficients_are_rejected(formula, bad):
    coefficients = list(BK7G18["cd"])
    coefficients[2] = bad
    with pytest.raises(ValueError, match="not finite"):
        reference.refractive_index(0.55, coefficients, formula)


@pytest.mark.parametrize("formula", [reference.FORMULA_SELLMEIER_1, reference.FORMULA_SCHOTT_SERIES])
def test_short_dispersion_coefficients_raise_value_error_not_index_error(formula):
    with pytest.raises(ValueError, match="needs 6 coefficients, got 5"):
        reference.refractive_index(0.55, BK7G18["cd"][:5], formula)


@pytest.mark.parametrize("bad", [None, "1.0", True])
def test_non_numeric_dispersion_coefficients_are_rejected(bad):
    coefficients = list(BK7G18["cd"])
    coefficients[4] = bad
    with pytest.raises(ValueError):
        reference.refractive_index(0.55, coefficients)


def test_placeholder_coefficient_reports_the_placeholder_condition():
    coefficients = list(BK7G18["cd"])
    coefficients[0] = None
    with pytest.raises(ValueError, match="placeholder"):
        reference.refractive_index(0.55, coefficients)


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf")])
def test_non_finite_thermal_coefficients_are_rejected(bad):
    thermal = list(BK7G18["td"])
    thermal[3] = bad
    index = reference.refractive_index(0.55, BK7G18["cd"])
    with pytest.raises(ValueError):
        reference.absolute_dn_dt(index, thermal, 0.55)


def test_schott_model_keeps_the_d1_d2_and_e1_terms():
    """The derivative must keep D1, D2 and E1, not just D0/E0."""
    index = reference.refractive_index(0.55, BK7G18["cd"])
    d0, d1, d2, e0, e1, lambda_tk, _temp = BK7G18["td"]
    delta = 10.0
    squared, resonant = 0.55 ** 2, 0.55 ** 2 - lambda_tk ** 2
    scale = (index ** 2 - 1) / (2 * index)
    expected = scale * (d0 + 2 * d1 * delta + 3 * d2 * delta ** 2
                        + (e0 + 2 * e1 * delta) / resonant)
    assert reference.absolute_dn_dt(index, BK7G18["td"], 0.55, delta) == pytest.approx(expected, rel=1e-12)
    reference_change = scale * (d0 * delta + d1 * delta ** 2 + d2 * delta ** 3
                                + (e0 * delta + e1 * delta ** 2) / resonant)
    assert reference.absolute_index_change(index, BK7G18["td"], 0.55, delta) == pytest.approx(
        reference_change, rel=1e-12)
    d0_only = scale * (d0 + e0 / resonant)
    assert abs(reference.absolute_dn_dt(index, BK7G18["td"], 0.55, delta) - d0_only) > 1e-7
    assert squared == pytest.approx(0.3025)


def test_relative_index_at_the_reference_temperature_is_unchanged():
    index = reference.refractive_index(0.55, BK7G18["cd"])
    assert reference.relative_index_at_temperature(index, BK7G18["td"], 0.55, 20.0) == index
    warmer = reference.relative_index_at_temperature(index, BK7G18["td"], 0.55, 25.0)
    assert warmer != index
    assert abs(warmer - index) < 1e-4


def test_environment_temperature_requires_an_explicit_opt_in():
    """Only the catalog reference temperature is validated against native runs."""
    index = reference.refractive_index(0.55, BK7G18["cd"])
    with pytest.raises(ValueError, match="reference temperature"):
        reference.thermal_power(index, BK7G18["td"], 7.0, 0.55, temperature_c=25.0)
    with pytest.raises(ValueError, match="allow_unvalidated_temperature"):
        reference.relative_dn_dt(index, BK7G18["td"], 0.55, temperature_c=25.0)
    with pytest.raises(ValueError, match="reference temperature"):
        reference.catalog_thermal_power(dict(BK7G18, ed=[7.0]), 0.55, temperature_c=25.0)
    accepted = reference.thermal_power(index, BK7G18["td"], 7.0, 0.55, temperature_c=25.0,
                                       allow_unvalidated_temperature=True)
    assert math.isfinite(accepted)
    assert accepted != reference.thermal_power(index, BK7G18["td"], 7.0, 0.55)
    assert abs(accepted - reference.thermal_power(index, BK7G18["td"], 7.0, 0.55)) < 1e-5


def test_reference_temperature_is_read_from_the_td_record():
    assert reference.reference_temperature(BK7G18["td"]) == 20.0
    with pytest.raises(ValueError, match="reference temperature"):
        reference.reference_temperature(BK7G18["td"][:6])


def test_system_air_reference_at_catalog_environment_matches_dispersion():
    expected = reference.refractive_index(.55,BK7G18['cd'])
    assert reference.system_relative_index(BK7G18,.55,20) == pytest.approx(expected,abs=1e-15)


def test_system_environment_constant_dispersion_obeys_air_normalization():
    entry=dict(formula=1,cd=[2.25,0.,0.,0.,0.,0.],td=[0.]*6+[20.])
    # With constant dispersion and zero absolute thermal change, n_abs is fixed
    # at the specified input wavelength even when system pressure changes.
    for temperature,pressure in ((10,1),(30,1),(20,0),(20,.8)):
        actual=reference.system_relative_index(entry,.55,temperature,pressure)
        assert actual*reference.air_index(.55,temperature,pressure) == pytest.approx(
            1.5*reference.air_index(.55,20),abs=1e-14)


def test_system_relative_index_requires_explicit_thermal_reference():
    with pytest.raises(ValueError,match='Thermal data'):
        reference.system_relative_index(dict(BK7G18,td=[]),.55,25)
