"""Owned RGB input and documented GBM selection/rotation/surface controls."""
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from PIL import Image
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean, unwrap


def run(destination):
    folder = Path(destination).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder/'state')
    backend = Backend(Config(Config.from_env().install_dir, folder/'native'))
    resource = Path.home()/'Documents/Zemax/IMAFiles'/('MCP_RGB_'+uuid.uuid4().hex+'.BMP')
    image = Image.new('RGB', (7, 5))
    pixels = [(255 if x < 2 else 0, 160 if y < 2 else 0,
               96 if x >= 4 and y >= 3 else 0) for y in range(5) for x in range(7)]
    image.putdata(pixels)
    image.save(folder/'source.bmp')
    record = dict(source_root=str(ROOT), resource=str(resource), source_pixels_top_down=pixels,
                  calls=[], cases=[], error=None)
    def save():
        (folder/'probe.json').write_text(json.dumps(clean(record), ensure_ascii=False, indent=2), encoding='utf-8')
    def call(name, args=None):
        r = backend.dispatch(name, args or {})
        record['calls'].append(dict(tool=name, arguments=args, response=r))
        save()
        if not r['ok']:
            raise RuntimeError(r)
        return r['data']
    try:
        image.save(resource)
        call('connect')
        call('open_lens', dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before = call('get_system_settings')
        surfaces = call('get_surfaces')
        for tag, source, surface, rotation in [
            ('basename_s7_r0', resource.name, 7, 0),
            ('absolute_s7_r0', str(resource), 7, 0),
            ('basename_s6_r1', resource.name, 6, 1),
            ('basename_s7_r90', resource.name, 7, 90),
            ('basename_s1_r0', resource.name, 1, 0),
        ]:
            case = dict(tag=tag, operations=[])
            record['cases'].append(case)
            tool = backend.system.Analyses.New_Analysis_SettingsFirst(backend.native.api.Analysis.AnalysisIDM.GeometricBitmapImageAnalysis)
            started = False
            try:
                settings = unwrap(tool.GetSettings())
                cfg = folder/(tag+'.CFG')
                case['saved'] = bool(settings.SaveTo(str(cfg)))
                if not case['saved']:
                    raise RuntimeError('SaveTo rejected')
                entries = dict(GBM_INPUT=source, GBM_OUTPUT=str(folder/(tag+'.bmp')),
                               GBM_FIELDSIZE=1, GBM_RAYS=10, GBM_XPIX=17, GBM_YPIX=11,
                               GBM_XSIZ=.05, GBM_YSIZ=.05, GBM_SURFACE=surface, GBM_ROTATION=rotation)
                for key, value in entries.items():
                    adopted = bool(settings.ModifySettings(str(cfg), key, str(value)))
                    case['operations'].append(dict(key=key, value=value, accepted=adopted))
                    if not adopted:
                        raise RuntimeError('ModifySettings rejected: '+key)
                case['loaded'] = bool(settings.LoadFrom(str(cfg)))
                if not case['loaded']:
                    raise RuntimeError('LoadFrom rejected')
                def collect(task):
                    native = unwrap(task['native'].GetResults())
                    path = folder/(tag+'.txt')
                    exported = bool(native.GetTextFile(str(path)))
                    return dict(text_path=str(path), text_exported=exported,
                                header=path.read_text(encoding='utf-16').splitlines()[:20] if exported else [],
                                output_exists=(folder/(tag+'.bmp')).is_file(),
                                valid=bool(native.IsValid), grid_count=int(native.NumberOfDataGrids))
                task = backend._start_task('analysis', tool, dict(kind='geometric_bitmap_image', probe=tag),
                                           analysis=True, collector=collect, budget_seconds=60)
                started = True
                deadline = time.monotonic()+75
                while backend.tasks[task['task_id']]['state'] not in {'succeeded','failed','cancelled'}:
                    if time.monotonic() > deadline:
                        raise TimeoutError(tag)
                    backend.tick()
                    time.sleep(.03)
                raw = backend.tasks[task['task_id']]
                case['task'] = backend._task_view(raw)
                case['result'] = raw.get('result') or json.loads(Path(raw['result_path']).read_text(encoding='utf-8'))
                if case['result']['output_exists']:
                    with Image.open(folder/(tag+'.bmp')) as output:
                        case['output_size'] = list(output.size)
                        case['output_mode'] = output.mode
            except Exception as exc:
                case['error'] = repr(exc)
            finally:
                if not started:
                    case['closed_after_setup_error'] = backend._close_task_native(dict(native=tool))
                save()
            if backend.active:
                raise RuntimeError('native task remains active')
        record['settings_preserved'] = before == call('get_system_settings')
        record['surfaces_preserved'] = surfaces == call('get_surfaces')
    except Exception as exc:
        record['error'] = repr(exc)
    finally:
        backend.shutdown()
        receipt = folder/'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        if resource.exists():
            resource.unlink()
        record['owned_resource_removed'] = not resource.exists()
        save()
    print(json.dumps(dict(folder=str(folder), error=record['error'],
        cases=[dict(tag=c['tag'], error=c.get('error'), result=c.get('result')) for c in record['cases']]),ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])
