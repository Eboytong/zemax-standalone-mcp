"""FFT spread selection, native display scale, paging and task lifecycle."""
import asyncio
import json
import time
from pathlib import Path

from PIL import Image
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_fft_spread_selection_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        q=dict(kind='fft_line_edge_spread',field=2,wavelength=2,sampling='S_128x128',spread='Edge',
               data_type='Y_Linear',use_polarization=True,plot_scale=30)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        native=result['task']['settings']['native']
        assert native['Field']==2 and native['Wavelength']==2 and native['UsePolarization'] is True and native['PlotScale']==30
        curve=result['series'][0]
        assert curve['scan_axis']=='X' and curve['value_units']==['relative intensity']
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=3,count=7))
        assert page['series'][0]['x']==curve['x'][3:10] and page['series'][0]['y']==curve['y'][3:10]
        png=e.folder/'fft-edge.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png))))
        with Image.open(png) as image:assert image.width>0 and image.height>0
        poly=await e.finish(await e.call('run_analysis',dict(request=q|dict(wavelength=0))))
        assert poly['task']['settings']['native']['Wavelength']==0 and poly['series']
        error=await e.call('run_analysis',dict(request=q|dict(wavelength=999)),okay=False)
        assert error['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=q|dict(sampling='S_1024x1024')))
        assert task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.05);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled' and task['close_attempted'],task
        await e.call('get_task_result',dict(task_id=task['task_id']))
        await e.finish(await e.call('run_analysis',dict(request=q)))
        async def unchanged():
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
        await unchanged()
        saved=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        await unchanged()
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('fft_spread319_lifecycle',work))
