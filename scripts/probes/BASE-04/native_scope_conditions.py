"""Current STAR and HPC prerequisites without submitting native/cloud jobs."""
import json
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT / 'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    record = dict(source_root=str(ROOT), calls=[], error=None, jobs_submitted=0)

    def call(name, arguments=None, required=True):
        response = backend.dispatch(name, arguments or {})
        record['calls'].append(dict(tool=name, arguments=arguments, response=response))
        if required and not response['ok']:
            raise RuntimeError(response)
        return response

    try:
        record['connect'] = call('connect')
        call('new_system')
        record['revision_before'] = backend.revision
        before = {name: call(name) for name in ['get_system_settings', 'get_surfaces', 'get_merit_function']}
        record['star_enabled'] = bool(backend.native.application.IsSTARModuleEnabled)
        record['star_read'] = call('get_star_data', dict(surface=1, data_kind='deformation'), required=False)
        record['hpc_queries'] = [call('get_hpc_settings', dict(request=request), required=False)
            for request in [dict(mode='preferences'), dict(mode='custom', node_count=1, instance_type='Default')]]
        record['tools_methods'] = sorted(set(str(m) for m in backend.system.Tools.GetType().GetMethods()
                                             if m.IsPublic and not m.IsSpecialName))
        record['preserved'] = {name: call(name) == response for name, response in before.items()}
        record['model_revision'] = backend.revision
        record['revision_preserved'] = backend.revision == record['revision_before']
    except Exception as exc:
        record['error'] = repr(exc)
    finally:
        record['session_id'] = backend.session_id
        backend.shutdown()
        receipt = folder / 'state/close_receipt.json'
        record['close_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else None
        (folder / 'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(output=str(folder), error=record['error'], star_enabled=record.get('star_enabled'),
        hpc=[dict(ok=row['ok'], error=row.get('error'), data=row.get('data')) for row in record.get('hpc_queries', [])],
        closed=(record.get('close_receipt') or {}).get('native', {}).get('closed')), ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])
