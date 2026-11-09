"""Bounded native FICL controls against independently integrated pupil fields."""
import json
import os
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT), str(ROOT / 'src')]
from probe_common import adapter
from tests.support.fiber_reference import circular_pupil_coupling

TOLERANCE = 5e-4


def run(destination, profile='baseline'):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    if profile not in ('baseline', 'huygens_sampling'):
        raise ValueError('unknown control profile')
    record = dict(calls=[], cases=[], tolerance=TOLERANCE, profile=profile,
                  assumptions=['scalar paraxial Gaussian angular amplitude', 'circular uniform pupil radius .5 mm', 'ideal paraxial lens f=100 mm', 'air, axial field, .55 um, no polarization'])
    call = adapter(backend, record['calls'])

    def save():
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    try:
        call('connect')
        for finite in (False, True):
            call('new_system')
            call('update_system_settings', dict(aperture_value=1., fields=[dict(x=0., y=0.)], wavelengths=[dict(wavelength_um=.55)]))
            distance = 200. if finite else 100.
            changes = [dict(surface=1, surface_type='Paraxial', parameters={'1': 100.}, thickness=distance, semi_diameter=.5, replace_solves=True),
                       dict(surface=2, semi_diameter=5., replace_solves=True)]
            if finite:
                changes.append(dict(surface=0, thickness=200., replace_solves=True))
            call('update_surfaces', dict(changes=changes))
            settings = call('get_system_settings')
            surfaces = call('get_surfaces', dict(start=0, count=100))
            merit = call('get_merit_function')
            case = dict(finite=finite, settings=settings, surfaces=surfaces, merit_before=merit, queries=[])
            record['cases'].append(case)
            code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType, 'FICL')
            base_na = .5 / distance
            scenarios = [(True, base_na, factor * base_na) for factor in (.5, 1., 2.)]
            if finite and profile == 'baseline':
                scenarios += [(False, factor * base_na, base_na) for factor in (.5, 1., 2.)]
            for ignore, source_na, receiver_na in scenarios:
                reference = circular_pupil_coupling(.5, distance, receiver_na, **({} if ignore else dict(object_distance=200., source_na=source_na)))
                for sample in ((1, 2, 3, 4) if profile == 'baseline' else (4, 5, 6)):
                    for mode in ((0, 1) if profile == 'baseline' else (1,)):
                        args = [sample, 1, 1., float(ignore), source_na, receiver_na, float(mode), 0.]
                        value = float(backend.system.MFE.GetOperandValue(code, *args))
                        case['queries'].append(dict(arguments=args, value=value, reference=reference,
                            error=value-reference, passed=abs(value-reference) <= TOLERANCE))
                        save()
            case['settings_preserved'] = call('get_system_settings') == settings
            case['surfaces_preserved'] = call('get_surfaces', dict(start=0, count=100)) == surfaces
            case['merit_preserved'] = call('get_merit_function') == merit
            save()
    except BaseException as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        save()
    print(json.dumps([dict(finite=c['finite'], queries=len(c['queries']), passed=sum(q['passed'] for q in c['queries']), maximum_error=max(abs(q['error']) for q in c['queries'])) for c in record['cases']]))


if __name__ == '__main__':
    run(*sys.argv[1:])
