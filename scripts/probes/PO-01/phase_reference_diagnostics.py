"""Compare retained phase traces using independently constructed references.

The 2024 R2 manual, Phase Aberration discussion (printed p.904), describes
interpolating the chief phase from two rays on its sides. Both candidates are
reported; neither the offset nor the sign is fitted to native table values.
This is an offline diagnostic, not a replacement for the native analysis.
"""
from __future__ import annotations

import argparse
import cmath
import json
import math
from pathlib import Path


TOLERANCE_WAVES = 1e-6 / 360


def diagnose(comparison, tolerance=TOLERANCE_WAVES):
    """Use raw complex-field phase plus independently traced propagation.

    The signs are the previously investigated raw + propagation + native
    combination. The neighboring-reference candidate keeps that sign fixed.
    A zero-amplitude component stays indeterminate. The chief table row is
    reported separately because its native zero is a reference marker.
    """
    points = comparison['points']
    result = dict(section=comparison['section'], component=comparison['component'],
                  tolerance_waves=tolerance,
                  indeterminate=comparison.get('indeterminate', 0))
    if not points:
        return dict(result, status='indeterminate', compared=0)
    if any(not all(math.isfinite(p[k]) for k in
                   ('pupil', 'raw', 'propagation_waves', 'native')) for p in points):
        raise ValueError('phase diagnostics require finite inputs')
    if any(a['pupil'] >= b['pupil'] for a, b in zip(points, points[1:])):
        raise ValueError('pupil points must be strictly increasing')
    chief = [i for i, p in enumerate(points) if p['pupil'] == 0]
    if len(chief) != 1 or chief[0] in (0, len(points) - 1):
        raise ValueError('an interior chief point and two adjacent rays are required')
    center = chief[0]
    left, right = points[center - 1], points[center + 1]
    if not math.isclose(left['pupil'], -right['pupil'], rel_tol=0, abs_tol=1e-12):
        raise ValueError('the two adjacent pupil coordinates must be symmetric')
    independent = lambda p: p['raw'] + p['propagation_waves']
    lo, hi = independent(left), independent(right)
    # Circular interpolation avoids averaging +0.499 and -0.499 to zero.
    vector = cmath.exp(2j * math.pi * lo) + cmath.exp(2j * math.pi * hi)
    if abs(vector) <= 1e-12:
        raise ValueError('opposite neighbor phases have no unique circular mean')
    reference = cmath.phase(vector) / (2 * math.pi)
    errors = []
    for index, point in enumerate(points):
        if index == center:
            continue
        raw_error = math.remainder(independent(point) + point['native'], 1)
        adjusted = math.remainder(independent(point) - reference + point['native'], 1)
        errors.append(dict(pupil=point['pupil'], native=point['native'],
                           independent_phase_waves=independent(point),
                           chief_error_waves=raw_error,
                           neighbor_error_waves=adjusted))
    chief_max = max(abs(p['chief_error_waves']) for p in errors)
    neighbor_max = max(abs(p['neighbor_error_waves']) for p in errors)
    return dict(result, status='compared', compared=len(errors),
                sign_candidate='raw + propagation + native',
                neighbor_pupils=[left['pupil'], right['pupil']],
                neighbor_reference_waves=reference,
                reference_source='batch complex fields and geometric optical paths only',
                chief_maximum_error_waves=chief_max,
                neighbor_maximum_error_waves=neighbor_max,
                neighbor_candidate_passed=neighbor_max <= tolerance,
                chief_marker=dict(pupil=0., native=points[center]['native'],
                                  is_zero=points[center]['native'] == 0,
                                  included_in_nonchief_error=False),
                points=errors)


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    data = json.loads(source.read_text(encoding='utf-8'))
    results = [diagnose(c) for c in data['comparisons']]
    report = dict(source=str(source), mode='offline retained native data',
                  native_version_source='source probe connect receipt',
                  reference_basis='OpticStudio 2024 R2 manual, Phase Aberration, p.904',
                  tolerance_waves=TOLERANCE_WAVES, comparisons=results,
                  native_session_created=False,
                  source_model_settings_preserved=data.get('model_settings_preserved'),
                  source_model_surfaces_preserved=data.get('model_surfaces_preserved'),
                  source_close_receipt=data.get('close_receipt'))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps([dict((k, v) for k, v in r.items() if k != 'points')
                      for r in results], ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    run(args.source, args.output)
