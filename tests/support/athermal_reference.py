"""Independent athermal glass-map references.

Every expression below is transcribed from the Ansys Zemax OpticStudio
Release 2024 R2 help; the page is cited next to the formula.  No ZOS-API
call and no production adapter is used, so the module stays usable as an
independent reference for the MA-01.AthermalGlassMap acceptance checks.

Units follow the glass catalog: wavelength in micrometres, temperature in
degrees Celsius, and the catalog TCE / thermal coefficients used verbatim
(the TCE is multiplied by 1e-6 as the catalog documentation requires).

Athermal Glass Map (topics/Athermal_Glass_Map.html, section 8.1.3.3)::

    chromatic power  phi = (n_min - n_max) / (n_cen - 1)
    thermal power    psi = (dn_rel/dt) / (n_cen - 1) - alpha

``dn_rel/dt`` is the derivative of the *relative* index with respect to
temperature at the center wavelength and the glass reference temperature,
so the air term of the index computation must be part of it.

Index of Refraction Computation (topics/Index_of_Refraction_Computation.html)::

    n_air(lam,T,P) = 1 + (n_ref - 1) P / (1 + (T - 15) * 3.4785e-3)
    n_ref(lam)     = 1 + [6432.8 + 2949810 lam^2/(146 lam^2 - 1)
                          + 25540 lam^2/(41 lam^2 - 1)] * 1e-8
    dn_abs(lam,dT) = (n^2 - 1)/(2n) [D0 dT + D1 dT^2 + D2 dT^3
                     + (E0 dT + E1 dT^2)/(lam^2 - S_tk lam_tk^2)]
    S_tk           = sign(lam_tk)

The thermal model describes the change in *absolute* index, while the
catalog and the map use the index relative to air, hence
``n_abs = n_rel * n_air`` and the conversion helpers below.

Description of Catalog Data: the TCE is "dimensionless ... multiplied by
1e-6 to yield the actual values", and ``Temp`` is "the reference
temperature in degrees Celsius".

Dispersion: ``refractive_index`` covers formula 1 (Schott power series,
the form used by B270) and formula 2 (Sellmeier 1, the SCHOTT default).

Coverage of the temperature argument
------------------------------------
Only the configuration "system temperature == the glass reference
temperature from the TD record" has been validated: it is the one that the
retained 364-row OpticStudio report shows (0.55 um, 20 C, 1 atm), and the
359 comparable rows reproduce within 5e-9.

The Schott expression above does define the temperature dependence through
D0..D2 and E0/E1, and ``absolute_dn_dt`` / ``thermal_power`` evaluate it at
an arbitrary environment temperature when ``delta_temperature`` or
``temperature_c`` is supplied.  That path is *not* covered by native
evidence: no accepted run changes the system temperature.  It is therefore
gated behind ``allow_unvalidated_temperature=True`` so a caller cannot
mistake it for accepted behaviour, and temperature-sweep acceptance is
tracked as a separate open item rather than claimed here.
"""
import math

FORMULA_SCHOTT_SERIES = 1
FORMULA_SELLMEIER_1 = 2

# Coefficients consumed by each dispersion formula, in catalog order.
_REQUIRED_COEFFICIENTS = {
    FORMULA_SCHOTT_SERIES: 6,   # A0 A1 A2 A3 A4 A5
    FORMULA_SELLMEIER_1: 6,     # B1 C1 B2 C2 B3 C3
}

_THERMAL_COEFFICIENTS = 7       # D0 D1 D2 E0 E1 Ltk Temp


def _finite(*values):
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        raise ValueError("A finite numeric argument is required")


def _coefficients(coefficients, formula):
    """Validate the coefficient record for ``formula`` and return its values."""
    if formula not in _REQUIRED_COEFFICIENTS:
        raise ValueError("Unsupported dispersion formula: %r" % (formula,))
    required = _REQUIRED_COEFFICIENTS[formula]
    try:
        values = list(coefficients)
    except TypeError as error:
        raise ValueError("Dispersion coefficients must be a sequence of numbers") from error
    if len(values) < required:
        raise ValueError("Dispersion formula %r needs %d coefficients, got %d"
                         % (formula, required, len(values)))
    selected = values[:required]
    for position, value in enumerate(selected):
        if value is None:
            raise ValueError("Coefficient %d of formula %r is a catalog placeholder" % (position, formula))
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Coefficient %d of formula %r is not a number: %r"
                             % (position, formula, value))
        if not math.isfinite(value):
            raise ValueError("Coefficient %d of formula %r is not finite: %r"
                             % (position, formula, value))
    return [float(value) for value in selected]


def reference_temperature(thermal):
    """``TD`` reference temperature in Celsius (the model's zero of dT)."""
    values = list(thermal)
    if len(values) < _THERMAL_COEFFICIENTS:
        raise ValueError("Thermal data needs D0 D1 D2 E0 E1 Ltk and the reference temperature")
    _finite(values[6])
    return float(values[6])


def refractive_index(wavelength_um, coefficients, formula=FORMULA_SELLMEIER_1):
    """Relative index at the catalog reference temperature and 1.0 atm."""
    values = _coefficients(coefficients, formula)
    _finite(wavelength_um)
    if wavelength_um <= 0:
        raise ValueError("A positive wavelength in micrometres is required")
    squared = wavelength_um ** 2
    if formula == FORMULA_SELLMEIER_1:
        pairs = [(values[index], values[index + 1]) for index in (0, 2, 4)]
        if any(squared - denominator == 0 for _, denominator in pairs):
            raise ValueError("Sellmeier coefficient equals the squared wavelength")
        return math.sqrt(1 + sum(b * squared / (squared - c) for b, c in pairs))
    # n^2 = A0 + A1 lam^2 + A2 lam^-2 + A3 lam^-4 + A4 lam^-6 + A5 lam^-8
    total = values[0] + values[1] * squared
    total += sum(values[index] / squared ** (index - 1) for index in (2, 3, 4, 5))
    if total <= 0:
        raise ValueError("Schott series yields a non-positive squared index")
    return math.sqrt(total)


def chromatic_power(n_min, n_center, n_max):
    """phi = (n_min - n_max)/(n_cen - 1); equals 1/V for a generalized V."""
    _finite(n_min, n_center, n_max)
    if n_center == 1:
        raise ValueError("The center index must differ from 1")
    return (n_min - n_max) / (n_center - 1)


def air_index(wavelength_um, temperature_c, pressure=1.0):
    """Index of air from eq. 1 and 2 of Index of Refraction Computation."""
    _finite(wavelength_um, temperature_c, pressure)
    squared = wavelength_um ** 2
    n_ref = 1 + (6432.8
                 + 2949810 * squared / (146 * squared - 1)
                 + 25540 * squared / (41 * squared - 1)) * 1e-8
    return 1 + (n_ref - 1) * pressure / (1 + (temperature_c - 15) * 3.4785e-3)


def air_dn_dt(wavelength_um, temperature_c, pressure=1.0):
    """Temperature derivative of ``air_index`` (negative near ambient)."""
    _finite(wavelength_um, temperature_c, pressure)
    squared = wavelength_um ** 2
    n_ref = 1 + (6432.8
                 + 2949810 * squared / (146 * squared - 1)
                 + 25540 * squared / (41 * squared - 1)) * 1e-8
    denominator = 1 + (temperature_c - 15) * 3.4785e-3
    return -(n_ref - 1) * pressure * 3.4785e-3 / denominator ** 2


def _thermal_terms(thermal):
    values = list(thermal)
    if len(values) < _THERMAL_COEFFICIENTS:
        raise ValueError("Thermal data needs D0 D1 D2 E0 E1 Ltk and the reference temperature")
    selected = values[:_THERMAL_COEFFICIENTS]
    for position, value in enumerate(selected):
        if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Thermal coefficient %d is not a number: %r" % (position, value))
        if not math.isfinite(value):
            raise ValueError("Thermal coefficient %d is not finite: %r" % (position, value))
    d0, d1, d2, e0, e1, lambda_tk, temperature = (float(value) for value in selected)
    return d0, d1, d2, e0, e1, lambda_tk, temperature


def _resonance(wavelength_um, lambda_tk):
    """lam^2 - S_tk lam_tk^2 with S_tk = sign(lam_tk)."""
    sign_tk = 1.0 if lambda_tk >= 0 else -1.0
    resonant = wavelength_um ** 2 - sign_tk * lambda_tk ** 2
    if resonant == 0:
        raise ValueError("Wavelength matches lambda_tk; the thermal model is singular")
    return resonant


def absolute_index_change(relative_index, thermal, wavelength_um, delta_temperature):
    """Delta n_abs for a temperature change relative to the reference."""
    _finite(relative_index, wavelength_um, delta_temperature)
    if relative_index <= 0:
        raise ValueError("A positive index is required")
    d0, d1, d2, e0, e1, lambda_tk, _temperature = _thermal_terms(thermal)
    resonant = _resonance(wavelength_um, lambda_tk)
    bracket = (d0 * delta_temperature + d1 * delta_temperature ** 2
               + d2 * delta_temperature ** 3
               + (e0 * delta_temperature + e1 * delta_temperature ** 2) / resonant)
    return (relative_index ** 2 - 1) / (2 * relative_index) * bracket


def absolute_dn_dt(relative_index, thermal, wavelength_um, delta_temperature=0.0):
    """d(n_abs)/dT of the Schott model at ``delta_temperature``.

    The formal model is
    ``dn_abs = (n^2-1)/(2n) [D0 dT + D1 dT^2 + D2 dT^3 + (E0 dT + E1 dT^2)/R]``,
    so the derivative keeps the D1, D2 and E1 terms:
    ``(n^2-1)/(2n) [D0 + 2 D1 dT + 3 D2 dT^2 + (E0 + 2 E1 dT)/R]``.
    ``delta_temperature = 0`` is the catalog reference temperature and the
    only configuration validated against native evidence.
    """
    _finite(relative_index, wavelength_um, delta_temperature)
    if relative_index <= 0:
        raise ValueError("A positive index is required")
    d0, d1, d2, e0, e1, lambda_tk, _temperature = _thermal_terms(thermal)
    resonant = _resonance(wavelength_um, lambda_tk)
    bracket = (d0 + 2 * d1 * delta_temperature + 3 * d2 * delta_temperature ** 2
               + (e0 + 2 * e1 * delta_temperature) / resonant)
    return (relative_index ** 2 - 1) / (2 * relative_index) * bracket


def relative_index_at_temperature(relative_index, thermal, wavelength_um, temperature_c):
    """n_rel at an environment temperature, via the absolute-index change."""
    _finite(relative_index, wavelength_um, temperature_c)
    reference_c = reference_temperature(thermal)
    delta = temperature_c - reference_c
    if delta == 0.0:
        return relative_index
    n_air_reference = air_index(wavelength_um, reference_c)
    n_abs = relative_index * n_air_reference + absolute_index_change(
        relative_index, thermal, wavelength_um, delta)
    return n_abs / air_index(wavelength_um, temperature_c)


def _require_validated_temperature(temperature_c, reference_c, allow_unvalidated, function):
    if allow_unvalidated or temperature_c == reference_c:
        return
    raise ValueError(
        "%s: only the catalog reference temperature (%.6g C) is validated against native "
        "evidence. The formal Schott model implements the D1/D2 and E1 terms for other "
        "temperatures, but no accepted native run changes the system temperature, so an "
        "environment temperature requires allow_unvalidated_temperature=True and its results "
        "must not be reported as accepted; temperature-sweep acceptance is a separate open item."
        % (function, reference_c))


def relative_dn_dt(relative_index, thermal, wavelength_um, temperature_c=None,
                   *, allow_unvalidated_temperature=False):
    """d(n_rel)/dT from n_rel = n_abs / n_air.

    The map asks for the derivative of the relative index, so the air
    derivative is subtracted, not ignored.  ``temperature_c=None`` means the
    catalog reference temperature of the glass (the validated case).
    """
    _finite(relative_index, wavelength_um)
    reference_c = reference_temperature(thermal)
    if temperature_c is None:
        temperature_c = reference_c
    _finite(temperature_c)
    _require_validated_temperature(temperature_c, reference_c, allow_unvalidated_temperature,
                                   "relative_dn_dt")
    delta = temperature_c - reference_c
    n_air = air_index(wavelength_um, temperature_c)
    dn_abs = absolute_dn_dt(relative_index, thermal, wavelength_um, delta)
    dn_air = air_dn_dt(wavelength_um, temperature_c)
    if delta == 0.0:
        return dn_abs / n_air - relative_index * dn_air / n_air
    n_rel = relative_index_at_temperature(relative_index, thermal, wavelength_um, temperature_c)
    return dn_abs / n_air - n_rel * dn_air / n_air


def thermal_power(relative_index, thermal, tce, wavelength_um, temperature_c=None,
                  *, allow_unvalidated_temperature=False):
    """psi = (dn_rel/dT)/(n_cen - 1) - alpha with alpha = tce * 1e-6."""
    _finite(relative_index, wavelength_um, tce)
    if relative_index <= 0:
        raise ValueError("A positive index is required")
    reference_c = reference_temperature(thermal)
    if temperature_c is None:
        temperature_c = reference_c
    _finite(temperature_c)
    _require_validated_temperature(temperature_c, reference_c, allow_unvalidated_temperature,
                                   "thermal_power")
    alpha = tce * 1e-6
    derivative = relative_dn_dt(relative_index, thermal, wavelength_um, temperature_c,
                               allow_unvalidated_temperature=allow_unvalidated_temperature)
    center = relative_index_at_temperature(relative_index, thermal, wavelength_um, temperature_c)
    return derivative / (center - 1) - alpha


def catalog_thermal_power(entry, wavelength_um, temperature_c=None,
                          *, allow_unvalidated_temperature=False):
    """psi for a parsed catalog record: cd/td/ed plus the NM dispersion formula.

    ``entry`` maps the catalog keys used by the AGF parser: ``formula``,
    ``cd`` (coefficients, ``None`` for a placeholder), ``td`` (D0..Temp) and
    ``ed`` (TCE -30..70 C first).
    """
    coefficients = entry.get("cd") or []
    thermal = entry.get("td") or []
    ed = entry.get("ed") or []
    if len(thermal) < _THERMAL_COEFFICIENTS:
        raise ValueError("The TD record carries no thermal coefficients")
    if not ed:
        raise ValueError("The ED record carries no TCE")
    n_rel = refractive_index(wavelength_um, coefficients, int(entry.get("formula", FORMULA_SELLMEIER_1)))
    return thermal_power(n_rel, thermal, ed[0], wavelength_um, temperature_c,
                         allow_unvalidated_temperature=allow_unvalidated_temperature)


def catalog_chromatic_power(entry, wavelengths_um):
    """phi at three wavelengths taken in minimum, center, maximum order.

    Evaluated at the catalog reference temperature; the map's own chromatic
    term has no temperature dependence beyond the indices at those
    wavelengths.
    """
    minimum, center, maximum = wavelengths_um
    coefficients = entry.get("cd") or []
    formula = int(entry.get("formula", FORMULA_SELLMEIER_1))
    return chromatic_power(refractive_index(minimum, coefficients, formula),
                           refractive_index(center, coefficients, formula),
                           refractive_index(maximum, coefficients, formula))


def system_relative_index(entry, wavelength_um, temperature_c, pressure_atm=1.0):
    """Apply the wavelength scaling steps in 2024 R2 manual section 2.1.1.4.2.

    The wavelength is measured in system air. The catalog wavelength is scaled by the ratio of
    system/reference air indices evaluated at that input wavelength. Thermal coefficients
    and reference temperature must be supplied explicitly in the entry.
    """
    _finite(wavelength_um, temperature_c, pressure_atm)
    if wavelength_um <= 0 or pressure_atm < 0:
        raise ValueError('Positive wavelength and nonnegative pressure are required')
    thermal = entry.get('td') or []
    reference_c = reference_temperature(thermal)
    # Manual p119 defines lambda in the air-index formula as the input system
    # wavelength, including when computing reference-environment air.
    system_air = air_index(wavelength_um, temperature_c, pressure_atm)
    reference_air = air_index(wavelength_um, reference_c)
    catalog_wave = wavelength_um*system_air/reference_air
    n_ref = refractive_index(catalog_wave, entry.get('cd') or [], int(entry['formula']))
    n_abs = n_ref*reference_air
    n_abs += absolute_index_change(n_ref, thermal, catalog_wave, temperature_c-reference_c)
    return n_abs/system_air
