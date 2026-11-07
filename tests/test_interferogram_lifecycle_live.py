"""Interferogram selection, vertex reference, subpupil and task lifecycle."""
import asyncio
import json
import time
from pathlib import Path

from PIL import Image
import pytest
from support.native import execute


@pytest.mark.zemax
def test_interferogram_selection_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function');mce=await e.call('get_configurations',dict(request={}))
        q=dict(kind='interferogram',field=2,wavelength=2,show_as='GreyScale',x_tilt=2,y_tilt=1,
               subaperture_x=.1,subaperture_y=-.2,subaperture_radius=.6)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        native=result['task']['settings']['native']
        assert native['Field']==2 and native['Wavelength']==2
        assert native['Subaperture_X']==.1 and native['Subaperture_R']==.6
        grid=result['grids'][0]
        assert grid['value_unit']=='dimensionless' and grid['array_order']=='values[y][x]'
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=3,y_start=2,width=5,height=4))
        assert page['grid']['values']==[row[3:8] for row in grid['values'][2:6]]
        png=e.folder/'interferogram.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png),item=len(result.get('series',[])))))
        with Image.open(png) as image:assert image.width>0 and image.height>0
        vertex=q|dict(beam_1='Configuration_1',beam_2='Configuration_1',
                      ref_beam_1_to_vertex=True,ref_beam_2_to_vertex=True)
        checked=await e.finish(await e.call('run_analysis',dict(request=vertex)))
        assert checked['task']['settings']['native']['Ref_Beam_1_To_Vertex'] is True
        assert checked['task']['settings']['native']['Ref_Beam_2_To_Vertex'] is True
        for patch in [dict(field=999),dict(beam_2='Configuration_2')]:
            error=await e.call('run_analysis',dict(request=q|patch),okay=False)
            assert error['error']['code']=='INDEX_OUT_OF_RANGE',error
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
            assert await e.call('get_configurations',dict(request={}))==mce
        await unchanged()
        saved=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        await unchanged()
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('interferogram307_lifecycle',work))
