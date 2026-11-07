import asyncio
from pathlib import Path

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_rms_wavelength_settings_curve_and_close():
    async def work(e):
        sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', {'path': str(sample)})
        task = await e.call('run_analysis', {'request': {
            'kind': 'rms_vs_wavelength', 'field': 1, 'sampling': 'S_256x256',
            'wavelength_density': 20, 'data_type': 'SpotRadius'}})
        result = await e.finish(task)
        assert result['analysis_kind'] == 'rms_vs_wavelength'
        assert result['series']
        assert result['task']['settings']['native']['WaveDensity'] == 'WaveDens_20'
        for series in result['series']:
            assert series['x_unit'] == 'micrometers'
            assert len(series['x']) > 1
            assert max(series['x']) > min(series['x'])
    asyncio.run(execute('rms_wavelength', work))
