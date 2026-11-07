"""Serial B005 candidate settings, outlets and closure discovery."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

TOPICS = ['PowerFieldMapSettings','PowerPupilMapSettings','RayDatabaseViewer','LightSourceAnalysis','ExtendedDiffractionImageAnalysis','PartiallyCoherentImageAnalysis']
COUNTS = ['NumberOfDataSeries', 'NumberOfDataGrids', 'NumberOfDataSeriesRgb',
          'NumberOfDataGridsRgb', 'NumberOfDataScatterPoints',
          'NumberOfDataScatterPointsRgb', 'NumberOfRayData', 'NumberOfMessages']


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    b = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(items=[])

    def save():
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def call(name, args=None):
        record['stage'] = name
        save()
        reply = b.dispatch(name, args or {})
        assert reply['ok'], reply
        return reply['data']

    try:
        record['connect'] = call('connect')
        call('open_lens', dict(path=str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['resources'] = call('get_system_resources', dict(kind='gradium_profiles'))
        for name in TOPICS:
            tool = None
            item = dict(native_id=name)
            record['items'].append(item)
            try:
                record['stage'] = name + ': settings'
                save()
                tool = b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM, name))
                if tool is None:
                    item['factory_result'] = None
                    continue
                settings = unwrap(tool.GetSettings())
                typ = settings.GetType()
                item['settings_type'] = str(typ.FullName)
                item['properties'] = [dict(name=p.Name, type=str(p.PropertyType), writable=bool(p.CanWrite)) for p in typ.GetProperties()]
                item['methods'] = [str(m) for m in typ.GetMethods() if m.IsPublic and not m.IsSpecialName]
                item['cfg_saved'] = bool(settings.SaveTo(str(folder / (name + '.CFG'))))
                record['stage'] = name + ': Apply'
                save()
                tool.Apply()
                deadline = time.monotonic() + 20
                while tool.IsRunning():
                    if time.monotonic() > deadline:
                        item['timeout'] = True
                        tool.Terminate()
                        break
                    time.sleep(.05)
                result = unwrap(tool.GetResults())
                item['counts'] = {k: int(getattr(result, k)) for k in COUNTS}
                item['messages'] = [str(result.GetMessageAt(i).Text) for i in range(result.NumberOfMessages)]
                item['text_exported'] = bool(result.GetTextFile(str(folder / (name + '.txt'))))
                item['result_methods'] = [str(m) for m in result.GetType().GetMethods() if m.IsPublic and not m.IsSpecialName]
                item['result_properties'] = [dict(name=p.Name, type=str(p.PropertyType)) for p in result.GetType().GetProperties()]
            except Exception as exc:
                item['error'] = dict(type=type(exc).__name__, message=str(exc))
            finally:
                if tool is not None:
                    item['closed'] = b._close_task_native(dict(native=tool))
                save()
            if tool is not None and not item['closed']:
                break
    finally:
        record['disconnect'] = b.dispatch('disconnect', {})
        record['stage'] = 'closed'
        save()
    print(json.dumps(dict(items=[{k: v for k, v in x.items() if k in ['native_id', 'counts', 'text_exported', 'error', 'closed']} for x in record['items']], disconnect=record['disconnect']), ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])
