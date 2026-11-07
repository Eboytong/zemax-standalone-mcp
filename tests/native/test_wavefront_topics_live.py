import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('kind', ['zernike_coefficients_vs_field', 'interferogram'])
def test_wavefront_topics_native_readback_results_and_close(kind):
    async def work(e):
        sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', {'path': str(sample)})
        result = await e.finish(await e.call('run_analysis', {'request': {'kind': kind}}))
        assert result['analysis_kind'] == kind
        assert result['artifacts']
        settings = result['task']['settings']['native']
        if kind == 'zernike_coefficients_vs_field':
            assert settings['Coefficients'] == '4,5,6'
            assert result['series']
        else:
            assert settings['Beam_1'] == 'Reference'
            assert settings['Beam_2'] == 'Configuration_1'
    asyncio.run(execute(kind, work))
