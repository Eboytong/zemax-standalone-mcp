import asyncio
import json
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_test_plates_native_file_agreement_paging_and_preservation():
    async def work(e):
        (e.folder / 'conditions.json').write_text(json.dumps(dict(reference='Independent installed TPD vendor resource; native report displays four decimals, dimensions always mm.', atol_mm=.0000500001, relative_tolerance=0)), encoding='utf-8')
        await e.call('new_system')
        capabilities = await e.call('get_capabilities')
        assert capabilities['analyses']['test_plate_list']['native_settings_readback'] is False
        assert capabilities['analyses']['test_plate_list']['methods'] == ['auto', 'native', 'file']
        before = await e.call('get_surfaces')
        settings = await e.call('get_system_settings')
        configs = await e.call('get_configurations', dict(request={}))
        resources = await e.call('get_system_resources', dict(request=dict(kind='test_plate_files', count=1000)))
        assert 'Applied.tpd' in resources['items']
        native = await e.finish(await e.call('run_analysis', dict(request=dict(kind='test_plate_list', method='native'))))
        actual = native['actual_settings']['catalog_file']
        assert native['native_closed'] is True
        file = await e.finish(await e.call('run_analysis', dict(request=dict(kind='test_plate_list', catalog_file=actual, method='file'))))
        assert len(native['rows']) == len(file['rows'])
        for nr, fr in zip(native['rows'], file['rows']):
            assert (nr['plate_id'], nr['concave'], nr['convex']) == (fr['plate_id'], fr['concave'], fr['convex'])
            for key in ['radius_mm', 'diameter_mm']:
                e.check(key, nr[key], fr[key], atol=.0000500001, rtol=0)
        task_id = native['task']['task_id']
        page = await e.call('get_task_result', dict(task_id=task_id, start=3, count=7))
        assert page['rows'] == native['rows'][3:10]
        other = next(n for n in resources['items'] if n != actual)
        fallback = await e.finish(await e.call('run_analysis', dict(request=dict(kind='test_plate_list', catalog_file=other))))
        assert fallback['actual_settings']['catalog_file'] == other and fallback['computation_method'] == 'documented_TPD_file'
        assert fallback['fallback_reason']['actual'] == actual and fallback['native_closed'] is True
        unsupported = await e.call('run_analysis', dict(request=dict(kind='test_plate_list', catalog_file=other, method='native')))
        while unsupported['state'] not in ['failed', 'cancelled', 'succeeded']:
            unsupported = await e.call('get_task_status', dict(task_id=unsupported['task_id']))
        result = await e.call('get_task_result', dict(task_id=unsupported['task_id']))
        assert unsupported['state'] == 'failed' and result['error']['code'] == 'SETTING_NOT_SUPPORTED'
        assert result['native_closed'] is True
        assert await e.call('get_surfaces') == before and await e.call('get_system_settings') == settings
        assert await e.call('get_configurations', dict(request={})) == configs
        (e.folder / 'native-result.json').write_text(json.dumps(native, ensure_ascii=False, indent=2), encoding='utf-8')
    asyncio.run(execute('plates429_native', work))


@pytest.mark.zemax
def test_test_plates_owned_resource_failure_cancel_reuse_reload():
    async def work(e):
        import time
        import uuid
        await e.call('new_system')
        resources = await e.call('get_system_resources', dict(request=dict(kind='test_plate_files')))
        own = Path(resources['directory']) / ('Agent' + uuid.uuid4().hex[:12] + '.tpd')
        try:
            own.write_text('! Controlled vendor\nconcave 2.345678 4 -1\nboth 3 5 0\nconvex 4 6 1\n', encoding='utf-8')
            q = dict(kind='test_plate_list', catalog_file=own.name, method='file')
            result = await e.finish(await e.call('run_analysis', dict(request=q)))
            assert [(r['concave'], r['convex']) for r in result['rows']] == [(True, False), (True, True), (False, True)]
            e.check('full TPD precision', result['rows'][0]['radius_mm'], 2.345678, atol=0, rtol=0)
            before = await e.call('get_surfaces')
            merit = await e.call('get_merit_function')
            missing = await e.call('run_analysis', dict(request=q | dict(catalog_file='absent-' + own.name)), okay=False)
            assert missing['error']['code'] == 'INVALID_RESOURCE'
            own.write_text('bad 1 nan 0\n', encoding='utf-8')
            task = await e.call('run_analysis', dict(request=q))
            deadline = time.monotonic() + 30
            while task['state'] not in ['failed', 'cancelled', 'succeeded']:
                assert time.monotonic() < deadline
                task = await e.call('get_task_status', dict(task_id=task['task_id']))
            failed = await e.call('get_task_result', dict(task_id=task['task_id']))
            assert task['state'] == 'failed' and failed['error']['code'] == 'INVALID_RESOURCE_DATA'
            own.write_text(''.join(f'p{i} 2 3 0\n' for i in range(20000)), encoding='utf-8')
            task = await e.call('run_analysis', dict(request=q))
            task = await e.call('get_task_status', dict(task_id=task['task_id']))
            assert task['state'] == 'running'
            task = await e.call('cancel_task', dict(task_id=task['task_id']))
            deadline = time.monotonic() + 30
            while task['state'] not in ['failed', 'cancelled', 'succeeded']:
                assert time.monotonic() < deadline
                task = await e.call('get_task_status', dict(task_id=task['task_id']))
            assert task['state'] == 'cancelled'
            cancelled = await e.call('get_task_result', dict(task_id=task['task_id']))
            assert len(cancelled['rows']) < 20000
            own.write_text('reuse 2 3 0\n', encoding='utf-8')
            await e.finish(await e.call('run_analysis', dict(request=q)))
            saved = str(e.folder / 'saved.zos')
            await e.call('save_lens_as', dict(path=saved))
            await e.call('open_lens', dict(path=saved))
            assert await e.call('get_surfaces') == before and await e.call('get_merit_function') == merit
            await e.finish(await e.call('run_analysis', dict(request=q)))
        finally:
            own.unlink(missing_ok=True)
    asyncio.run(execute('plates433_lifecycle', work))
