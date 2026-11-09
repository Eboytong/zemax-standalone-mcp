"""Axial Cooke control: separate geometric propagation from polarized phase."""
import cmath
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'src')]

from phase_aberration_reference import native_points, batch_request, WAVE_ATOL
from phase_reference_diagnostics import diagnose
from probe_common import adapter, paged_result, poll_task


def global_position(matrix, point):
    return [sum(matrix[3 * i + j] * point[j] for j in range(3)) + matrix[9 + i]
            for i in range(3)]


def propagation_differences(positions, indices, incident_direction=(0., 0., 1.), *,
                            initial_reference='wave_normal'):
    """Incident plane wave at surface 1, followed by real ray segments.

    positions[s][ray] are global coordinates; indices[s] is the index in the
    medium before positions[s], so indices[0] is the incident medium.
    """
    if not positions or len(indices) != len(positions):
        raise ValueError('surface positions and preceding-medium indices must match')
    if len(incident_direction) != 3 or any(not math.isfinite(v) for v in incident_direction):
        raise ValueError('incident direction must contain three finite cosines')
    if not math.isclose(math.hypot(*incident_direction), 1., rel_tol=0, abs_tol=1e-12):
        raise ValueError('incident direction must be a unit vector')
    if initial_reference not in ('wave_normal', 'local_z_launch'):
        raise ValueError('unknown initial reference plane')
    if initial_reference == 'local_z_launch' and abs(incident_direction[2]) <= 1e-12:
        raise ValueError('a local-Z launch plane requires nonzero axial direction')
    count = len(positions[0])
    if not count or any(len(p) != count for p in positions):
        raise ValueError('every surface must contain the same ordered rays')
    if initial_reference == 'wave_normal':
        paths = [indices[0] * math.fsum(a * b for a, b in zip(p, incident_direction))
                 for p in positions[0]]
    else:
        # Relative ray travel from a common Z plane. Its constant location
        # cancels when subtracting the chief. Keep the wave-normal prediction
        # available separately; this is an explicit launch-phase hypothesis.
        paths = [indices[0] * p[2] / incident_direction[2] for p in positions[0]]
    for i in range(1, len(positions)):
        for ray in range(count):
            paths[ray] += indices[i] * math.dist(positions[i - 1][ray], positions[i][ray])
    return paths


def compare_phase(points, rows, paths, wavelength_mm, count_per_section=401):
    if len(points) != len(rows) or len(paths) != len(rows):
        raise ValueError('phase, trace and path counts must match')
    output = []
    for start in range(0, len(points), count_per_section):
        chief = min(range(start, start + count_per_section), key=lambda k: abs(points[k]['pupil']))
        for component in ('x', 'y'):
            def field(index):
                e = rows[index]['electric_field']
                return complex(e[f'e{component}_real'], e[f'e{component}_imag'])
            ref = field(chief)
            values = []
            missing = 0
            for i in range(start, start + count_per_section):
                value = field(i)
                if abs(ref) <= 1e-12 or abs(value) <= 1e-12:
                    missing += 1
                    continue
                native = points[i][f'{component}_phase']
                raw = cmath.phase(value / ref) / (2 * math.pi)
                propagation = (paths[i] - paths[chief]) / wavelength_mm
                residuals = {str(sign): math.remainder(raw + sign * propagation - native, 1.)
                             for sign in (-1, 1)}
                reversed_native = {str(sign): math.remainder(raw + sign * propagation + native, 1.)
                                   for sign in (-1, 1)}
                values.append(dict(pupil=points[i]['pupil'], native=native, raw=raw,
                    propagation_waves=propagation, residuals=residuals,
                    reversed_native_residuals=reversed_native))
            maxima = {str(sign): max((abs(v['residuals'][str(sign)]) for v in values), default=None)
                      for sign in (-1, 1)}
            output.append(dict(section=points[start]['section'], component=component,
                indeterminate=missing, compared=len(values), maximum_errors_waves=maxima,
                tolerance_waves=WAVE_ATOL,
                reversed_native_sign_maximum_errors={str(sign): max(
                    (abs(v['reversed_native_residuals'][str(sign)]) for v in values), default=None)
                    for sign in (-1, 1)},
                passed={sign: error is not None and error <= WAVE_ATOL for sign, error in maxima.items()},
                points=values))
    return output


def run(folder):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    receipts = []
    call = adapter(backend, receipts)
    result = dict(assumptions=['axial Angle field (0,0)', 'parallel incident rays along global +Z',
                              'no reflections in the controlled Cooke model'], calls=receipts)
    def finish(task):
        task = poll_task(call, task, result, 120)
        if task['state'] != 'succeeded':
            raise RuntimeError(task)
        return paged_result(call, task['task_id'], result)
    try:
        call('connect')
        from System import Array, Double
        model = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        call('open_lens', dict(path=str(model)))
        baseline = call('get_system_settings')
        surfaces = call('get_surfaces', dict(start=0, count=100))
        result.update(baseline=baseline, surfaces=surfaces)
        native = finish(call('run_analysis', dict(request=dict(kind='phase_aberration'))))
        result['phase_header'] = native['input_header']
        if baseline['field_type'] != 'Angle' or baseline['fields'][0]['x'] != 0 or baseline['fields'][0]['y'] != 0:
            raise ValueError('control requires an axial angle field')
        _, points = native_points(native)
        wave = next(w for w in baseline['wavelengths'] if abs(w['wavelength_um'] - .55) < 1e-9)
        request = batch_request(points, wave['number'])
        polarized = finish(call('run_batch_ray_trace', dict(request=request)))
        positions, previous_indices, native_geometry = [], [], []
        image = int(backend.system.LDE.NumberOfSurfaces) - 1
        nw = len(baseline['wavelengths'])
        for surface in range(1, image + 1):
            trace = finish(call('run_batch_ray_trace', dict(request=dict(
                rays=request['rays'], target_surface=surface))))
            if len(trace['rows']) != len(points) or any(row['state'] != 'succeeded' for row in trace['rows']):
                raise ValueError(f'geometry trace incomplete at surface {surface}')
            matrix = backend.system.LDE.GetGlobalMatrix(surface)
            if not matrix[0]:
                raise ValueError(f'global matrix unavailable at surface {surface}')
            transform = [float(v) for v in matrix[1:]]
            positions.append([global_position(transform, row['position']) for row in trace['rows']])
            indices = Array[Double]([0.] * nw)
            count = int(backend.system.LDE.GetIndex(surface - 1, nw, indices))
            previous_indices.append(float(indices[wave['number'] - 1]))
            native_geometry.append(dict(surface=surface, matrix=transform, index_surface=surface - 1,
                get_index_return=count, indices=[float(v) for v in indices]))
        result['geometry'] = native_geometry
        result['optical_paths_mm'] = propagation_differences(positions, previous_indices)
        result['comparisons'] = compare_phase(points, polarized['rows'], result['optical_paths_mm'], wave['wavelength_um'] * .001)
        result['neighbor_reference_diagnostics'] = [diagnose(c) for c in result['comparisons']]
        result['model_settings_preserved'] = call('get_system_settings') == baseline
        result['model_surfaces_preserved'] = call('get_surfaces', dict(start=0, count=100)) == surfaces
    except BaseException as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        result['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        (folder / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([dict(section=c['section'], component=c['component'], errors=c['maximum_errors_waves'], passed=c['passed'])
                      for c in result['comparisons']]))


if __name__ == '__main__':
    run(sys.argv[1])
