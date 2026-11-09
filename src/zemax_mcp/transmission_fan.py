"""Selectable transmission fans using formal normalized polarized ray tracing."""
import math
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .errors import ZemaxError
from .schema import FiniteFloat, Index, Request


class FanJones(Request):
    jx: Annotated[FiniteFloat, Field(ge=0)] = 1
    jy: Annotated[FiniteFloat, Field(ge=0)] = 0
    x_phase: FiniteFloat = 0
    y_phase: FiniteFloat = 0

    @model_validator(mode='after')
    def nonzero_input(self):
        if self.jx == self.jy == 0:
            raise ValueError('Jones输入至少一个振幅非零。')
        return self


class PolarizationTransmissionFan(Request):
    kind: Literal['polarization_transmission_fan']
    method: Literal['auto', 'native', 'ray_trace'] = 'auto'
    field: Index = 0
    wavelength: Index = 0
    sampling: Annotated[int, Field(strict=True, ge=3, le=1001)] = 201
    polarization: FanJones | None = None

    @model_validator(mode='after')
    def odd_sampling(self):
        if self.sampling % 2 != 1:
            raise ValueError('sampling须为3至1001的奇数。')
        return self


def uses_batch(q):
    explicit = q.model_fields_set & {'field', 'wavelength', 'sampling', 'polarization'}
    if q.method == 'native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING', '本机TransmissionFan原生专题没有选择设置的采用回读。', settings=sorted(explicit))
    return q.method == 'ray_trace' or q.method == 'auto' and bool(explicit)


def transmission_fan(backend, q):
    from .field_analyses import normalized_field
    from .models import BatchRays

    backend._require_sequential()
    settings = backend.get_system_settings(None)
    fields, waves = settings['fields'], settings['wavelengths']
    if q.field > len(fields) or q.wavelength > len(waves):
        raise ZemaxError('INDEX_OUT_OF_RANGE', '视场或波长编号越界。')
    fields = [f for f in fields if not q.field or f['number'] == q.field]
    waves = [w for w in waves if not q.wavelength or w['number'] == q.wavelength]
    if not fields or not waves:
        raise ZemaxError('NO_RESULT_DATA', '没有可用的视场或波长。')
    if q.polarization is None:
        inputs = [dict(jx=1., jy=0., x_phase=0., y_phase=0.), dict(jx=0., jy=1., x_phase=0., y_phase=0.)]
    else:
        scale = max(q.polarization.jx, q.polarization.jy)
        nx, ny = q.polarization.jx / scale, q.polarization.jy / scale
        norm = math.hypot(nx, ny)
        inputs = [dict(jx=nx / norm, jy=ny / norm,
                       x_phase=q.polarization.x_phase, y_phase=q.polarization.y_phase)]
    image = int(backend.system.LDE.NumberOfSurfaces) - 1

    def flow(task):
        actual = dict(field_numbers=[f['number'] for f in fields], wavelength_numbers=[w['number'] for w in waves],
            fields=fields, wavelengths=waves, sampling=q.sampling, target_surface=image,
            configuration=settings['configuration'], field_normalization=settings['field_normalization'],
            polarization_inputs=inputs, input_normalization='unit incident intensity',
            settings_source='system readback and formal CreateNormPol/AddRay arguments')
        task['payload'] = dict(analysis_kind=q.kind, computation_method='native_batch_polarized_ray_trace',
            actual_settings=actual, polarization='unpolarized' if q.polarization is None else 'Jones',
            intensity_unit='dimensionless normalized intensity', wavelengths_um=[w['wavelength_um'] for w in waves],
            fan_axes=dict(sagittal='normalized pupil X', tangential='normalized pupil Y'),
            series=[], grids=[], structured_data_available=True, ray_trace_tasks=[],
            resource_lifecycle='Each child batch closes its owned native tool in finally; close failures fail the child',
            fallback_reason='Installed TransmissionFan settings have no selectable input readback' if q.method == 'auto' else None)
        jobs = [(f, fan) for f in fields for fan in ['tangential', 'sagittal']]
        for job_number, (field, fan) in enumerate(jobs):
            backend._cancel_boundary(task)
            hx, hy = normalized_field(settings['fields'], field, settings['field_normalization'])
            pupils = [-1 + 2 * i / (q.sampling - 1) for i in range(q.sampling)]
            output = [[] for _ in pupils]
            for wave in waves:
                rays = [dict(hx=hx, hy=hy, px=p if fan == 'sagittal' else 0.,
                             py=p if fan == 'tangential' else 0., wavelength=wave['number']) for p in pupils]
                geometric = yield from backend._child_job(task, backend.run_batch_ray_trace,
                    BatchRays(rays=rays, target_surface=image))
                task['payload']['ray_trace_tasks'].append(geometric.get('task', {}).get('task_id'))
                traces = []
                for polarization in inputs:
                    trace = yield from backend._child_job(task, backend.run_batch_ray_trace,
                        BatchRays(rays=rays, target_surface=image, polarization=polarization))
                    task['payload']['ray_trace_tasks'].append(trace.get('task', {}).get('task_id'))
                    traces.append(trace['rows'])
                if len(geometric['rows']) != len(pupils) or any(len(t) != len(pupils) for t in traces):
                    raise ZemaxError('INVALID_RESULT_DATA', '透射扇图追迹行数不匹配。')
                for i, geometry in enumerate(geometric['rows']):
                    sample = [t[i] for t in traces]
                    valid = geometry['state'] == 'succeeded' and all(r['state'] == 'succeeded' for r in sample)
                    intensity = sum(r['intensity'] for r in sample) / len(sample) if valid else None
                    if intensity is not None and (not math.isfinite(intensity) or intensity < 0):
                        raise ZemaxError('INVALID_RESULT_DATA', '原生偏振追迹返回无效强度。', pupil=i, wavelength=wave['number'])
                    output[i].append(dict(value=intensity, geometry_state=geometry['state'],
                        error_code=geometry.get('error_code'), vignette_code=geometry.get('vignette_code'),
                        polarization_error_codes=[r.get('error_code') for r in sample]))
                task['payload']['series'].append(dict(series=len(task['payload']['series']),
                    description=f'{fan} transmission at field {field["number"]}', fan=fan,
                    field_number=field['number'], field_position=dict(x=field['x'], y=field['y']),
                    wavelength_number=wave['number'], wavelength_um=wave['wavelength_um'],
                    x_label='Normalized pupil', x_unit='normalized pupil', labels=['Normalized intensity'],
                    y_unit='dimensionless normalized intensity', x=pupils,
                    y=[[samples[-1]['value']] for samples in output],
                    invalid_count=sum(samples[-1]['value'] is None for samples in output)))
            for i, pupil in enumerate(pupils):
                task['rows'].append(dict(index=len(task['rows']), fan=fan, field_number=field['number'],
                    field_position=dict(x=field['x'], y=field['y']), pupil=pupil,
                    wavelengths_um=[w['wavelength_um'] for w in waves], transmission=[v['value'] for v in output[i]],
                    invalid_count=sum(v['value'] is None for v in output[i]), ray_status=output[i]))
            task['progress'] = int(100 * (job_number + 1) / len(jobs))
            yield
    return backend._composite(q.kind, q.model_dump(), flow)
