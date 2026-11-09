"""Selectable single-mode fiber coupling through the documented FICL operand."""
import math

from .errors import ZemaxError

SELECTORS = {'sampling', 'field', 'wavelength', 'ignore_source', 'source_na',
             'receiver_na', 'integration', 'use_polarization'}


def uses_operand(q):
    explicit = q.model_fields_set & SELECTORS
    if q.method == 'native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING', '原生光纤专题未提供所选参数的正式设置回读。', settings=sorted(explicit))
    return q.method == 'operand' or q.method == 'auto' and bool(explicit)


def run_fiber_operand(backend, q):
    backend._require_sequential()
    settings = backend.get_system_settings(None)
    if q.field > len(settings['fields']) or q.wavelength > len(settings['wavelengths']):
        raise ZemaxError('INDEX_OUT_OF_RANGE', '视场或波长编号越界。')
    sample = {32: 1, 64: 2, 128: 3, 256: 4}[q.sampling]
    offset = int(q.integration == 'huygens')
    parameters = [sample, q.wavelength, float(q.field), float(q.ignore_source),
                  q.source_na, q.receiver_na, float(offset), float(q.use_polarization)]
    code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, 'FICL')

    def flow(task):
        payload = dict(analysis_kind=q.kind, computation_method='native_FICL_GetOperandValue',
            selection=dict(method='operand', requested_method=q.method),
            integration_method=q.integration, actual_settings=dict(
                sampling=q.sampling, sampling_code=sample, field=settings['fields'][q.field - 1],
                wavelength=settings['wavelengths'][q.wavelength - 1],
                ignore_source=q.ignore_source, source_na=q.source_na, receiver_na=q.receiver_na,
                use_polarization=q.use_polarization, configuration=settings['configuration'],
                input_source='formal FICL call arguments; no analysis-window setting mutation'),
            native_queries=[], series=[], grids=[], units=dict(efficiency='dimensionless fraction',
                amplitude='dimensionless complex coupling amplitude', na='dimensionless'),
            structured_data_available=True,
            scope='FICL circular fibers and native default alignment; dedicated tilt/decenter/elliptical NA are not parameters of this operand',
            definition_source='OpticStudio 2024 R2 manual pp.1116-1117')
        task['payload'] = payload
        values = {}
        for index, name in enumerate(('power', 'real', 'imaginary')):
            backend._cancel_boundary(task)
            args = list(parameters)
            args[6] = float(offset + 2 * index)
            value = float(backend.system.MFE.GetOperandValue(code, *args))
            payload['native_queries'].append(dict(operand='FICL', arguments=args, value=value))
            if not math.isfinite(value):
                raise ZemaxError('INVALID_RESULT_DATA', 'FICL返回非有限结果。', quantity=name, value=str(value))
            values[name] = value
            task['rows'].append(dict(index=index, quantity=name, value=value))
            task['progress'] = (index + 1) * 30
            yield
        payload['efficiencies'] = dict(total_coupling=values['power'])
        payload['coupling_amplitude'] = dict(real=values['real'], imaginary=values['imaginary'])
        payload['consistency'] = dict(power_from_amplitude=values['real'] ** 2 + values['imaginary'] ** 2,
            residual=values['power'] - values['real'] ** 2 - values['imaginary'] ** 2,
            definition='power equals squared modulus of complex coupling amplitude')

    return backend._composite(q.kind, q.model_dump(), flow)
