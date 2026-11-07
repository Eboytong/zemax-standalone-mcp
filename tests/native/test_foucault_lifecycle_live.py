"""Public BMP input, selection, result paging and serial lifecycle acceptance."""
import asyncio
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_foucault_source_selection_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function')
        q=dict(kind='foucault',field=2,wavelength=2,use_polarization=True,sampling='S_64x64',show_as='GreyScale')
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        native=result['task']['settings']['native']
        assert native['Field']==2 and native['Wavelength']==2 and native['UsePolarization'] is True
        grid=result['grids'][0]
        assert grid['value_unit']=='dimensionless' and grid['invalid_count']==0
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=1,y_start=2,width=4,height=3))
        assert page['grid']['values']==[row[1:5] for row in grid['values'][2:5]]
        png=e.folder/'foucault.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png),item=len(result['series']))))
        with Image.open(png) as image:
            assert image.width>0 and image.height>0
        source=e.folder/'reference.bmp'
        pixels=np.zeros((64,64,3),dtype=np.uint8);pixels[:,32:]=255
        Image.fromarray(pixels).save(source)
        reference=await e.finish(await e.call('run_analysis',dict(request=q|dict(data='Reference',source=str(source)))))
        (e.folder/'reference.json').write_text(json.dumps(reference,ensure_ascii=False,indent=2),encoding='utf-8')
        assert reference['task']['settings']['native']['Source']==str(source)
        np.testing.assert_array_equal(reference['grids'][0]['values'],pixels[:,:,0]/255)
        difference=await e.finish(await e.call('run_analysis',dict(request=q|dict(data='Difference',source=str(source)))))
        assert difference['grids'][0]['nx']==64 and difference['grids'][0]['invalid_count']==0
        for patch,code in [(dict(field=999),'INDEX_OUT_OF_RANGE'),
                           (dict(source=str(e.folder/'missing.bmp')),'FILE_NOT_FOUND'),
                           (dict(source=str(e.folder/'wrong.png')),'INVALID_ARGUMENT')]:
            error=await e.call('run_analysis',dict(request=q|patch),okay=False)
            assert error['error']['code']==code,error
        task=await e.call('run_analysis',dict(request=q|dict(sampling='S_1024x1024')))
        assert task['state']=='running',task
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.05)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled' and task['close_attempted'],task
        await e.call('get_task_result',dict(task_id=task['task_id']))
        await e.finish(await e.call('run_analysis',dict(request=q)))
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        saved=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('foucault298_lifecycle',work))
