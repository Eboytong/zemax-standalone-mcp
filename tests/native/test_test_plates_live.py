import asyncio
import json
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_test_plates_selected_native_cfgs_identity_and_reload():
    import os
    import shutil
    presets = json.loads(os.environ.get('ZEMAX_TEST_PLATE_CFGS', '[]'))
    if len(presets) < 2:
        pytest.skip('Provide at least two original native catalog CFG presets in ZEMAX_TEST_PLATE_CFGS')

    async def work(e):
        await e.call('new_system')
        baseline = {name: await e.call(name) for name in
                    ('get_system_settings', 'get_surfaces', 'get_merit_function')}
        configs = await e.call('get_configurations', dict(request={}))
        requests = []
        results = []
        for index, preset in enumerate(presets):
            owned = e.folder / f'catalog-{index}.CFG'
            shutil.copyfile(preset['path'], owned)
            request = dict(kind='test_plate_list', method='native',
                           native_settings_file=str(owned), catalog_file=preset['catalog_file'])
            requests.append(request)
            result = await e.finish(await e.call('run_analysis', dict(request=request)))
            results.append(result)
            assert result['native_configuration']['loaded'] and result['native_closed']
            assert result['actual_settings']['catalog_file'] == preset['catalog_file']
            assert result['computation_method'] == 'native_TestPlateList_text'
            reference = await e.finish(await e.call('run_analysis', dict(request=dict(
                kind='test_plate_list', method='file', catalog_file=preset['catalog_file']))))
            for nr, fr in zip(result['rows'], reference['rows'], strict=True):
                assert (nr['plate_id'], nr['availability_code']) == (fr['plate_id'], fr['availability_code'])
                for key in ('radius_mm', 'diameter_mm'):
                    e.check(preset['catalog_file'] + ':' + key, nr[key], fr[key], atol=.0000500001, rtol=0)
            page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=3, count=7))
            assert page['rows'] == result['rows'][3:10]
        saved = str(e.folder / 'saved.zos')
        await e.call('save_lens_as', dict(path=saved))
        await e.call('open_lens', dict(path=saved))
        reloaded = await e.finish(await e.call('run_analysis', dict(request=requests[0])))
        assert reloaded['rows'] == results[0]['rows']
        mismatch = await e.call('run_analysis', dict(request=dict(
            requests[0], method='auto', catalog_file=presets[1]['catalog_file'])))
        import asyncio
        while mismatch['state'] not in ('succeeded', 'failed', 'cancelled'):
            await asyncio.sleep(.02)
            mismatch = await e.call('get_task_status', dict(task_id=mismatch['task_id']))
        failed = await e.call('get_task_result', dict(task_id=mismatch['task_id']))
        assert mismatch['state'] == 'failed' and failed['error']['code'] == 'SETTING_NOT_SUPPORTED'
        assert failed['native_closed'] and 'fallback_reason' not in failed
        reused = await e.finish(await e.call('run_analysis', dict(request=requests[1])))
        assert reused['rows'] == results[1]['rows']
        for name, expected in baseline.items():
            assert await e.call(name) == expected
        assert await e.call('get_configurations', dict(request={})) == configs
        (e.folder / 'cfg-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    asyncio.run(execute('plates_selected_cfg', work))


@pytest.mark.zemax
def test_test_plates_formal_cfg_save_and_stdio_reload(tmp_path):
    """Replay a task-owned official preset; this covers the active catalog only."""
    import os
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.data import unwrap
    from zemax_mcp.test_plates import catalog_resources, parse_native

    folder = tmp_path / 'cfg-source'
    folder.mkdir()
    previous = os.environ.get('ZEMAX_STATE_DIR')
    os.environ['ZEMAX_STATE_DIR'] = str(folder / 'state')
    backend = Backend(Config(Config.from_env().install_dir, folder / 'native'))
    tool = None
    cfg = folder / 'TestPlateList.CFG'
    try:
        assert backend.dispatch('connect', {})['ok']
        assert backend.dispatch('new_system', {})['ok']
        tool = backend.system.Analyses.New_Analysis_SettingsFirst(
            backend.native.enum(backend.native.api.Analysis.AnalysisIDM, 'TestPlateList'))
        assert unwrap(tool.GetSettings()).SaveTo(str(cfg))
        tool.ApplyAndWaitForCompletion()
        text = folder / 'catalog.txt'
        assert tool.GetResults().GetTextFile(str(text))
        _, names = catalog_resources(backend.native.application)
        actual, reference = parse_native(text.read_text(encoding='utf-16'), names)
    finally:
        try:
            if tool is not None:
                assert backend._close_task_native(dict(native=tool))
        finally:
            backend.shutdown()
            if previous is None:
                os.environ.pop('ZEMAX_STATE_DIR', None)
            else:
                os.environ['ZEMAX_STATE_DIR'] = previous

    async def work(e):
        import shutil
        owned_cfg = e.folder / 'TestPlateList.CFG'
        shutil.copyfile(cfg, owned_cfg)
        (e.folder / 'reference.json').write_text(json.dumps(dict(
            catalog_file=actual, rows=reference, source='formal native SaveTo and GetTextFile'),
            ensure_ascii=False, indent=2), encoding='utf-8')
        await e.call('new_system')
        baseline = {name: await e.call(name) for name in
                    ('get_system_settings', 'get_surfaces', 'get_merit_function')}
        request = dict(kind='test_plate_list', method='native', catalog_file=actual,
                       native_settings_file=str(owned_cfg))
        result = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert result['native_closed']
        assert result['native_configuration']['loaded']
        assert result['native_configuration']['actual_catalog_file'] == actual
        assert result['rows'] == reference
        page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=3, count=7))
        assert page['rows'] == reference[3:10]
        file = await e.finish(await e.call('run_analysis', dict(request=dict(
            kind='test_plate_list', method='file', catalog_file=actual))))
        for native_row, file_row in zip(result['rows'], file['rows'], strict=True):
            assert (native_row['plate_id'], native_row['availability_code']) == (
                file_row['plate_id'], file_row['availability_code'])
            for key in ('radius_mm', 'diameter_mm'):
                e.check(key, native_row[key], file_row[key], atol=.0000500001, rtol=0)
        for name, expected in baseline.items():
            assert await e.call(name) == expected
    asyncio.run(execute('plates_cfg_replay', work))


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
