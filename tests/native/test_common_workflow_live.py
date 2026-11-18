import asyncio
from pathlib import Path
import uuid

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_common_workflow_contracts_over_stdio():
    async def work(e):
        status = await e.call('get_status')
        assert status['server_version'] == '1.4.3' and status['capability_index_version'] >= 2
        lens = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        absent = e.folder / 'absent.zos'
        detail = await e.call('get_capabilities', dict(topic='dependencies', capability_id='tool:open_lens',
                                                      arguments={'path': str(absent)}))
        assert detail['readiness']['blockers'][0]['code'] == 'INVALID_INPUT_FILE'
        await e.call('open_lens', {'path': str(lens)})
        request_id = uuid.uuid4().hex
        payload = dict(capability_id='tool:update_system_settings', request_id=request_id,
                       arguments={'settings': {'title': 'Common workflow smoke'}})
        first = (await e.client.call_tool('execute_capability', payload)).structured_content
        second = (await e.client.call_tool('execute_capability', payload)).structured_content
        assert first['ok'] and second == first
        receipt = await e.call('get_request_status', {'request': {'request_id': request_id}})
        assert receipt['observed_execution_state'] == 'returned'
        mtf = await e.finish(await e.call('run_fft_mtf', {'sampling': 'S_64x64', 'field': 1}))
        assert mtf['provenance']['calculation_source'] == 'native_opticstudio'
        assert mtf['series'][0]['axes']['x']['unit'] == 'CyclesPerMillimeter'
        batch = await e.finish(await e.call('run_batch_evaluation', {'request': {
            'paths': [str(absent), str(lens)], 'evaluation': {'spot': {'reference': 'Centroid'}}}}))
        assert batch['outcome']['coverage'] == dict(state='incomplete', planned=2, succeeded=1,
                                                    failed=1, skipped=0, pending=0)
        assert batch['outcome']['restoration']['state'] == 'restored'
        history = await e.call('get_historical_result', {'request': {
            'session_id': batch['context']['session_id'], 'task_id': batch['task']['task_id']}})
        assert history['outcome'] == batch['outcome']
        report = await e.call('export_evaluation_report', {'task_ids': [mtf['task']['task_id']]})
        assert any(a['kind'] == 'series_csv' for a in report['artifacts'])

    asyncio.run(execute('common_workflow', work))
