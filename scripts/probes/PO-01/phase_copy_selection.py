"""Test native PhaseAberration input identity after reordering an owned copy."""
import json
import math
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.polarization_topics import parse_phase_aberration_text
from zemax_mcp.speos import OwnedCopyTool


def run(destination, freeze=False):
    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(plan='promote selected field and make selected wavelength primary in an owned copy; preserve source model',
                  freeze_core_geometry=freeze, calls=[], cases=[])

    def save():
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    def call(name, args=None):
        response = backend.dispatch(name, args or {})
        record['calls'].append(dict(tool=name, arguments=args, response=response))
        if not response['ok']:
            raise RuntimeError(response)
        return response['data']

    def geometry(system):
        return [dict(surface=i, radius=str(row.Radius), thickness=str(row.Thickness),
                     conic=float(row.Conic), material=str(row.Material), semi_diameter=float(row.SemiDiameter))
                for i in range(int(system.LDE.NumberOfSurfaces))
                for row in [system.LDE.GetSurfaceAt(i)]]

    try:
        call('connect')
        record['context'] = backend.context()
        call('open_lens', dict(path=str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        call('update_system_settings', dict(
            fields=[dict(x=0., y=0., weight=1.), dict(x=0., y=5., weight=.7)],
            wavelengths=[dict(wavelength_um=.4861327, weight=.6), dict(wavelength_um=.6562725, weight=1.)],
            primary_wavelength=2, polarization=dict(unpolarized=False, jx=1., jy=1., x_phase=17., y_phase=73.)))
        baseline = {name: call(name) for name in ('get_system_settings', 'get_surfaces', 'get_merit_function')}
        record['source_geometry'] = geometry(backend.system)
        for field_number, wave_number in ((1, 1), (2, 1), (1, 2), (2, 2)):
            case = dict(field=field_number, wavelength=wave_number)
            record['cases'].append(case)
            copy = backend.system.CopySystem()
            tool = None
            try:
                data = copy.SystemData
                case['fixed_copy_cells'] = []
                if freeze:
                    for i in range(1, int(copy.LDE.NumberOfSurfaces)):
                        row = copy.LDE.GetSurfaceAt(i)
                        for attr in ('RadiusCell', 'ThicknessCell', 'ConicCell', 'SemiDiameterCell'):
                            cell = getattr(row, attr)
                            previous = str(cell.Solve)
                            if previous in ('Fixed', 'Variable'):
                                continue
                            value = float(cell.DoubleValue)
                            adopted = bool(cell.MakeSolveFixed())
                            if not adopted or str(cell.Solve) != 'Fixed':
                                raise RuntimeError(f'copy {i}.{attr} could not be fixed: {previous}')
                            cell.DoubleValue = value
                            case['fixed_copy_cells'].append(dict(surface=i, cell=attr, previous_solve=previous,
                                                                 requested_value=str(value), actual_value=str(cell.DoubleValue)))
                attrs = ('X', 'Y', 'Weight', 'VDX', 'VDY', 'VCX', 'VCY', 'VAN')
                fields = [{k: float(getattr(data.Fields.GetField(i), k)) for k in attrs}
                          for i in range(1, int(data.Fields.NumberOfFields) + 1)]
                waves = [dict(wavelength=float(data.Wavelengths.GetWavelength(i).Wavelength),
                              weight=float(data.Wavelengths.GetWavelength(i).Weight),
                              primary=bool(data.Wavelengths.GetWavelength(i).IsPrimary))
                         for i in range(1, int(data.Wavelengths.NumberOfWavelengths) + 1)]
                fields[0], fields[field_number - 1] = fields[field_number - 1], fields[0]
                for i, field in enumerate(fields, 1):
                    native_field = data.Fields.GetField(i)
                    for k, v in field.items():
                        setattr(native_field, k, v)
                for i, wave in enumerate(waves, 1):
                    native_wave = data.Wavelengths.GetWavelength(i)
                    native_wave.Wavelength = wave['wavelength']
                    native_wave.Weight = wave['weight']
                data.Wavelengths.GetWavelength(wave_number).MakePrimary()
                case['actual'] = dict(field={k: float(getattr(data.Fields.GetField(1), k)) for k in attrs},
                    wavelength_um=float(data.Wavelengths.GetWavelength(wave_number).Wavelength),
                    primary_slot=next(i for i in range(1, int(data.Wavelengths.NumberOfWavelengths) + 1)
                                      if data.Wavelengths.GetWavelength(i).IsPrimary),
                    source_system_id=int(backend.system.SystemID), analysis_system_id=int(copy.SystemID))
                tool = copy.Analyses.New_Analysis_SettingsFirst(backend.native.enum(backend.native.api.Analysis.AnalysisIDM, 'PhaseAberration'))
                tool.ApplyAndWaitForCompletion()
                path = folder / f'field{field_number}-wave{wave_number}.txt'
                case['text_exported'] = bool(tool.GetResults().GetTextFile(str(path)))
                parsed = parse_phase_aberration_text(path.read_text(encoding='utf-16'), dict(field_type='Angle'))
                case['header'] = parsed['input_header']
                case['row_count'] = len(parsed['rows'])
                case['geometry_after_analysis'] = geometry(copy)
                comparisons = []
                for source, actual in zip(record['source_geometry'], case['geometry_after_analysis'], strict=True):
                    for key in ('radius', 'thickness', 'conic', 'semi_diameter'):
                        wanted, got = float(source[key]), float(actual[key])
                        error = abs(got - wanted) if math.isfinite(wanted) and math.isfinite(got) else None
                        tolerance = 1e-12 + 1e-12 * abs(wanted) if math.isfinite(wanted) else None
                        comparisons.append(dict(surface=source['surface'], quantity=key, source=str(wanted), actual=str(got),
                                                error=error, tolerance=tolerance,
                                                passed=(error <= tolerance) if error is not None else got == wanted))
                case['geometry_comparisons'] = comparisons
                case['geometry_matches_source'] = (all(c['passed'] for c in comparisons)
                    and all(a['material'] == b['material'] for a, b in zip(record['source_geometry'], case['geometry_after_analysis'], strict=True)))
                case['identity_matches'] = (
                    abs(case['header']['field_position']['y'] - fields[0]['Y']) < 1e-8
                    and abs(case['header']['wavelength_um'] - waves[wave_number - 1]['wavelength']) < .00005)
            finally:
                if tool is not None:
                    case['tool_closed'] = backend._close_task_native(dict(native=tool))
                backend._release_owned(OwnedCopyTool(copy))
                case['copy_closed'] = True
            case['source_preserved'] = {name: call(name) == value for name, value in baseline.items()}
            save()
            if not case['identity_matches'] or not case['geometry_matches_source'] or not all(case['source_preserved'].values()):
                raise RuntimeError('native input identity or source preservation did not match')
    except Exception as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        save()
    print(json.dumps(dict(error=record.get('error'), cases=record['cases'],
                          native_closed=(record.get('close_receipt') or {}).get('native')), ensure_ascii=False))
    return bool(record.get('error'))


if __name__ == '__main__':
    sys.exit(run(sys.argv[1], freeze='--freeze' in sys.argv[2:]))
