"""Compare adopted NCE source colors with the separate native spectrum viewer."""
import json
import os
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts/probes/PO-01')]

from probe_common import adapter, paged_result, poll_task, write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(destination):
    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(calls=[], cases=[], cleanup_failures=[],
                  hypothesis='NCE source-color changes may bind the separate SourceSpectrumViewer')
    call = adapter(backend, record['calls'])
    source = Path.home() / 'Documents/Zemax/Samples/Non-sequential/Colorimetry/Example 1  Two-color mixing gives white.zos'

    def snapshot():
        mce = backend.system.MCE
        return dict(settings=call('get_system_settings'), objects=call('get_nsc_objects'),
                    merit=call('get_merit_function'), configurations=dict(
                        count=int(mce.NumberOfConfigurations), current=int(mce.CurrentConfiguration)))

    try:
        call('connect')
        call('open_lens', dict(path=str(source)))
        record['context'] = backend.context()
        before = snapshot()
        source_indices = [i for i in range(1, int(backend.system.NCE.NumberOfObjects) + 1)
                          if backend.system.NCE.GetObjectAt(i).SourcesData.IsSourcesAvailable]
        record['source_indices'] = source_indices
        if not source_indices:
            raise RuntimeError('controlled model has no source objects')
        variants = [
            ('blackbody_3000', 'BlackBodySpectrum', dict(TemperatureK=3000, SpectrumCount=20,
                                                       WavelengthFrom=.4, WavelengthTo=.7)),
            ('blackbody_6000', 'BlackBodySpectrum', dict(TemperatureK=6000, SpectrumCount=20,
                                                       WavelengthFrom=.4, WavelengthTo=.7)),
            ('xyz_red', 'CIE1931Tristimulus', dict(X=1.5, Y=.5, Z=.1)),
            ('xyz_blue', 'CIE1931Tristimulus', dict(X=.2, Y=.1, Z=1.5)),
        ]
        for label, mode, settings in variants:
            entry = dict(label=label, requested=dict(mode=mode, settings=settings))
            record['cases'].append(entry)
            call('open_lens', dict(path=str(source)))
            entry['update'] = call('update_nsc_objects', dict(changes=[
                dict(object=i, spectrum=dict(mode=mode, settings=settings)) for i in source_indices]))
            adopted = snapshot()
            entry['adopted_objects'] = adopted['objects']
            entry['context'] = backend.context()
            if mode == 'BlackBodySpectrum':
                spectra = [row['spectrum'] for row in adopted['objects']['rows']
                           if row['object'] in source_indices]
                entry['inactive_aliases_absent'] = all(
                    not {'X', 'R', 'u'}.intersection(spectrum['settings']) for spectrum in spectra)
                if not entry['inactive_aliases_absent']:
                    raise RuntimeError('source readback includes inactive alias fields')
            rejection = backend.dispatch('update_nsc_objects', dict(changes=[
                dict(object=source_indices[0], spectrum=dict(mode='BlackBodySpectrum', settings=dict(X=3000)))]))
            entry['alias_rejection'] = rejection
            if rejection['ok'] or rejection['error']['code'] != 'INVALID_ARGUMENT':
                raise RuntimeError('cross-mode request was not rejected before writing')
            entry['rejection_preserved'] = snapshot() == adopted
            task = call('run_analysis', dict(request=dict(kind='source_spectrum_viewer')))
            entry['task'] = poll_task(call, task, record, timeout_s=75)
            if entry['task']['state'] != 'succeeded':
                raise RuntimeError('spectrum task failed: ' + str(entry['task']))
            entry['result'] = paged_result(call, task['task_id'], record, chunk=7)
            after = snapshot()
            entry['analysis_preserved'] = {k: adopted[k] == after[k] for k in adopted}
            saved = folder / (label + '.zos')
            entry['save'] = call('save_lens_as', dict(path=str(saved)))
            call('open_lens', dict(path=str(saved)))
            reloaded = snapshot()
            entry['reload_preserved'] = {k: after[k] == reloaded[k] for k in after}
            if not entry['rejection_preserved'] or not all(entry['reload_preserved'].values()):
                raise RuntimeError('rejection or save/reload changed controlled model state')
            write_json(folder / 'probe.json', record)
            if backend.active:
                raise RuntimeError('native task remains active')
        call('open_lens', dict(path=str(source)))
        restored = snapshot()
        record['restored_from_source'] = {k: before[k] == restored[k] for k in before}
        points = [case['result'].get('rows') for case in record['cases']]
        record['viewer_rows_identical'] = all(rows == points[0] for rows in points[1:])
    except Exception as exc:
        record['error'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        write_json(folder / 'probe.json', record)
    print(json.dumps(dict(output=str(folder), error=record.get('error'),
                          cases=[dict(label=c['label'], state=c.get('task', {}).get('state'),
                                      preserved=c.get('analysis_preserved')) for c in record['cases']],
                          viewer_rows_identical=record.get('viewer_rows_identical'),
                          restored=record.get('restored_from_source'), closed=record['close_receipt']),
                     ensure_ascii=False))
    return record


if __name__ == '__main__':
    result = run(sys.argv[1])
    if result.get('error'):
        sys.exit(1)
