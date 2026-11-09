import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('kind', ['seidel_diagram', 'surface_slope', 'surface_slope_cross',
                                 'surface_phase_slope', 'surface_phase_slope_cross'])
def test_seidel_slopes_native_settings_results_and_close(kind):
    async def work(e):
        sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', {'path': str(sample)})
        request = {'kind': kind}
        if kind=='seidel_diagram':request['method']='native'
        if kind.startswith('surface_'):
            request['surface'] = 1
        task = await e.call('run_analysis', {'request': request})
        if kind == 'seidel_diagram':
            while task['state'] not in {'succeeded', 'failed', 'cancelled'}:
                await asyncio.sleep(.02)
                task = await e.call('get_task_status', {'task_id': task['task_id']})
            assert task['state'] == 'failed'
            assert task['error']['code'] == 'EXPORT_FAILED'
            assert task['close_attempted'] is True
            native = task['settings']['native']
            assert native['IgnoreChromatic'] is False
            assert native['IgnoreDistortion'] is False
            assert native['SuppressFrame'] is False
            assert native['PlotScale'] == 0
            result = await e.call('get_task_result', {'task_id': task['task_id']})
            assert result['completed'] is False
            assert result['task']['error']['code'] == 'EXPORT_FAILED'
            assert result['artifacts'] == []
            return
        result = await e.finish(task)
        assert result['analysis_kind'] == kind
        assert result['artifacts']
        native = result['task']['settings']['native']
        if kind.startswith('surface_'):
            assert native['Surface'] == 1
            assert native['Sampling'] == ('S_65' if kind.endswith('_cross') else 'S_65x65')
        else:
            assert native['IgnoreChromatic'] is False
    asyncio.run(execute(kind, work))
