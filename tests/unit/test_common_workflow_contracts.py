import asyncio
import csv
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.history import RequestJournal
from zemax_mcp.models import Capabilities
from zemax_mcp.outcome import task_outcome
from zemax_mcp.reports import export_saved_report
from zemax_mcp.worker import handle_frame


KEY = 'a' * 32


@pytest.mark.parametrize('stage,observed,initial_count', [
    ('before_reserve', 'not_registered', 0),
    ('during_dispatch', 'unknown_after_worker_exit', 1),
    ('after_finish', 'returned', 1),
])
def test_bridge_recovers_after_worker_process_exit(stage, observed, initial_count, tmp_path, monkeypatch):
    from zemax_mcp.bridge import Bridge
    from zemax_mcp.config import PROJECT_ROOT

    bootstrap = """
import os
from pathlib import Path
from zemax_mcp import worker
stage = os.environ.get('TEST_WORKER_EXIT')
reserve, finish, dispatch = (worker.RequestJournal.reserve, worker.RequestJournal.finish, worker.Backend.dispatch)
def claim(self, *args):
    if stage == 'before_reserve': os._exit(91)
    return reserve(self, *args)
def record(self, receipt, response):
    finish(self, receipt, response)
    if receipt.get('client_assigned') and stage == 'after_finish': os._exit(93)
def run(self, command, arguments, request_id=None):
    if command != 'test_mutation':
        return dispatch(self, command, arguments, request_id=request_id)
    with (Path(os.environ['ZEMAX_OUTPUT_DIR']) / 'applied.txt').open('a') as stream:
        stream.write(request_id + '\\n')
    if stage == 'during_dispatch': os._exit(92)
    return dict(ok=True, data={'applied': True}, error=None, context={}, warnings=[], artifacts=[])
worker.RequestJournal.reserve, worker.RequestJournal.finish, worker.Backend.dispatch = claim, record, run
worker.main()
"""
    create = asyncio.create_subprocess_exec

    async def instrumented(python, *_args, **options):
        return await create(python, '-B', '-u', '-c', bootstrap, **options)

    monkeypatch.setenv('PYTHONPATH', str(PROJECT_ROOT / 'src'))
    monkeypatch.setenv('ZEMAX_OUTPUT_DIR', str(tmp_path))
    monkeypatch.setenv('TEST_WORKER_EXIT', stage)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', instrumented)

    async def scenario():
        bridge = Bridge()
        applied = tmp_path / 'applied.txt'
        try:
            first = await bridge.request('test_mutation', request_id=KEY)
            assert first['error']['code'] == 'WORKER_UNAVAILABLE'
            assert first['error']['details']['request_id'] == KEY
            assert (len(applied.read_text().splitlines()) if applied.exists() else 0) == initial_count
            monkeypatch.delenv('TEST_WORKER_EXIT')
            receipt = await bridge.request('get_request_status', {'request_id': KEY})
            assert receipt['data']['observed_execution_state'] == observed
            retry = await bridge.request('test_mutation', request_id=KEY)
            if stage == 'during_dispatch':
                assert retry['data']['observed_execution_state'] == observed
            else:
                assert retry['data'] == {'applied': True}
            assert applied.read_text().splitlines() == [KEY]
        finally:
            await bridge.close()

    asyncio.run(scenario())


@pytest.mark.parametrize('state,rows,expected', [
    ('succeeded', ['succeeded', 'failed', 'succeeded'], ('incomplete', 2, 1, 0, 0)),
    ('succeeded', ['failed'] * 3, ('incomplete', 0, 3, 0, 0)),
    ('cancelled', ['succeeded'], ('incomplete', 1, 0, 2, 0)),
    ('running', ['succeeded'], ('pending', 1, 0, 0, 2)),
    ('failed', ['failed'], ('incomplete', 0, 1, 2, 0)),
    ('succeeded', ['succeeded'] * 3, ('complete', 3, 0, 0, 0)),
])
def test_batch_outcome_is_independent_of_dispatch_and_recovery(state, rows, expected):
    outcome = task_outcome(dict(state=state, kind='configuration_evaluation',
        settings={'configurations': [1, 2, 3]}, rows=[{'state': row} for row in rows],
        restoration={'restored': state != 'failed'}))
    coverage = outcome['coverage']
    assert tuple(coverage[k] for k in ('state', 'succeeded', 'failed', 'skipped', 'pending')) == expected
    assert outcome['execution_state'] == state and coverage['planned'] == 3
    if state == 'failed':
        assert outcome['restoration']['state'] == 'failed'


def test_worker_receipt_restart_boundaries_and_conflict(tmp_path):
    calls = []

    def dispatch(command, arguments, request_id):
        calls.append((command, arguments, request_id))
        return dict(ok=True, data={'model_revision': len(calls)}, warnings=[], error=None, artifacts=[])

    backend = SimpleNamespace(dispatch=dispatch)
    frame = dict(id='transport', request_id=KEY, command='update_surfaces', arguments={'changes': [1]})
    assert Backend(Config(tmp_path, tmp_path)).get_request_status(SimpleNamespace(request_id=KEY))[
        'observed_execution_state'] == 'not_registered'
    first = handle_frame(backend, RequestJournal(tmp_path, 'worker1'), frame)
    assert handle_frame(backend, RequestJournal(tmp_path, 'worker2'), frame) == first
    changed = handle_frame(backend, RequestJournal(tmp_path, 'worker2'), frame | {'arguments': {'changes': [2]}})
    assert changed['error']['code'] == 'REQUEST_ID_CONFLICT'
    interrupted = 'b' * 32
    RequestJournal(tmp_path, 'worker1').reserve(interrupted, frame['command'], frame['arguments'])
    unknown = handle_frame(backend, RequestJournal(tmp_path, 'worker2'), frame | {'request_id': interrupted})
    assert unknown['data']['observed_execution_state'] == 'unknown_after_worker_exit'
    assert len(calls) == 1


def test_reservation_has_single_winner_across_workers(tmp_path):
    def reserve(index):
        return RequestJournal(tmp_path, str(index)).reserve(KEY, 'new_system', {})[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(receipt is not None for receipt in pool.map(reserve, range(8))) == 1


def test_discovery_exposes_live_conditions_and_checks_input(tmp_path):
    backend = Backend(Config(tmp_path, tmp_path / 'runs'))
    get = lambda cap, args=None: backend.get_capabilities(Capabilities(
        topic='dependencies', capability_id='tool:' + cap, arguments=args))
    offline = get('run_fft_mtf')['readiness']
    assert offline['state'] == 'blocked' and offline['blockers'][0]['code'] == 'NOT_CONNECTED'
    backend.native = SimpleNamespace(application=SimpleNamespace(IsSTARModuleEnabled=False),
                                     connection_ready=True)
    backend.system_context['mode'] = 'NonSequential'
    assert get('run_fft_mtf')['readiness']['blockers'][0]['code'] == 'MODE_MISMATCH'
    missing = get('open_lens', {'path': str(tmp_path/'missing.zos')})['readiness']
    assert missing['state'] == 'blocked' and missing['blockers'][0]['code'] == 'INVALID_INPUT_FILE'
    assert get('run_nsc_ray_trace')['readiness']['state'] == 'ready'
    assert get('get_star_data')['readiness']['blockers'][-1]['code'] == 'FEATURE_UNAVAILABLE'
    backend.tasks[KEY] = {'state': 'running'}
    assert get('export_analysis_image', {'request': {'task_id': KEY}})['readiness']['blockers'][0]['code'] == 'TASK_NOT_FINISHED'


def test_result_and_report_share_axes_and_coverage(tmp_path):
    backend = Backend(Config(tmp_path, tmp_path / 'runs'))
    task = dict(task_id=KEY, state='succeeded', kind='configuration_evaluation', directory=str(tmp_path),
                rows=[{'state': 'failed'}], settings={'configurations': [1]}, system_settings={},
                context={'model_revision': 7}, restoration={'restored': True})
    series = [dict(series=i, description=axis, x_label=axis, x_unit=unit, labels=['value'],
                   value_units=['dimensionless'], x=[1], y=[[.5]], source='native')
              for i, (axis, unit) in enumerate([('field', 'degrees'), ('position', 'micrometers')])]
    result = {'series': series, 'rows': task['rows']}
    backend._save_task_result(task, result)
    assert result['outcome']['coverage']['state'] == 'incomplete'
    folder = tmp_path / 'report'
    folder.mkdir()
    report = export_saved_report(folder, [dict(task_id=KEY, result=result)], 'test', False, ['markdown'])
    from pathlib import Path
    for artifacts in (result['artifacts'], report['artifacts']):
        file = next(Path(a['path']) for a in artifacts if a['kind'] == 'series_csv')
        with file.open(encoding='utf-8-sig', newline='') as stream:
            assert [(r['x_label'], r['x_unit'], r['y_unit']) for r in csv.DictReader(stream)] == [
                ('field', 'degrees', 'dimensionless'), ('position', 'micrometers', 'dimensionless')]
    assert '"coverage"' in (folder/'report.md').read_text(encoding='utf-8')
