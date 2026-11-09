"""Serial Cooke controls for off-axis and nonzero X/Y polarized phase.

Each controlled input is a model edit in a working copy. It does not expose
analysis selectors or claim a general replacement for the native topic.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'src')]

from phase_aberration_reference import native_points
from phase_propagation_reference import global_position, propagation_differences, compare_phase
from phase_reference_diagnostics import diagnose
from probe_common import adapter, paged_result, poll_task
from zemax_mcp.field_analyses import normalized_field
from zemax_mcp.models import BatchRays, SystemPatch


CASES = (
    dict(name='axis_circular', field_y=0., wavelength_um=.55, jx=1., jy=1., y_phase=90.),
    dict(name='offaxis_y', field_y=5., wavelength_um=.55, jx=0., jy=1., y_phase=0.),
    dict(name='offaxis_circular', field_y=5., wavelength_um=.55, jx=1., jy=1., y_phase=90.),
    dict(name='offaxis_second_wave', field_y=5., wavelength_um=.4861327, jx=1., jy=1., y_phase=90.),
)


def incident_direction(field):
    direction = [math.tan(math.radians(field['x'])), math.tan(math.radians(field['y'])), 1.]
    norm = math.hypot(*direction)
    return [v / norm for v in direction]


def settings_patch(baseline, case):
    fields = [{k: v for k, v in f.items() if k != 'number'} for f in baseline['fields']]
    fields[0].update(x=0., y=case['field_y'])
    return SystemPatch(fields=fields, wavelengths=[dict(wavelength_um=case['wavelength_um'])],
                       primary_wavelength=1, polarization=dict(unpolarized=False,
                       jx=case['jx'], jy=case['jy'], x_phase=0., y_phase=case['y_phase']))


def trace_request(points, settings, jones):
    field = settings['fields'][0]
    hx, hy = normalized_field(settings['fields'], field, settings['field_normalization'])
    rays = [dict(hx=hx, hy=hy, px=p['pupil'] if p['section']=='sagittal' else 0.,
                 py=p['pupil'] if p['section']=='tangential' else 0., wavelength=1) for p in points]
    return BatchRays(rays=rays, polarization=jones)


def summarize(case):
    return dict(name=case['input']['name'], error=case.get('error'),
                model_settings_preserved=case.get('model_settings_preserved'),
                model_surfaces_preserved=case.get('model_surfaces_preserved'),
                restoration=case.get('restoration'),
                comparisons=[{k: v for k, v in c.items() if k != 'points'}
                             for c in case.get('neighbor_reference_diagnostics', [])],
                ray_launch_comparisons=[{k: v for k, v in c.items() if k != 'points'}
                             for c in case.get('ray_launch_reference_diagnostics', [])])


def run(folder):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    receipts = []
    call = adapter(backend, receipts)
    result = dict(calls=receipts, cases=[], controlled_scope='infinite object, Angle fields, no mirrors')
    model = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'

    def finish(task, record):
        task = poll_task(call, task, record, 120)
        if task['state'] != 'succeeded':
            raise RuntimeError(task)
        return paged_result(call, task['task_id'], record)

    try:
        call('connect')
        from System import Array, Double
        for case in CASES:
            record = dict(input=case)
            result['cases'].append(record)
            call('open_lens', dict(path=str(model)))
            original = call('get_system_settings')
            original_surfaces = call('get_surfaces', dict(start=0, count=100))
            try:
                patch = settings_patch(original, case)
                record['patch'] = patch.model_dump(exclude_unset=True)
                call('update_system_settings', dict(settings=record['patch']))
                settings = call('get_system_settings')
                surfaces = call('get_surfaces', dict(start=0, count=100))
                record.update(settings=settings, surfaces=surfaces)
                if settings['field_type'] != 'Angle' or settings['fields'][0]['x'] != 0.:
                    raise ValueError('control requires an Angle field in the Y-Z plane')
                field = settings['fields'][0]
                if field['y'] != case['field_y'] or settings['wavelengths'][0]['wavelength_um'] != case['wavelength_um']:
                    raise ValueError('controlled system field/wavelength was not adopted')
                native = finish(call('run_analysis', dict(request=dict(kind='phase_aberration'))), record)
                header = native['input_header']
                record['phase_header'] = header
                expected = dict(jx=case['jx'], jy=case['jy'], x_phase_deg=0., y_phase_deg=case['y_phase'])
                if header['jones'] != expected or header['field_position']['y'] != case['field_y']:
                    raise ValueError('native topic did not use the controlled field/Jones input')
                if abs(header['wavelength_um']-case['wavelength_um']) > .00005:
                    raise ValueError('native topic wavelength differs beyond header rounding')
                _, points = native_points(native)
                jones = dict(jx=case['jx'], jy=case['jy'], x_phase=0., y_phase=case['y_phase'])
                request = trace_request(points, settings, jones)
                polarized = finish(call('run_batch_ray_trace', dict(request=request.model_dump())), record)
                if len(polarized['rows']) != len(points) or any(r['state']!='succeeded' for r in polarized['rows']):
                    raise ValueError('polarized reference has failed or missing rays')
                positions, indices, geometry = [], [], []
                image = int(backend.system.LDE.NumberOfSurfaces)-1
                for surface in range(1, image+1):
                    geometry_request = BatchRays(rays=request.rays, target_surface=surface)
                    traced = finish(call('run_batch_ray_trace', dict(request=geometry_request.model_dump())), record)
                    if len(traced['rows'])!=len(points) or any(r['state']!='succeeded' for r in traced['rows']):
                        raise ValueError(f'geometry trace incomplete at surface {surface}')
                    matrix = backend.system.LDE.GetGlobalMatrix(surface)
                    if not matrix[0]:
                        raise ValueError('native global transform unavailable')
                    transform = [float(v) for v in matrix[1:]]
                    positions.append([global_position(transform,r['position']) for r in traced['rows']])
                    wavelengths = Array[Double]([0.])
                    count = int(backend.system.LDE.GetIndex(surface-1,1,wavelengths))
                    indices.append(float(wavelengths[0]))
                    geometry.append(dict(surface=surface,matrix=transform,index_surface=surface-1,
                                         get_index_return=count,index_before=indices[-1]))
                direction = incident_direction(field)
                paths = propagation_differences(positions,indices,direction)
                record.update(geometry=geometry,incident_direction=direction,optical_paths_mm=paths)
                record['comparisons'] = compare_phase(points,polarized['rows'],paths,case['wavelength_um']*.001)
                record['neighbor_reference_diagnostics'] = [diagnose(c) for c in record['comparisons']]
                launch_paths = propagation_differences(positions,indices,direction,initial_reference='local_z_launch')
                record['ray_launch_optical_paths_mm'] = launch_paths
                record['ray_launch_comparisons'] = compare_phase(points,polarized['rows'],launch_paths,case['wavelength_um']*.001)
                record['ray_launch_reference_diagnostics'] = [diagnose(c) for c in record['ray_launch_comparisons']]
                record['model_settings_preserved'] = call('get_system_settings') == settings
                record['model_surfaces_preserved'] = call('get_surfaces',dict(start=0,count=100)) == surfaces
            except Exception as exc:
                record['error'] = dict(type=type(exc).__name__,message=str(exc))
            finally:
                try:
                    call('open_lens',dict(path=str(model)))
                    record['restoration'] = dict(settings=call('get_system_settings')==original,
                        surfaces=call('get_surfaces',dict(start=0,count=100))==original_surfaces)
                except Exception as exc:
                    record['restoration'] = dict(error=repr(exc))
                (folder/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(summarize(record),ensure_ascii=False),flush=True)
            if record['restoration'] != dict(settings=True,surfaces=True):
                raise RuntimeError('baseline restoration failed; serial controls stopped')
    finally:
        backend.shutdown()
        receipt=folder/'state/close_receipt.json'
        result['close_receipt']=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        (folder/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    run(sys.argv[1])
