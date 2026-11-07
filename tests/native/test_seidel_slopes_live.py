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
        if kind.startswith('surface_'):
            request['surface'] = 1
        result = await e.finish(await e.call('run_analysis', {'request': request}))
        assert result['analysis_kind'] == kind
        assert result['artifacts']
        native = result['task']['settings']['native']
        if kind.startswith('surface_'):
            assert native['Surface'] == 1
            assert native['Sampling'] == ('S_65' if kind.endswith('_cross') else 'S_65x65')
        else:
            assert native['IgnoreChromatic'] is False
    asyncio.run(execute(kind, work))
