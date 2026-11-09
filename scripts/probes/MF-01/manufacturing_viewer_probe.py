import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Serial formal settings/result discovery for manufacturing and resource viewers."""
import json
import sys
import time
import argparse
import os
from pathlib import Path

ROOT = PROJECT_ROOT
sys.path.insert(0, str(ROOT / 'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

TOPICS = ['TestPlateList', 'ZemaxElementDrawing', 'BitmapFileViewer',
          'IMABIMFileViewer', 'GradiumProfile', 'BeamFileViewer']
COUNTS = ['NumberOfDataSeries', 'NumberOfDataGrids', 'NumberOfDataSeriesRgb',
          'NumberOfDataGridsRgb', 'NumberOfDataScatterPoints',
          'NumberOfDataScatterPointsRgb', 'NumberOfRayData', 'NumberOfMessages']


def run(folder, selected_topics=TOPICS):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
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
        if 'GradiumProfile' in selected_topics:
            record['resources'] = call('get_system_resources', dict(kind='gradium_profiles'))
        record['before_settings'] = call('get_system_settings')
        record['before_surfaces'] = call('get_surfaces')
        for name in selected_topics:
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
        record['settings_preserved'] = call('get_system_settings') == record['before_settings']
        record['surfaces_preserved'] = call('get_surfaces') == record['before_surfaces']
    finally:
        record['session_id'] = b.session_id
        b.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else None
        record['stage'] = 'closed'
        save()
    print(json.dumps(dict(items=[{k: v for k, v in x.items() if k in ['native_id', 'counts', 'text_exported', 'error', 'closed']} for x in record['items']], close_receipt=record['close_receipt']), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder')
    parser.add_argument('--topic', choices=TOPICS, action='append')
    args = parser.parse_args()
    run(args.folder, args.topic or TOPICS)
