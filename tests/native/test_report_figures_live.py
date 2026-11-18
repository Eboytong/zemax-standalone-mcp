import asyncio
from pathlib import Path

import pytest
from PIL import Image

from tests.support.native import execute


@pytest.mark.zemax
def test_report_figures_over_stdio():
    async def work(e):
        sample = Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', dict(path=str(sample)))

        async def view(name, arguments):
            task = await e.call(name, arguments)
            await e.finish(task)
            return await e.call('get_task_result', dict(task_id=task['task_id']))

        async def export(result, filename, **kwargs):
            return await e.call('export_analysis_image', dict(request=dict(
                task_id=result['task']['task_id'], path=str(e.folder / filename), **kwargs)))

        layout = await view('run_layout_export', dict(request=dict(path=str(e.folder / 'layout.png'))))
        assert layout['image_exports']['available_sources'] == ['native']
        assert layout['image_exports']['native_images'][0]['image_source'] == 'native'
        assert (await export(layout, 'layout-copy.png', source='native'))['image_source'] == 'native'

        fft = await view('run_fft_mtf', dict(field=1, sampling='S_64x64'))
        assert fft['image_exports']['available_sources'] == ['data_plot']
        page = await e.call('get_task_result', dict(task_id=fft['task']['task_id'], series=0, count=3))
        assert page['image_exports'] == fft['image_exports']
        plot = await export(fft, 'mtf.png')
        assert plot['image_source'] == 'data_plot'
        assert plot['plotting_settings']['data_source'] == 'OpticStudio FFT MTF'

        spot = await view('run_spot_analysis', dict(reference='Centroid', field=1))
        assert spot['metrics'][0]['rms_radius'] > 0
        failed = await e.call('export_analysis_image', dict(request=dict(
            task_id=spot['task']['task_id'], path=str(e.folder / 'spot-native.png'), source='native')), okay=False)
        assert failed['error']['code'] == 'UNSUPPORTED_NATIVE_IMAGE'
        assert failed['error']['details']['alternative']['capability_id'] == 'tool:run_batch_ray_trace'

        rays = [dict(hy=hy, px=px, py=py, wavelength=wavelength)
                for hy in (0, .4) for wavelength in (1, 2)
                for px, py in ((0, 0), (.4, .2), (-.4, -.2), (.1, -.5))]
        batch = await view('run_batch_ray_trace', dict(request=dict(rays=rays)))
        assert batch['image_exports']['data_plot_items'] == 2
        plotted = await export(batch, 'spot-intercepts.png', item=1)
        assert plotted['image_source'] == 'data_plot'
        assert plotted['plotting_settings']['field'] == [0, .4]
        assert plotted['plotting_settings']['point_count'] == sum(
            row['state'] == 'succeeded' and row['input']['hy'] == .4 for row in batch['rows'])
        for filename in ('layout.png', 'layout-copy.png', 'mtf.png', 'spot-intercepts.png'):
            with Image.open(e.folder / filename) as image:
                image.load()
                assert image.format == 'PNG'
                assert len(set(image.convert('L').getextrema())) == 2

    asyncio.run(execute('report_figures', work))
