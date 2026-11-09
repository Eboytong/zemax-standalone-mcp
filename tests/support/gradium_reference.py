"""Independent GRADIUM references from the installed manual and resource files.

This module is test support only. Product code never imports it: the power-series
evaluation and the capping outcome rules below are *references* used to judge
native behavior, not results that the MCP server may report as native values.

Documented sources
------------------
- ``development/evidence/MA-01/manual437-gradium.txt`` (installed manual, page 244-245):
  * Profile file blocks are ``PROFILE_NAME GLASS_FAMILY MAX_Z ...`` followed by the
    twelve coefficients ``n0..n11`` (parameter 0 is the boule thickness, i.e. ``MAX_Z``).
  * The reference index is the profile polynomial evaluated at the profile
    coordinate ``z + offset``; the surface-local ``z`` may be negative.
  * Capping: 0 bounds both profile ends, 1 bounds only the left end, 2 bounds only
    the right end, 3 bounds neither end.
  * Parameter 3 is the vertex reference index at the *glass-family* reference
    wavelength from ``SGRIN.DAT``, not the selected system wavelength.
- ``SGRIN.DAT`` family blocks: ``NAME``, wavelength range, reference wavelength,
  ``n_terms m_terms``, then the index/dispersion coefficient rows.

The left/right end naming is not taken on faith: the recorded native matrix
``development/evidence/MA-01/gradium-capping-boundary-repeat20261108.md`` shows that
``offset + 5.6`` (profile coordinate above ``zmax = 5.8``) is rejected for capping
0 and 2 and accepted for capping 1 and 3, so the *right* end is the ``u > zmax``
end. Which physical end of the blank is "left" for a negative offset is exactly
what the E2 experiment decides; ``boundary_hypotheses`` keeps the alternatives.
"""
from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path

GRD_COEFFICIENTS = 12
PROFILE_END_LEFT = 'left'
PROFILE_END_RIGHT = 'right'

# Retained raw probe records (offline replay for E1).
PROBE_RECORDS = {
    'probe637-monomials': 'development/evidence/MA-01/probe637-monomials/basis.json',
    'probe638-unit-monomials': 'development/evidence/MA-01/probe638-unit-monomials/basis.json',
    'probe639-boule-scale': 'development/evidence/MA-01/probe639-boule-scale/basis.json',
}
# Conditions recorded in development/evidence/MA-01/progress641-monomials.json
# (probe637 did not copy amplitude/maximum_z into its own raw record).
PROBE_CONDITIONS = {
    'probe637-monomials': dict(amplitude=0.1, maximum_z=1.0),
    'probe638-unit-monomials': dict(amplitude=1.0, maximum_z=1.0),
    'probe639-boule-scale': dict(amplitude=1.0, maximum_z=5.8),
}

# Original numeric gates; these are kept, never relaxed.
CURVE_ATOL = 1e-10
CURVE_RTOL = 1e-9
DIRECTION_ATOL = 1e-10
# Retained low-order residual bound observed in 637-639 (degrees 0..9).
LOW_ORDER_MAX_RESIDUAL = 2.220446049250313e-15


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# --- GRD profile blocks ----------------------------------------------------

def parse_grd_blocks(text):
    """Parse a GRD file into ``{profile_name: block}``.

    A block is the documented first line plus the twelve ``n0..n11`` values.
    Tokens after ``MAX_Z`` (density/unused/paired name in the stock file) are
    retained as ``extra_tokens`` because their semantics are not documented as
    ray-tracing inputs.
    """
    lines = text.splitlines()
    blocks = {}
    index = 0
    while index < len(lines):
        raw = lines[index].strip()
        index += 1
        if not raw or raw.startswith('!'):
            continue
        parts = raw.split()
        if len(parts) < 3:
            raise ValueError(f'GRD block header needs name, family and maximum z: {raw!r}')
        name, family = parts[0], parts[1]
        maximum_z = float(parts[2])
        if not math.isfinite(maximum_z) or maximum_z <= 0:
            raise ValueError(f'GRD maximum z must be finite and positive: {raw!r}')
        coefficients = []
        while len(coefficients) < GRD_COEFFICIENTS and index < len(lines):
            candidate = lines[index].strip()
            index += 1
            if not candidate or candidate.startswith('!'):
                continue
            coefficients.append(float(candidate.split()[0]))
        if len(coefficients) != GRD_COEFFICIENTS:
            raise ValueError(f'GRD block {name!r} has {len(coefficients)} coefficients')
        if name in blocks:
            raise ValueError(f'duplicate GRD profile name {name!r}')
        blocks[name] = dict(name=name, family=family, maximum_z=maximum_z,
                            coefficients=coefficients, extra_tokens=parts[3:],
                            source_line=index - len(coefficients) - 1)
    return blocks


def parse_grd_block(text, name):
    blocks = parse_grd_blocks(text)
    if name not in blocks:
        raise KeyError(f'GRD profile {name!r} not found; available: {sorted(blocks)}')
    return blocks[name]


# --- SGRIN glass families --------------------------------------------------

def parse_sgrin_families(text):
    """Parse ``SGRIN.DAT`` into ``{family: block}``.

    Only the documented header fields are interpreted: wavelength range,
    reference wavelength and the two term counts. The coefficient rows that follow
    are kept verbatim as ``raw_rows`` (their formula is not needed by this task) and
    are skipped by shape: a family header starts with a non-numeric token, while
    coefficient rows start with a number. The row layout is therefore never
    inferred, so a layout change cannot make this parser report wrong numbers.
    """
    lines = [line.strip() for line in text.splitlines()]
    families = {}
    index = 0
    while index < len(lines):
        if not lines[index] or lines[index].startswith('!'):
            index += 1
            continue
        name = lines[index]
        header = lines[index + 1:index + 4]
        if len(header) != 3:
            raise ValueError(f'SGRIN family {name!r} is truncated')
        range_tokens = header[0].split()
        if len(range_tokens) != 2:
            raise ValueError(f'SGRIN family {name!r} wavelength range invalid: {header[0]!r}')
        minimum, maximum = (float(token) for token in range_tokens)
        reference = float(header[1].split()[0])
        terms = header[2].split()
        if len(terms) != 2:
            raise ValueError(f'SGRIN family {name!r} term counts invalid: {header[2]!r}')
        index_count, dispersion_count = (int(token) for token in terms)
        index += 4
        rows = []
        while index < len(lines) and lines[index] and not lines[index].startswith('!'):
            first = lines[index].split()[0]
            try:
                float(first)
            except ValueError:
                break
            rows.append(lines[index])
            index += 1
        families[name] = dict(name=name, minimum_wavelength_um=minimum, maximum_wavelength_um=maximum,
                              reference_wavelength_um=reference, index_terms=index_count,
                              dispersion_terms=dispersion_count, raw_rows=rows)
    return families


def parse_sgrin_family(text, family):
    families = parse_sgrin_families(text)
    if family not in families:
        raise KeyError(f'SGRIN family {family!r} not found; available: {sorted(families)}')
    return families[family]


# --- documented profile evaluation ----------------------------------------

def profile_coordinate(z, offset):
    """Profile coordinate ``z + offset``; ``z`` is the surface-local axial coordinate."""
    return float(z) + float(offset)


def normalized_coordinate(z, offset, maximum_z):
    return profile_coordinate(z, offset) / float(maximum_z)


def exact_reference_index(coefficients, maximum_z, offset, z=0.0):
    """Exact rational value of ``sum_i n_i * ((z + offset) / maximum_z) ** i``."""
    u = Fraction(profile_coordinate(z, offset)) / Fraction(float(maximum_z))
    total = Fraction(0)
    for power, coefficient in enumerate(coefficients):
        total += Fraction(float(coefficient)) * u ** power
    return total


def reference_index(coefficients, maximum_z, offset, z=0.0):
    """Floating-point evaluation of the documented polynomial (reference only)."""
    u = profile_coordinate(z, offset) / float(maximum_z)
    total = 0.0
    for power, coefficient in enumerate(coefficients):
        total += float(coefficient) * u ** power
    return total


# --- documented capping semantics -----------------------------------------

BOUNDED_ENDS_DOCUMENTED = {
    0: (PROFILE_END_LEFT, PROFILE_END_RIGHT),
    1: (PROFILE_END_LEFT,),
    2: (PROFILE_END_RIGHT,),
    3: (),
}


def exceeds_ends(u, maximum_z):
    """Profile ends reached by coordinate ``u``: left is ``u < 0``, right is ``u > maximum_z``."""
    if u < 0:
        return (PROFILE_END_LEFT,)
    if u > maximum_z:
        return (PROFILE_END_RIGHT,)
    return ()


def bounded_ends(capping):
    try:
        return BOUNDED_ENDS_DOCUMENTED[int(capping)]
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f'capping must be 0, 1, 2 or 3, got {capping!r}') from exc


def documented_allowed(u, maximum_z, capping, offset=None):
    """Manual rule: a ray is flagged when it needs material beyond a *bounded* end."""
    bounded = bounded_ends(capping)
    return not any(end in bounded for end in exceeds_ends(u, maximum_z))


def _negative_offset_rejected(u, maximum_z, capping, offset=None):
    """H-D: a negative offset is refused independent of capping and profile ends."""
    return offset is None or float(offset) >= 0


def _labels_swapped(u, maximum_z, capping, offset=None):
    """H-E: the implementation bounds the opposite physical end for capping 1 and 2."""
    swapped = {0: (PROFILE_END_LEFT, PROFILE_END_RIGHT), 1: (PROFILE_END_RIGHT,),
               2: (PROFILE_END_LEFT,), 3: ()}
    bounded = swapped[int(capping)]
    return not any(end in bounded for end in exceeds_ends(u, maximum_z))


def boundary_hypotheses():
    """Distinguishable boundary rules; each takes ``(u, maximum_z, capping, offset=None)``."""
    return {
        'documented': dict(rule='bounded ends 0=both,1=left,2=right,3=none; left means u<0',
                           allowed=documented_allowed),
        'negative_offset_rejected': dict(rule='H-D: offset<0 refused regardless of capping',
                                         allowed=_negative_offset_rejected),
        'labels_swapped': dict(rule='H-E: capping 1 bounds u>zmax and capping 2 bounds u<0',
                               allowed=_labels_swapped),
    }


# --- independent surface sag (E2 profile coordinate) ----------------------

def surface_sag(height, radius):
    """Sag of a spherical surface of ``radius`` at radial ``height`` (conic constant 0)."""
    height, radius = float(height), float(radius)
    if not math.isfinite(radius) or radius == 0:
        raise ValueError('radius must be finite and non-zero')
    if abs(height) > abs(radius):
        raise ValueError('height exceeds the sphere radius')
    return height * height / (radius * (1.0 + math.sqrt(1.0 - (height / radius) ** 2)))


# --- E1 offline replay of the retained monomial records --------------------

def load_probe_record(name):
    path = project_root() / PROBE_RECORDS[name]
    return json.loads(path.read_text(encoding='utf-8'))


def probe_conditions(record, name=None):
    """Rows of one retained probe record: degree, normalized coordinate, native value, exact value."""
    conditions = record.get('conditions') or {}
    retained = PROBE_CONDITIONS.get(name or record.get('record') or '', {})
    amplitude = float(record.get('amplitude', conditions.get('amplitude', retained.get('amplitude', 0.0))))
    maximum_z = float(record.get('maximum_z', conditions.get('maximum_z', retained.get('maximum_z', 1.0))))
    rows = []
    for case in record['cases']:
        degree = int(case['degree'])
        # 637-639 wrote n_ref = 1.5 + amplitude*(z/zmax)**degree with n0 = 1.5.
        coefficients = [0.0] * GRD_COEFFICIENTS
        coefficients[0] = 1.5
        if degree:
            coefficients[degree] = amplitude
        for point in case['points']:
            native = float(point['indices'][0])
            coordinate = float(point['coordinate'])
            exact = exact_reference_index(coefficients, maximum_z, coordinate)
            residual = Fraction(native) - exact
            rows.append(dict(record=name or record.get('record'), degree=degree,
                             coordinate=coordinate,
                             normalized_coordinate=float(point.get('normalized_coordinate', coordinate / maximum_z)),
                             native=native, exact=float(exact),
                             residual=float(residual),
                             relative_to_amplitude=None if not amplitude else float(residual) / amplitude,
                             native_return=int(point['native_return'])))
    return dict(amplitude=amplitude, maximum_z=maximum_z, rows=rows)


def residual_report(records):
    """Summarize per-degree maximum absolute residual and the 0..9 / 10..11 split."""
    summary = []
    for name, record in records.items():
        conditions = probe_conditions(record, name)
        per_degree = {}
        for row in conditions['rows']:
            per_degree.setdefault(row['degree'], []).append(row)
        for degree in sorted(per_degree):
            rows = per_degree[degree]
            worst = max(rows, key=lambda row: abs(row['residual']))
            summary.append(dict(record=name, amplitude=conditions['amplitude'],
                                maximum_z=conditions['maximum_z'], degree=degree,
                                maximum_absolute_residual=abs(worst['residual']),
                                at_normalized_coordinate=worst['normalized_coordinate'],
                                at_coordinate=worst['coordinate'],
                                within_low_order_bound=abs(worst['residual']) <= LOW_ORDER_MAX_RESIDUAL))
    return summary


def hypothesis_verdicts(records):
    """Offline verdicts for H-A/H-B/H-C from the retained 637-639 records.

    H-A (high-order evaluation path) stays open: it needs the E3 native rows.
    H-B (text precision / coefficient order) is refuted when degrees 0..9 match
    the exact polynomial at double precision.
    H-C (dispersion / wavelength attribution) is refuted as the cause of the
    5e-9 residuals when the residual is many orders below one system-wavelength
    index step, and is left to the Q3 native probe.
    """
    report = residual_report(records)
    low = [row for row in report if row['degree'] <= 9]
    high = [row for row in report if row['degree'] >= 10]
    low_bound = max((row['maximum_absolute_residual'] for row in low), default=0.0)
    verdict = dict(
        records=sorted(records),
        low_order_maximum_residual=low_bound,
        low_order_bound=LOW_ORDER_MAX_RESIDUAL,
        low_order_matches_exact_polynomial=low_bound <= LOW_ORDER_MAX_RESIDUAL,
        high_order=[dict(record=row['record'], degree=row['degree'],
                         maximum_absolute_residual=row['maximum_absolute_residual'],
                         at_normalized_coordinate=row['at_normalized_coordinate']) for row in high],
        h_b_text_or_coefficient_order_refuted=low_bound <= LOW_ORDER_MAX_RESIDUAL,
        h_b_basis='degrees 0..9 match the exact GRD polynomial, so text precision and coefficient order are not the source of the 10/11-order residuals',
        h_a_status='open; E3 native rows decide additivity and zmax invariance',
        h_c_status='not the cause of the 5e-9 residuals by magnitude; Q3 native probe decides column wavelength attribution',
    )
    verdict.update(normalization_and_amplitude_checks(records))
    return verdict


def normalization_and_amplitude_checks(records):
    """Compare zmax=1 vs zmax=5.8 at equal normalized coordinates, and 0.1 vs 1 amplitude."""
    checks = {}
    unit = records.get('probe638-unit-monomials')
    boule = records.get('probe639-boule-scale')
    if unit and boule:
        left = {(row['degree'], round(row['normalized_coordinate'], 12)): row for row in probe_conditions(unit, 'probe638-unit-monomials')['rows']}
        right = {(row['degree'], round(row['normalized_coordinate'], 12)): row for row in probe_conditions(boule, 'probe639-boule-scale')['rows']}
        shared = sorted(set(left) & set(right))
        mismatches = [(key, left[key]['native'], right[key]['native']) for key in shared
                      if left[key]['native'] != right[key]['native']]
        checks['zmax_invariance'] = dict(
            compared_points=len(shared), bit_identical=not mismatches,
            mismatches=mismatches[:5],
            basis='same normalized coordinate with maximum_z 1.0 versus 5.8')
    tenth = records.get('probe637-monomials')
    if tenth and unit:
        small = {(row['degree'], round(row['normalized_coordinate'], 12)): row for row in probe_conditions(tenth, 'probe637-monomials')['rows']}
        large = {(row['degree'], round(row['normalized_coordinate'], 12)): row for row in probe_conditions(unit, 'probe638-unit-monomials')['rows']}
        # Ratios are only meaningful where the unit-amplitude residual is well above
        # double rounding of the returned index (2.2e-16); otherwise skip the point.
        pairs = [(key, small[key]['residual'], large[key]['residual']) for key in sorted(set(small) & set(large))
                 if abs(large[key]['residual']) >= 1e-11]
        if pairs:
            ratios = [residual / large_residual for _, residual, large_residual in pairs]
            checks['amplitude_scaling'] = dict(
                compared_points=len(pairs),
                skipped_points=len(small) - len(pairs),
                ratio_min=min(ratios), ratio_max=max(ratios),
                maximum_absolute_extra_residual=max(abs(residual - 0.1 * large_residual)
                                                    for _, residual, large_residual in pairs),
                basis='amplitude 0.1 versus 1.0 at the same normalized coordinate; points with |unit residual| < 1e-11 skipped')
    return checks
