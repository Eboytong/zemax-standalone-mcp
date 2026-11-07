"""Contrast Loss field/wavelength, display toggles and serial recovery."""
import asyncio
import json
import time
from pathlib import Path

from PIL import Image
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_contrast_loss_selection_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function')
        q=dict(kind='contrast_loss',field=2,wavelength=2,sampling='S_21x21',frequency=50)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        native=result['task']['settings']['native']
        assert native['Field']==2 and native['Wavelength']==2 and native['Frequency']==50
        assert [g['direction'] for g in result['grids']]==['Tangential','Tangential','Sagittal','Sagittal']
        other=await e.finish(await e.call('run_analysis',dict(request=q|dict(normalize=False,show_opd=True))))
        for a,b in zip(result['grids'],other['grids']):
            assert a['values']==b['values']
            assert a['invalid_count']==sum(v is None for row in a['values'] for v in row)
        grid=result['grids'][1]
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=1,x_start=3,y_start=2,width=5,height=4))
        assert page['grid']['values']==[row[3:8] for row in grid['values'][2:6]]
        png=e.folder/'contrast-loss.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png),item=len(result.get('series',[]))+1)))
        with Image.open(png) as image:assert image.width>0 and image.height>0
        error=await e.call('run_analysis',dict(request=q|dict(field=999)),okay=False)
        assert error['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=q|dict(sampling='S_83x83')))
        assert task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.05);task=await e.call('get_task_status',dict(task_id=task['task_id']))
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
    asyncio.run(execute('contrast_loss314_lifecycle',work))
