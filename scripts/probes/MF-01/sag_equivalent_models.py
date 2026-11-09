"""Single-variable DSAG/SSAG fit controls for equal analytic sag models."""
import json
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT / 'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.sag_fit import infer_removed_sphere


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(source_root=str(ROOT), cases=[], error=None, calls=[],
                  hypothesis='normalization radius or enabled zero Zernike terms affects fit despite identical sag',
                  reference=dict(sag='0.0126*y**2', slope='0.0252*y',
                                 rms_with_offset_radius=39.84003968804416,
                                 radius_source='progress589 independent 256-node radial-area quadrature',
                                 radius_atol=5e-6, row_atol=1e-8, row_rtol=1e-6))

    def save():
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    def call(name, arguments=None):
        response = backend.dispatch(name, arguments or {})
        record['calls'].append(dict(tool=name, arguments=arguments, response=response))
        save()
        if not response['ok']:
            raise RuntimeError(response)
        return response['data']

    try:
        call('connect')
        native = backend.native.api.Editors.MFE.MeritOperandType
        variants = [('EvenAspheric', None, None), ('ZernikeFringeSag', 1, 5),
                    ('ZernikeFringeSag', 1, 10), ('ZernikeFringeSag', 4, 5)]
        for surface_type, terms, norm in variants:
            call('new_system')
            parameters = {'1': .0001}
            if terms is not None:
                parameters.update({'13': terms, '14': norm, '15': 0})
            call('update_surfaces', dict(changes=[dict(surface=1, surface_type=surface_type,
                radius=40, conic=-1, parameters=parameters, semi_diameter=5,
                thickness=20, replace_solves=True)]))
            case = dict(surface_type=surface_type, terms=terms, normalization_radius=norm,
                        samples=[], queries=[], fits=[])
            record['cases'].append(case)
            before = {key: call(tool) for key, tool in [('surfaces', 'get_surfaces'),
                ('settings', 'get_system_settings'), ('merit', 'get_merit_function')]}
            case['actual_surfaces'] = before['surfaces']
            for i in range(17):
                y = 5 * i / 16
                ok, sag, alternate = backend.system.LDE.GetSag(1, 0., y)
                args = [1, 1, 0., y, 0., 0., 0., 3.]
                slope = float(backend.system.MFE.GetOperandValue(backend.native.enum(native, 'SSLP'), *args))
                expected_sag, expected_slope = .0126*y*y, .0252*y
                case['samples'].append(dict(y=y, native_success=bool(ok), sag=float(sag),
                    alternate=float(alternate), slope=slope, sag_error=abs(sag-expected_sag),
                    slope_error=abs(slope-expected_slope),
                    passed=bool(ok) and abs(sag-expected_sag)<=1e-8+1e-6*abs(expected_sag)
                    and abs(slope-expected_slope)<=1e-8+1e-6*abs(expected_slope)))
            case['geometry_passed'] = all(row['passed'] for row in case['samples'])
            if not case['geometry_passed']:
                save()
                raise ValueError('controlled surface does not match analytic sag/slope')
            for flag in [0, 1, 2, 3]:
                samples = []
                for y in [0., 1., 2.5, 5.]:
                    ok, sag, _ = backend.system.LDE.GetSag(1, 0., y)
                    args = [1, 1, 0., y, 0., 2., float(flag), 0.]
                    removed = float(backend.system.MFE.GetOperandValue(backend.native.enum(native, 'SSAG'), *args))
                    case['queries'].append(dict(operand='SSAG', arguments=args, value=removed))
                    samples.append((y, float(sag), removed))
                fit = infer_removed_sphere(samples, atol=1e-10, rtol=1e-9)
                case['fits'].append(dict(flag=flag, ssag=fit))
                if flag < 3:
                    values = {}
                    for data, key in [(9, 'radius'), (10, 'raw_vertex_z_offset')]:
                        args = [1, 0, data, 1, 0, 2, flag, 0.]
                        value = float(backend.system.MFE.GetOperandValue(backend.native.enum(native, 'DSAG'), *args))
                        values[key] = value
                        case['queries'].append(dict(operand='DSAG', arguments=args, value=value))
                    case['fits'][-1]['dsag'] = values
                    case['fits'][-1]['dsag_ssag_radius_error'] = abs(values['radius'] - fit['radius'])
                if flag == 2:
                    error = abs(fit['radius'] - record['reference']['rms_with_offset_radius'])
                    case['fits'][-1].update(independent_radius_error=error,
                                            independent_radius_passed=error<=5e-6)
                save()
            case['preserved'] = all(call(tool) == before[key] for key, tool in [
                ('surfaces', 'get_surfaces'), ('settings', 'get_system_settings'), ('merit', 'get_merit_function')])
            save()
    except Exception as exc:
        record['error'] = repr(exc)
    finally:
        record['session_id'] = backend.session_id
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else None
        save()
    print(json.dumps(dict(output=str(folder), error=record['error'], cases=[
        {key: value for key, value in case.items() if key not in ['queries', 'samples', 'actual_surfaces']}
        for case in record['cases']], closed=(record.get('close_receipt') or {}).get('native', {}).get('closed')),
        ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])
