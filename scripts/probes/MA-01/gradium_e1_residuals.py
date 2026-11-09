import sys
from pathlib import Path
_workspace = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(_workspace), str(_workspace / "src")]
"""E1 offline replay of the retained 637-639 monomial records (no native instance).

Recomputes every retained point with exact rational arithmetic, separates the
coordinate conversion, coefficient order, evaluation algorithm, text precision
and dispersion explanations, and writes a residual table plus the H-A/H-B/H-C
verdicts for the implementation report.

Usage:
    python scripts/probes/MA-01/gradium_e1_residuals.py [output-directory]
"""
import json
from pathlib import Path

from tests.support.gradium_reference import (
    LOW_ORDER_MAX_RESIDUAL,
    PROBE_RECORDS,
    hypothesis_verdicts,
    load_probe_record,
    probe_conditions,
    residual_report,
)


def main(output=None):
    records = {name: load_probe_record(name) for name in PROBE_RECORDS}
    table = residual_report(records)
    verdicts = hypothesis_verdicts(records)
    detail = {name: probe_conditions(record, name) for name, record in records.items()}
    artifact = dict(
        experiment='E1 exact offline residual replay of 637-639',
        inputs={name: PROBE_RECORDS[name] for name in records},
        gates=dict(curve_atol=1e-10, curve_rtol=1e-9,
                   low_order_maximum_residual=LOW_ORDER_MAX_RESIDUAL,
                   note='original gates retained; E1 adds no tolerance'),
        conditions={name: dict(amplitude=detail[name]['amplitude'], maximum_z=detail[name]['maximum_z'])
                    for name in detail},
        residual_table=table,
        per_point={name: detail[name]['rows'] for name in detail},
        verdicts=verdicts,
    )
    folder = Path(output).resolve() if output else _workspace / '.local' / 'gradium'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'e1-residuals.json'
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(f'E1 artifact: {path}')
    print('degree  max|residual|  (record, normalized coordinate)')
    for row in table:
        if row['degree'] in (0, 5, 8, 9, 10, 11):
            print(f"  {row['degree']:>2}  {row['maximum_absolute_residual']:.6e}  "
                  f"({row['record']}, u={row['at_normalized_coordinate']:.2f}, amp={row['amplitude']})")
    print()
    print('low-order (0..9) maximum residual:', f"{verdicts['low_order_maximum_residual']:.6e}",
          '<= bound', f"{LOW_ORDER_MAX_RESIDUAL:.6e}", '->',
          verdicts['low_order_matches_exact_polynomial'])
    print('H-B (text precision / coefficient order) refuted:', verdicts['h_b_text_or_coefficient_order_refuted'])
    print('H-A status:', verdicts['h_a_status'])
    print('H-C status:', verdicts['h_c_status'])
    zmax = verdicts.get('zmax_invariance', {})
    print('zmax invariance:', zmax.get('compared_points'), 'points, bit identical =', zmax.get('bit_identical'))
    scale = verdicts.get('amplitude_scaling', {})
    if scale:
        print('amplitude scaling 0.1/1.0:', f"{scale['ratio_min']:.9f}..{scale['ratio_max']:.9f}",
              'max extra residual', f"{scale['maximum_absolute_extra_residual']:.3e}")
    return artifact


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
