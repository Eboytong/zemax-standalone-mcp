"""Real stdio checks of typed default D008 text reports; requires --run-zemax."""
import asyncio
from pathlib import Path

import pytest

from tests.support.native import execute

COOKE = str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')


@pytest.mark.zemax
def test_prescription_default_report():
    """D008-R1: default prescription report through the kind-only entry."""
    async def work(e):
        await e.call('open_lens', dict(path=COOKE))
        before = await e.call('get_surfaces')
        result = await e.finish(await e.call('run_analysis', dict(request=dict(kind='prescription_data'))))
        assert result['analysis_kind'] == 'prescription_data'
        assert result['section_count'] >= 1
        assert result['lines'] and result['line_count'] == len(result['lines'])
        assert result['acceptance_scope'] == 'default_report_only'
        assert result['selection_scope']['status'] == 'blocked'
        assert result['report_title']
        status = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
        assert status['state'] == 'succeeded' and status['close_attempted']
        assert await e.call('get_surfaces') == before
        e.checks.append(dict(kind='prescription_data', sections=result['section_count'],
                             lines=result['line_count'], title=result['report_title']))
    asyncio.run(execute('d008r1', work))


@pytest.mark.zemax
def test_surface_default_report_identity():
    """D008-R2: default surface-data report, identity and units recorded verbatim."""
    async def work(e):
        await e.call('open_lens', dict(path=COOKE))
        before = await e.call('get_surfaces')
        result = await e.finish(await e.call('run_analysis', dict(request=dict(kind='surface_data'))))
        assert result['analysis_kind'] == 'surface_data'
        assert result['surface_source'] == 'report title'
        assert result['surface'] >= 1
        assert result['identity_check']['consistent'] is not False
        for section, rows in result['surface_power_components'].items():
            assert [row['surface'] for row in rows] == [1, 2]
            selected = result['surface_power'][section]
            assert selected in rows and selected['surface'] == result['surface']
        status = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
        assert status['state'] == 'succeeded' and status['close_attempted']
        assert await e.call('get_surfaces') == before
        e.checks.append(dict(kind='surface_data', surface=result['surface'],
                             unit=result['unit'], identity=result['identity_check']))
    asyncio.run(execute('d008r2', work))


@pytest.mark.zemax
def test_prescription_selected_sections_paging_reload_failure_and_close():
    async def work(e):
        await e.call('open_lens', dict(path=COOKE))
        settings = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        merit = await e.call('get_merit_function')
        request = dict(kind='prescription_data', sections=['files_used', 'general_data', 'index_data'])
        selected = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert selected['selected_section_ids'] == ['general_data', 'index_data', 'files_used']
        assert selected['selection']['requested'] == request['sections']
        assert selected['selection']['native_settings_modified'] is False
        assert selected['task']['settings']['output_selection']['actual'] == selected['selected_section_ids']
        raw = Path(selected['native_text']).read_bytes().decode('utf-16').splitlines(keepends=True)
        with Path(selected['selected_text']).open(encoding='utf-8', newline='') as stream:
            assert stream.read() == ''.join(raw[row['line'] - 1] for row in selected['rows'])
        tid = selected['task']['task_id']
        rows, start = [], 0
        while start is not None:
            page = await e.call('get_task_result', dict(task_id=tid, start=start, count=7))
            rows.extend(page['rows'])
            start = page['next_start']
        assert rows == selected['rows']
        status = await e.call('get_task_status', dict(task_id=tid))
        assert status['state'] == 'succeeded' and status['close_attempted']
        e.checks.append(dict(label='selected native text exact source lines', passed=True,
                             selected=selected['selected_section_ids'], rows=len(rows),
                             settings=selected['task']['settings'], close=status))
        # A single-configuration Cooke report has no multi-config chapter.
        assert 'multi_config_data' not in selected['section_ids']
        failed = await e.call('run_analysis', dict(request=dict(kind='prescription_data', sections=['multi_config_data'])))
        while failed['state'] not in {'failed', 'cancelled', 'succeeded'}:
            await asyncio.sleep(.02)
            failed = await e.call('get_task_status', dict(task_id=failed['task_id']))
        assert failed['state'] == 'failed' and failed['close_attempted']
        assert failed['error']['code'] == 'INVALID_RESULT_DATA'
        assert failed['error']['details']['missing_sections'] == ['multi_config_data']
        await e.call('save_lens_as', dict(path=str(e.folder / 'sections-baseline.zos')))
        await e.call('open_lens', dict(path=str(e.folder / 'sections-baseline.zos')))
        reused = await e.finish(await e.call('run_analysis', dict(request=request)))
        # Header file path changes after SaveAs; compare selected index body instead.
        index = lambda result: next(section['lines'] for section in result['selected_sections'] if section['section_id'] == 'index_data')
        assert index(reused) == index(selected)
        assert await e.call('get_system_settings') == settings
        assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
        assert await e.call('get_merit_function') == merit
        e.checks.append(dict(label='failure close, reuse, reload and source state', passed=True,
                             failed=failed, reused_task=reused['task']['task_id']))
    asyncio.run(execute('prescription_sections', work))
