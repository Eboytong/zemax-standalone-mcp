"""Compare native dispersion text with fixed-step derivatives of native GetIndex.

The candidate steps are fixed before running. No step is fitted to report values.
This diagnostic separates the report's finite-difference behavior from AGF identity
and printed rounding; it does not change the analytic acceptance threshold.
"""
from pathlib import Path
import json
import math
import os
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts/probes/PO-01')]

from probe_common import adapter, paged_result, poll_task, write_json
from tests.support.finite_reference import glass_coefficients, sellmeier
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import SystemPatch

STEPS = (5e-5, 1e-4, 2e-4)
TOLERANCE = 5.1e-8


def wavelength_request(wavelengths):
    return SystemPatch(wavelengths=[dict(wavelength_um=w) for w in wavelengths],
                       primary_wavelength=1).model_dump(exclude_unset=True)


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    os.environ['ZEMAX_STATE_DIR'] = str(folder/'state')
    backend = Backend(Config(Config.from_env().install_dir, folder/'native'))
    receipts = []
    call = adapter(backend, receipts)
    record = dict(probe='native GetIndex fixed-step dispersion identity',
                  source_version='0.1.62 working tree', catalog='SCHOTT', material='BK7G18',
                  candidate_half_steps_um=STEPS, analytic_tolerance=TOLERANCE,
                  derivative_text_tolerance=TOLERANCE, native_index_tolerance=1e-12,
                  note='A passing candidate is a numerical correspondence, not a formal algorithm contract.',
                  calls=receipts, samples=[], cleanup_failures=[])
    snapshot = None
    try:
        call('connect')
        call('new_system')
        baseline = call('get_system_settings')
        before_surfaces = call('get_surfaces', dict(start=0, count=100))
        record['context'] = backend.context()
        record['baseline_settings'] = baseline
        record['baseline_surfaces'] = before_surfaces
        # Capture the native topic before changing a material or wavelength.
        reports = {}
        for kind in ('dispersion_diagram', 'dispersion_vs_wavelength'):
            task = poll_task(call, call('run_analysis', dict(request=dict(kind=kind))), record)
            if task['state'] != 'succeeded':
                raise RuntimeError(dict(kind=kind, task=task))
            reports[kind] = paged_result(call, task['task_id'], record)
        index_curve = reports['dispersion_diagram']['series'][0]
        curve = reports['dispersion_vs_wavelength']['series'][0]
        if curve['x'] != index_curve['x'] or curve['labels'] != index_curve['labels']:
            raise RuntimeError('Native index and derivative axes/identities differ')
        column = curve['labels'].index('BK7G18')
        record['reports'] = reports
        record['coefficients'] = coefficients = glass_coefficients('BK7G18')
        source, work = backend.source_path, backend.work_path
        snapshot = backend._checkpoint('dispersion_step_identity')
        call('update_system_settings', dict(settings=dict(
            material_catalogs=['SCHOTT'], adjust_index_to_environment=False)))
        call('update_surfaces', dict(changes=[dict(surface=1, material='BK7G18', replace_solves=True)]))
        record['actual_material'] = call('get_surfaces', dict(start=1, count=1))
        from System import Array, Double
        for i, wavelength in enumerate(curve['x']):
            # At most seven wavelengths: centre and the three +/- pairs.
            wavelengths = [wavelength]+[wavelength+sign*h for h in STEPS for sign in (-1, 1)]
            call('update_system_settings', dict(settings=wavelength_request(wavelengths)))
            actual = call('get_system_settings')
            if [w['wavelength_um'] for w in actual['wavelengths']] != wavelengths:
                raise RuntimeError('Native wavelength readback differs')
            values = Array[Double]([0.]*len(wavelengths))
            returned = int(backend.system.LDE.GetIndex(1, len(wavelengths), values))
            if returned != len(wavelengths):
                raise RuntimeError(dict(reason='GetIndex count mismatch', expected=len(wavelengths), actual=returned))
            native = [float(v) for v in values]
            if any(not math.isfinite(v) or v <= 0 for v in native):
                raise RuntimeError('Native GetIndex returned invalid values')
            independent = [sellmeier(w, coefficients) for w in wavelengths]
            analytic = -wavelength/independent[0]*sum(
                coefficients[k]*coefficients[k+1]/(wavelength*wavelength-coefficients[k+1])**2
                for k in (0, 2, 4))
            reported = curve['y'][i][column]
            sample = dict(wavelength_um=wavelength, report_derivative=reported,
                          analytic_derivative=analytic, analytic_error=abs(reported-analytic),
                          analytic_passed=abs(reported-analytic) <= TOLERANCE,
                          native_wavelengths_um=wavelengths, native_indices=native,
                          independent_indices=independent, get_index_return=returned,
                          index_max_error=max(abs(a-b) for a,b in zip(native, independent)), candidates=[])
            for j, h in enumerate(STEPS):
                derivative = (native[2+2*j]-native[1+2*j])/(2*h)
                reference = (independent[2+2*j]-independent[1+2*j])/(2*h)
                sample['candidates'].append(dict(half_step_um=h, native_derivative=derivative,
                    independent_derivative=reference, report_error=abs(reported-derivative),
                    native_reference_error=abs(derivative-reference),
                    report_passed=abs(reported-derivative) <= TOLERANCE))
            record['samples'].append(sample)
        record['summary'] = dict(sample_count=len(record['samples']),
            analytic_failure_count=sum(not s['analytic_passed'] for s in record['samples']),
            analytic_max_error=max(s['analytic_error'] for s in record['samples']),
            index_max_error=max(s['index_max_error'] for s in record['samples']),
            candidates=[dict(half_step_um=h,
                passing_count=sum(s['candidates'][j]['report_passed'] for s in record['samples']),
                max_report_error=max(s['candidates'][j]['report_error'] for s in record['samples']),
                max_native_reference_error=max(s['candidates'][j]['native_reference_error'] for s in record['samples']))
                for j,h in enumerate(STEPS)])
    except Exception as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        if snapshot is not None:
            holder = {}
            try:
                backend._restore_model(holder, snapshot, source, work)
                record['restoration'] = holder.get('restoration')
                record['settings_restored'] = call('get_system_settings') == baseline
                record['surfaces_restored'] = call('get_surfaces', dict(start=0, count=100)) == before_surfaces
            except Exception as exc:
                record['cleanup_failures'].append(dict(step='restore', error=repr(exc)))
        try:
            record['disconnect'] = call('disconnect')
        except Exception as exc:
            record['cleanup_failures'].append(dict(step='disconnect', error=repr(exc)))
        write_json(folder/'probe.json', record)
    print(json.dumps(dict(folder=str(folder), summary=record.get('summary'), error=record.get('error'),
        settings_restored=record.get('settings_restored'), surfaces_restored=record.get('surfaces_restored'),
        cleanup_failures=record['cleanup_failures']), ensure_ascii=False))
    return record


if __name__ == '__main__':
    result = run(sys.argv[1])
    if result.get('error') or result['cleanup_failures']:
        sys.exit(1)
