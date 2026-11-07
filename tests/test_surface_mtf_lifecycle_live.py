"""Analytic mirror reference, rectangular result page and analysis lifecycle."""
import asyncio
import json
import math
import time
from pathlib import Path

import pytest

from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('family',['fft','huygens'])
def test_surface_mtf_frequency_axis_labels_and_plot(family):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=family+'_surface_mtf',field=3,wavelength=1))))
        grid=result['grids'][0]
        assert grid['x_label']=='Spatial frequency X' and grid['y_label']=='Spatial frequency Y'
        assert grid['native_axis_labels']==dict(x_label='None',y_label='None')
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=3,y_start=5,width=7,height=5))
        assert page['grid']['values']==[row[3:10] for row in grid['values'][5:10]]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'surface.png'))))
        task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert task['state']=='succeeded' and task['close_attempted']
    asyncio.run(execute('surface_mtf287_'+family,work))


@pytest.mark.zemax
def test_huygens_surface_mtf_mirror_reference_and_lifecycle():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,
            material='MIRROR',thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        saved=str(e.folder/'mirror.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function')
        request=dict(kind='huygens_surface_mtf',field=1,wavelength=1,sampling='S_256x256',
                     image_sampling='S_512x512',image_delta=1,mtf_type='MTF_Incoherent')
        (e.folder/'reference.json').write_text(json.dumps(dict(
            item_id='CV-01.HuygensSurfaceMtf',model='On-axis paraboloid R=-200mm K=-1, pupil diameter10mm, image thickness-100mm, wavelength.55um',
            cutoff_cycles_per_mm=10/(.00055*100),reference='2/pi * (acos(v) - v*sqrt(1-v*v)) for circular pupil',
            absolute_tolerance=.005,relative_tolerance=0,request=request),indent=2),encoding='utf-8')
        result=await e.finish(await e.call('run_analysis',dict(request=request)),timeout_seconds=180)
        g=result['grids'][0];cx=g['zero_frequency_index']['x'];cy=g['zero_frequency_index']['y']
        failures=[]
        for ax,ay in [(1,0),(0,1),(.6,.8)]:
            for v in [0,.15,.3,.5,.7,.85]:
                ix=cx+round(v*10/(.00055*100)*ax/g['dx'])
                iy=cy+round(v*10/(.00055*100)*ay/g['dy'])
                fx=g['min_x']+ix*g['dx'];fy=g['min_y']+iy*g['dy']
                v=math.hypot(fx,fy)*.00055*100/10
                expected=2/math.pi*(math.acos(v)-v*math.sqrt(1-v*v))
                try:e.check(f'paraboloid circular MTF ({fx},{fy})',g['values'][iy][ix],expected,atol=.005,rtol=0)
                except AssertionError:failures.append(e.checks[-1])
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,
            x_start=cx-3,y_start=cy-2,width=7,height=5))
        assert len(page['grid']['values'])==5 and all(len(row)==7 for row in page['grid']['values'])
        assert page['grid']['values']==[row[cx-3:cx+4] for row in g['values'][cy-2:cy+3]]
        (e.folder/'page.json').write_text(json.dumps(page,indent=2),encoding='utf-8')
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'surface.png'))))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        bad=await e.call('run_analysis',dict(request=request|dict(field=2)),okay=False)
        assert bad['ok'] is False and bad['error']['code']=='INDEX_OUT_OF_RANGE',bad
        # A running high-sampling analysis gives cancellation a real native target.
        task=await e.call('run_analysis',dict(request=request|dict(sampling='S_512x512',image_sampling='S_1024x1024')))
        assert task['state']=='running',task
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.05)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled' and task['close_attempted'],task
        await e.call('get_task_result',dict(task_id=task['task_id']))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        recovered=await e.finish(await e.call('run_analysis',dict(request=request|dict(sampling='S_64x64',image_sampling='S_64x64'))))
        assert (await e.call('get_task_status',dict(task_id=recovered['task']['task_id'])))['close_attempted']
        await e.call('save_lens_as',dict(path=str(e.folder/'after.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'after.zos')))
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('surface_mtf286_huygens',work))
