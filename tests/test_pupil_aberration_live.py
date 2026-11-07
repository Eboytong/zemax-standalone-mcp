import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_pupil_aberration_planar_stop_reference():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        source=str(e.folder/'stop.zos');await e.call('save_lens_as',dict(path=source));await e.call('open_lens',dict(path=source))
        baseline=await e.call('get_surfaces',dict(request={}))
        for wave in [0,1,2]:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='pupil_aberration_fan',number_of_rays=21,wavelength=wave))))
            for curve in result['series']:
                for row in curve['y']:
                    for v in row:
                        if v is not None:e.check('stop in entrance-pupil plane: percent aberration',v,0,atol=1e-8,rtol=1e-7)
            assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
            page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=2,count=3))
            assert page['series'][0]['y']==result['series'][0]['y'][2:5]
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/f'pupil_{wave}.png'))))
        assert await e.call('get_surfaces',dict(request={}))==baseline
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(sample)))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='pupil_aberration_fan',number_of_rays=21,wavelength=1))))
        (e.folder/'cooke-characterization.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        settings=result['system_settings'];primary=next(w['number']for w in settings['wavelengths']if w['primary'])
        stop=result['stop_surface']
        marginal=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(ray_type='Paraxial',target_surface=stop,rays=[dict(px=0,py=1,wavelength=primary)]))))
        radius=marginal['rows'][0]['position'][1]
        rays=[];parax=[];expected=[]
        for i,curve in enumerate(result['series']):
            field=settings['fields'][i//2];axis=1 if i%2==0 else 0
            for p,values in zip(curve['x'],curve['y']):
                if values[0]is None:continue
                pupil=dict(px=p if axis==0 else 0,py=p if axis==1 else 0)
                rays.append(dict(hx=field['x']/20,hy=field['y']/20,wavelength=1,**pupil))
                parax.append(dict(wavelength=primary,**pupil))
                expected.append((axis,values[0]))
        real=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(target_surface=stop,rays=rays))))
        ref=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(target_surface=stop,ray_type='Paraxial',rays=parax))))
        comparisons=[]
        for (axis,value),r,p in zip(expected,real['rows'],ref['rows']):
            assert r['position']is not None and p['position']is not None
            reference=100*(p['position'][axis]-r['position'][axis])/radius
            comparisons.append(dict(value=value,reference=reference,error=abs(value-reference)))
        (e.folder/'cooke-stop-comparisons.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
        for item in comparisons:e.check('Cooke primary paraxial minus real stop intercept [%]',item['value'],item['reference'],atol=1e-8,rtol=1e-7)
        current=await e.call('get_surfaces',dict(request={}))
        task=await e.call('run_analysis',dict(request=dict(kind='pupil_aberration_fan',number_of_rays=10001)))
        started_running=task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        import time
        deadline=time.monotonic()+60
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'cancelled','succeeded'} and task['close_attempted'],task
        (e.folder/'cancellation.json').write_text(json.dumps(dict(started_running=started_running,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces',dict(request={}))==current
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='pupil_aberration_fan',field=1,wavelength=1,number_of_rays=3))))
    asyncio.run(execute('pupil073',work))
