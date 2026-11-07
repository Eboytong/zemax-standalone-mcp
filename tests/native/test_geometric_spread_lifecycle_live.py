"""Geometric spread selection, four-column paging and lifecycle."""
import asyncio
import json
import time
from pathlib import Path

from PIL import Image
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_geometric_spread_selection_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        image=baseline['surfaces'][-1]['surface']
        q=dict(kind='geometric_line_edge_spread',field=3,wavelength=2,surface=image,
               sampling='S_256x256',radius_maximum=50,use_polarization=True)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        native=result['task']['settings']['native']
        assert native['Field']==3 and native['Wavelength']==2 and native['Surface']==image
        assert native['UsePolarization'] is True and native['RadiusMaximum']==50
        curve=result['series'][0]
        assert curve['labels']==['X_LSF','X_ESF','Y_LSF','Y_ESF'] and curve['x_unit']=='micrometers'
        for column in [1,3]:
            values=[row[column] for row in curve['y']]
            assert all(0<=v<=1 for v in values) and all(b>=a for a,b in zip(values,values[1:]))
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=3,count=7))
        assert page['series'][0]['x']==curve['x'][3:10] and page['series'][0]['y']==curve['y'][3:10]
        png=e.folder/'geometric-spread.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png))))
        with Image.open(png) as bitmap:assert bitmap.width>0 and bitmap.height>0
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
    asyncio.run(execute('geometric_spread325_lifecycle',work))
