"""Check the recovered user-context Standalone through a real MCP stdio client."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from mcp import Client
from scripts.development.native_startup_check import process_context
from tests.support.native import Evidence, server_parameters


async def scenario(folder, record):
    evidence = None
    try:
        async with Client(server_parameters(folder / 'runs'), read_timeout_seconds=180) as client:
            evidence = Evidence(client, folder)
            try:
                await evidence.call('get_capabilities', dict(topic='tool', tool_name='run_analysis'))
                await evidence.call('connect')
                sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
                working = folder / 'Cooke.zos'
                shutil.copyfile(sample, working)
                record['input'] = dict(source=str(sample), working_copy=str(working))
                await evidence.call('open_lens', dict(path=str(working)))
                result = await evidence.finish(await evidence.call('run_analysis',
                    dict(request=dict(kind='relative_illumination'))))
                assert result.get('series'), result
                curve = result['series'][0]
                evidence.check('RI maximum', max(row[0] for row in curve['y']), 1, atol=1e-6)
                task_id = result['task']['task_id']
                for start in (0, 7):
                    page = await evidence.call('get_task_result',
                        dict(task_id=task_id, series=0, start=start, count=7))
                    assert page['series'][0]['x'] == curve['x'][start:start+7]
                    assert page['series'][0]['y'] == curve['y'][start:start+7]
                png = folder / 'relative-illumination.png'
                await evidence.call('export_analysis_image', dict(request=dict(task_id=task_id, path=str(png))))
                assert png.is_file() and png.stat().st_size > 0
                status = await evidence.call('get_task_status', dict(task_id=task_id))
                assert status['state'] == 'succeeded' and status['close_attempted'], status
                record.update(task=status, image=str(png), analysis_passed=True)
            finally:
                primary_error = sys.exc_info()[0] is not None
                try:
                    await evidence.call('disconnect')
                    status = await evidence.call('get_status')
                    assert not status['connected'] and not status['running_tasks'], status
                    startup = status['native_startup']
                    assert any(e['stage'] == 'application_close' and e['event'] == 'completed'
                               for e in startup['events']), startup
                    record.update(normal_close=True, final_status=status)
                except Exception as exc:
                    record['close_error'] = dict(type=type(exc).__name__, message=str(exc))
                    if not primary_error:
                        raise
    finally:
        if evidence:
            (folder / 'calls.json').write_text(json.dumps(evidence.calls, ensure_ascii=False, indent=2), encoding='utf-8')
            (folder / 'checks.json').write_text(json.dumps(evidence.checks, ensure_ascii=False, indent=2), encoding='utf-8')


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    context = process_context()
    record = dict(context=context, transport='real MCP stdio', normal_close=False)
    print('Evidence: ' + str(folder), flush=True)
    key = 'COMPLUS_LoadFromRemoteSources'
    previous = os.environ.get(key)
    try:
        if context['integrity_rid'] != 8192 or context['elevated']:
            record['state'] = 'requires_non_elevated_medium_context'
            return 2
        os.environ[key] = '1'
        asyncio.run(scenario(folder, record))
        record['state'] = 'passed'
        return 0
    except Exception as exc:
        record.update(state='failed', error=dict(type=type(exc).__name__, message=str(exc)))
        return 1
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous
        (folder / 'result.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(dict(state=record.get('state'), evidence=str(folder)), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    label = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    parser.add_argument('--output-dir', type=Path, default=ROOT / '.local/evidence/development/BASE-04' / ('stdio-recovery-' + label))
    sys.exit(run(parser.parse_args().output_dir))
