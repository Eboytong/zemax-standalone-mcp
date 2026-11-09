"""Separate physical BFS vertex offsets from removed-data piston conventions."""
import json
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.sag_fit import infer_removed_sphere


def run(destination):
    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    result = dict(plan='compare BFSD manufacturing vertex and DSAG local vertex for signed parabolas and both material sides',
                  tolerances=dict(sag_atol=1e-8, sag_rtol=1e-6, radius_mm=5e-6),
                  cases=[], calls=[])

    def save():
        (folder / 'probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    def call(name, arguments=None):
        response = backend.dispatch(name, arguments or {})
        result['calls'].append(dict(tool=name, arguments=arguments, response=response))
        if not response['ok']:
            raise RuntimeError(response)
        return response['data']

    try:
        call('connect')
        result['context'] = backend.context()
        operands = backend.native.api.Editors.MFE.MeritOperandType

        def query(name, values):
            args = list(values) + [0.] * (8 - len(values))
            value = float(backend.system.MFE.GetOperandValue(backend.native.enum(operands, name), *args))
            case['queries'].append(dict(operand=name, arguments=args, value=value))
            return value

        for sign in (1., -1.):
            for side in ('entering', 'exiting'):
                call('new_system')
                call('insert_surfaces', dict(at=1))
                call('update_surfaces', dict(changes=[
                    dict(surface=1, material='N-BK7' if side == 'exiting' else '', thickness=5., replace_solves=True),
                    dict(surface=2, surface_type='EvenAspheric', radius=sign * 40., conic=-1.,
                         parameters={'1': sign * .0001}, semi_diameter=5., thickness=20.,
                         material='N-BK7' if side == 'entering' else '', replace_solves=True)]))
                state = {name: call(name) for name in ('get_system_settings', 'get_surfaces', 'get_merit_function')}
                case = dict(sign=sign, side=side, actual=state, queries=[], criteria=[])
                result['cases'].append(case)
                case['bfsd'] = {name: query('BFSD', [2, code, 0., 5.]) for code, name in enumerate(
                    ('curvature', 'radius', 'vertex_offset', 'maximum_removal_depth', 'removal_volume',
                     'maximum_slope_difference', 'rms_removal_depth', 'rms_slope_difference'))}
                for flag in (0, 1, 2, 3):
                    samples = []
                    for y in (0., 1., 2.5, 5.):
                        ok, sag, _ = backend.system.LDE.GetSag(2, 0., y)
                        expected = sign * .0126 * y * y
                        assert ok and abs(sag - expected) <= 1e-8 + 1e-6 * abs(expected)
                        removed = query('SSAG', [2, 1, 0., y, 0., 2., flag])
                        samples.append((y, float(sag), removed))
                    criterion = dict(flag=flag, sphere=infer_removed_sphere(samples, atol=1e-10, rtol=1e-9),
                                     samples=samples)
                    if flag <= 2:
                        criterion['dsag'] = {name: query('DSAG', [2, 0, data, 1, 0, 2, flag])
                                             for data, name in ((9, 'radius'), (10, 'vertex_z_offset'))}
                    case['criteria'].append(criterion)
                case['preserved'] = {name: call(name) == value for name, value in state.items()}
                assert all(case['preserved'].values())
                save()
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        result['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        save()
    print(json.dumps(dict(error=result.get('error'), cases=[dict(sign=c['sign'], side=c['side'],
        bfsd=c['bfsd'], criteria=c['criteria']) for c in result['cases']],
        closed=(result.get('close_receipt') or {}).get('native', {})), ensure_ascii=False))
    return result


if __name__ == '__main__':
    if run(sys.argv[1]).get('error'):
        sys.exit(1)
