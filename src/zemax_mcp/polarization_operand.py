"""Selectable polarized ray data through the documented CODA operand."""

import math

from .errors import ZemaxError

SELECTORS = {'field', 'wavelength', 'surface', 'pupil_x', 'pupil_y'}
DATA = {
    's_reflectance': -1, 's_transmittance': -2, 's_absorption': -3,
    's_transmission_amplitude_real': -4, 's_transmission_amplitude_imag': -5,
    's_reflection_amplitude_real': -6, 's_reflection_amplitude_imag': -7,
    'p_reflectance': 1, 'p_transmittance': 2, 'p_absorption': 3,
    'p_transmission_amplitude_real': 4, 'p_transmission_amplitude_imag': 5,
    'p_reflection_amplitude_real': 6, 'p_reflection_amplitude_imag': 7,
    'ex_real': 101, 'ex_imag': 102, 'ey_real': 103, 'ey_imag': 104,
    'ez_real': 105, 'ez_imag': 106, 'phase_xy_deg': 110,
    'phase_x_deg': 111, 'phase_y_deg': 112, 'phase_z_deg': 113,
    'polarized_transmitted_intensity': 0, 'unpolarized_transmitted_intensity': 8,
    'ellipse_major_axis': 121, 'ellipse_minor_axis': 122, 'ellipse_angle_deg': 123,
}
PHASE_CODES_RADIANS = frozenset((110, 111, 112, 113))


def uses_operand(q):
    explicit = q.model_fields_set & SELECTORS
    if q.method == 'native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING', '原生PolarizationRayTrace未提供请求光线选择器。', settings=sorted(explicit))
    return q.method == 'operand' or q.method == 'auto' and bool(explicit)


def run_polarization_operand(backend, q):
    backend._require_sequential()
    settings = backend.get_system_settings(None)
    surfaces = int(backend.system.LDE.NumberOfSurfaces)
    if q.field > len(settings['fields']) or q.wavelength > len(settings['wavelengths']):
        raise ZemaxError('INDEX_OUT_OF_RANGE', '视场或波长编号越界。')
    if q.surface >= surfaces:
        raise ZemaxError('INDEX_OUT_OF_RANGE', '曲面编号越界。', surface=q.surface, count=surfaces)
    field = settings['fields'][q.field - 1]
    wave = settings['wavelengths'][q.wavelength - 1]
    code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, 'CODA')
    args_base = [q.surface, q.wavelength, q.field, 0, q.pupil_x, q.pupil_y, 0., 0.]

    def flow(task):
        payload = dict(analysis_kind=q.kind, computation_method='native_CODA_GetOperandValue',
            selection=dict(method='operand', requested_method=q.method),
            actual_settings=dict(field=field, wavelength=wave, surface=q.surface,
                surface_definition='Surf=0 selects image surface; positive values are sequential surface numbers',
                pupil=dict(x=q.pupil_x, y=q.pupil_y, coordinate='normalized pupil'),
                jones=settings['polarization'], configuration=settings['configuration'],
                data_codes=DATA, input_source='formal CODA parameters and current system Jones state'),
            data_source='OpticStudio 2024 R2 manual p.1130; CODA row headers and values verified natively',
            native_phase_unit='radians',
            native_ellipse_angle_unit='degrees',
            units=dict(pupil='normalized pupil', phase='degrees', intensity='relative fraction',
                field='native normalized complex electric field'), series=[], grids=[],
            structured_data_available=True)
        task['payload'] = payload
        for name, data in DATA.items():
            backend._cancel_boundary(task)
            args = list(args_base)
            args[3] = data
            value = float(backend.system.MFE.GetOperandValue(code, *args))
            if not math.isfinite(value):
                raise ZemaxError('INVALID_RESULT_DATA', 'CODA返回非有限结果。', quantity=name, value=str(value))
            payload['native_queries'] = payload.get('native_queries', [])
            payload['native_queries'].append(dict(operand='CODA', arguments=args, value=value))
            task['rows'].append(dict(quantity=name, value=math.degrees(value) if data in PHASE_CODES_RADIANS else value,
                                     unit='degrees' if name.endswith('_deg') else 'dimensionless'))
            task['progress'] = int(100 * len(task['rows']) / len(DATA))
            yield

    return backend._composite(q.kind, q.model_dump(exclude_unset=True), flow)
