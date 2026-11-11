import asyncio
import json
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_native_target_surface_intensity_semantics():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5,material_catalogs=['SCHOTT'],wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=0,thickness=3,material='N-BK7',semi_diameter=5,is_stop=True,replace_solves=True),
            dict(surface=2,radius=0,thickness=30,material='',semi_diameter=5,replace_solves=True),
            dict(surface=3,semi_diameter=5,replace_solves=True)]))
        await e.call('save_lens_as',dict(path=str(e.folder/'bare-glass-plate.zos')))
        baseline=await e.call('get_surfaces')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sequential_energy_budget',
            rays=[dict(hx=0,hy=0,px=.2,py=0,wavelength=1)],polarization=dict(jx=1,jy=0),
            first_surface=1,last_surface=3,input_power_w=1))),timeout_seconds=180)
        observations=result['surfaces']
        (e.folder/'target-surface-intensity.json').write_text(json.dumps(observations,indent=2),encoding='utf-8')
        e.check('first surface bare-air/N-BK7 transmission',observations[0]['cumulative_throughput'],.9576119544052238,atol=1e-8,rtol=1e-7)
        e.check('second surface cumulative transmission',observations[1]['cumulative_throughput'],.9165667153412831,atol=1e-8,rtol=1e-7)
        e.check('image-plane intensity after final interface',observations[2]['cumulative_throughput'],observations[1]['cumulative_throughput'])
        assert result['summary']['final_throughput']==pytest.approx(observations[-1]['cumulative_throughput'])
        assert result['resources']['closed_child_tasks']==6
        assert await e.call('get_surfaces')==baseline
        second_wave=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sequential_energy_budget',
            rays=[dict(hx=0,hy=0,px=.2,py=0,wavelength=2)],polarization=dict(jx=1,jy=0),
            first_surface=1,last_surface=3,input_power_w=1))),timeout_seconds=180)
        assert second_wave['summary']['final_throughput'] != pytest.approx(result['summary']['final_throughput'],abs=1e-7)
        assert second_wave['resources']['closed_child_tasks']==6
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=.5))]))
        clipped=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sequential_energy_budget',
            rays=[dict(hx=0,hy=0,px=0,py=0),dict(hx=0,hy=0,px=.8,py=0),dict(hx=0,hy=0,px=-.8,py=0)],
            first_surface=1,last_surface=3))),timeout_seconds=120)
        assert clipped['surfaces'][0]['succeeded']==1 and clipped['surfaces'][0]['vignetted']==2,clipped['surfaces'][0]
        assert clipped['summary']['identified_vignetting_surfaces']==[1]
        assert [r['vignette_code'] for r in clipped['rows']]==[0,1,1]*3
        assert clipped['resources']['closed_child_tasks']==6
    asyncio.run(execute('d022_target_surface_probe',work))


@pytest.mark.zemax
def test_sequential_energy_cancel_closes_active_children():
    async def work(e):
        await e.model()
        rays=[dict(hx=0,hy=0,px=(i%100)/100,py=(i//100)/100) for i in range(5000)]
        task=await e.call('run_analysis',dict(request=dict(kind='sequential_energy_budget',
            rays=rays,first_surface=1,last_surface=3)))
        assert task['state']=='running',task
        deadline=asyncio.get_running_loop().time()+60
        while task.get('progress',0)==0 and task['state']=='running':
            assert asyncio.get_running_loop().time()<deadline,task
            await asyncio.sleep(.02)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='running',task
        await e.call('cancel_task',dict(task_id=task['task_id']))
        while task['state'] not in ('succeeded','failed','cancelled'):
            assert asyncio.get_running_loop().time()<deadline,task
            await asyncio.sleep(.02)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        result=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert result['resources']['child_tasks_closed'] is True
        assert result['resources']['closed_child_tasks'] >= 2
        assert result['resources']['source_model_unchanged'] is True
    asyncio.run(execute('d022_energy_cancel',work))


@pytest.mark.zemax
def test_energy_decentered_aperture_and_multiple_fields():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(aperture_value=5,
            fields=[dict(x=0, y=0), dict(x=1, y=0)])))
        await e.call('update_surfaces', dict(changes=[dict(surface=1, is_stop=True, thickness=10),
            dict(surface=2, aperture=dict(type='CircularAperture', maximum_radius=.5, x_decenter=.2))]))
        rays = [dict(hx=hx, hy=0, px=px, py=0) for hx in (-1, 0, 1) for px in (-.08, .08, .32)]
        result = await e.finish(await e.call('run_analysis', dict(request=dict(
            kind='sequential_energy_budget', rays=rays, first_surface=2, last_surface=2,
            input_power_w=1))), timeout_seconds=120)
        expected = []
        for source, row in zip(rays, result['rows'], strict=True):
            x = 2.5*source['px'] + 10*math.tan(math.radians(source['hx']))
            passed = abs(x-.2) < .5
            expected.append(passed)
            assert row['state'] == ('succeeded' if passed else 'vignetted'), dict(source=source, x=x, actual=row)
        e.check('decentered multi-field geometric fraction', result['summary']['final_throughput'], sum(expected)/len(expected))
        assert result['resources']['closed_child_tasks'] == 2
    asyncio.run(execute('d022_decentered_multifield', work))

