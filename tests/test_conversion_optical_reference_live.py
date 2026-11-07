"""Serial, polarized critical-ray equivalence for both native conversion modes."""
import asyncio
import json
import math

import pytest

from support.native import execute
from support.nsc import trace
from test_pure_conversion_reference_live import compare_saved


RAYS = [dict(x=x, y=y, z=0, l=l, m=m,
             n=math.sqrt(1-l*l-m*m), wavelength=1)
        for x, y, l, m in [(0, 0, 0, 0), (.2, -.3, 0, 0),
                            (-.2, .1, .03, 0), (.1, .2, -.02, .025)]]


async def setup(e):
    await e.call('new_system')
    await e.call('insert_surfaces', dict(at=1, count=4))
    await e.call('update_system_settings', dict(settings=dict(
        aperture_value=4, wavelengths=[dict(wavelength_um=.55)],
        polarization=dict(unpolarized=False, jx=1, jy=0, x_phase=0, y_phase=0))))
    await e.call('update_surfaces', dict(changes=[dict(change,replace_solves=True) for change in [
        dict(surface=0, thickness=1),
        dict(surface=1, radius='Infinity', thickness=1, semi_diameter=5),
        dict(surface=2, radius='Infinity', thickness=2, material='N-BK7', semi_diameter=5),
        dict(surface=3, radius='Infinity', thickness=1, material='', semi_diameter=5),
        dict(surface=4, radius='Infinity', thickness=1, semi_diameter=5),
    ]]))
    path=str(e.folder/'sequential-baseline.zos')
    await e.call('save_lens_as', dict(path=path))
    await e.call('open_lens', dict(path=path))


async def sequential(e):
    result=await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
        input_mode='Direct', start_surface=0, rays=RAYS,
        polarization=dict(jx=1, jy=0)))))
    assert len(result['rows'])==len(RAYS)
    assert all(r['state']=='succeeded' for r in result['rows']), result['rows']
    assert all(.8<r['intensity']<1 for r in result['rows'])
    return result['rows']


def compare(e, actual, expected, label):
    for i, (a,b) in enumerate(zip(actual,expected,strict=True)):
        assert a['state']==b['state']=='succeeded'
        for k in range(3):
            e.check(f'{label} ray{i} position{k}', a['position'][k], b['position'][k], atol=1e-7, rtol=1e-7)
            e.check(f'{label} ray{i} direction{k}', a['direction'][k], b['direction'][k], atol=1e-7, rtol=0)
        e.check(f'{label} ray{i} power', a['intensity'], b['intensity'], atol=1e-8, rtol=1e-7)


def persisted_optics(objects):
    keys=['object','type','x','y','z','tilt_x','tilt_y','tilt_z','ref_object','inside_of',
          'material','data','parameter_cells','global_transform','faces','volume']
    return [dict({k:r[k] for k in keys},sources=r['sources'] if r['sources']['IsSourcesAvailable'] else None)
            for r in objects['rows']]


async def pure_rays(e,detector,origin_shift,stage):
    rows=[]
    for i,ray in enumerate(RAYS):
        await e.call('update_nsc_objects',dict(request=dict(changes=[dict(
            object=detector+1,object_type='SourceRay',
            x=ray['x'],y=ray['y'],z=ray['z']+origin_shift,
            data=dict(NumberOfAnalysisRays=1,Power=1,XCosine=ray['l'],YCosine=ray['m'],ZCosine=ray['n']),
            sources=dict(RandomPolarization=False,Jx=1,Jy=0,XPhase=0,YPhase=0))])))
        result,segments=await trace(e,stage+'_critical_'+str(i),use_polarization=True,split_rays=False)
        hit=next(r for r in segments if r['HitObject']==detector)
        rows.append(dict(state='succeeded', position=[hit['X'],hit['Y'],hit['Z']-origin_shift-6],
                         direction=[hit['L'],hit['M'],hit['N']], intensity=hit['Intensity']))
        status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert status['state']=='succeeded' and status['close_attempted']
    return rows


@pytest.mark.zemax
@pytest.mark.parametrize('mode',['pure','group'])
def test_conversion_polarized_plane_reference(mode):
    blocked=[]
    async def work(e):
        (e.folder/'reference.json').write_text(json.dumps(dict(
            item_id='NS-01.Conversion', mode=mode,
            model='Air 2 mm / N-BK7 plane plate 2 mm / air 2 mm; image global z=6 mm',
            rays=RAYS, position_atol=1e-7, position_rtol=1e-7,
            direction_atol=1e-7, direction_rtol=0, power_atol=1e-8, power_rtol=1e-7,
            reference='Polarized sequential direct rays before native conversion; native pure-conversion image origin shift -6 mm; deterministic SourceRay Jx=1 Jy=0'),
            indent=2),encoding='utf-8')
        await setup(e)
        baseline_surfaces=await e.call('get_surfaces')
        baseline_settings=await e.call('get_system_settings')
        baseline_merit=await e.call('get_merit_function')
        before=await sequential(e)
        started=await e.call('run_nsc_conversion',dict(request=dict(
            mode=mode, first_surface=1, last_surface=4,
            convert_stop_to_nsc_aperture=False, convert_to_global_coordinates=True)),okay=False)
        if mode=='group' and started.get('ok') is False:
            assert started['error']['code']=='TASK_START_FAILED',started
            assert started['error']['message']=='An unknown error occurred',started
            status=await e.call('get_task_status',dict(task_id=started['error']['details']['task_id']))
            assert status['state']=='failed' and status['close_attempted'],status
            await e.call('open_lens',dict(path=started['context']['checkpoint']))
            compare_saved(e,await e.call('get_surfaces'),baseline_surfaces,'failed group restored surfaces')
            compare(e,await sequential(e),before,'failed group restored')
            blocked.append('2024 R2 controlled dummy-boundary group conversion: native unknown start error; checkpoint restore/retrace accepted')
            return
        conversion=await e.finish(started)
        task=await e.call('get_task_status',dict(task_id=conversion['task']['task_id']))
        assert task['state']=='succeeded' and task['close_attempted']
        selection={} if mode=='pure' else dict(nsc_surface=conversion['after']['nsc_groups'][0])
        objects=await e.call('get_nsc_objects',dict(request=dict(start=1,count=20,**selection)))
        (e.folder/'converted-object-mapping.json').write_text(json.dumps(dict(
            sequential=baseline_surfaces,converted=objects,conversion=conversion),indent=2),encoding='utf-8')
        glass=[r for r in objects['rows'] if r['material']=='N-BK7']
        assert len(glass)==1 and glass[0]['type']=='StandardLens', objects
        e.check('mapped plane plate thickness',glass[0]['data']['Thickness'],2,atol=1e-10,rtol=0)
        if mode=='pure':
            # Native pure conversion uses the former image as its origin.
            # Its plate front is at -4 rather than sequential global +2.
            origin_shift=-6
            e.check('mapped plate front in image-origin frame',glass[0]['global_transform']['translation'][2],-4,atol=1e-10,rtol=0)
            count=conversion['after']['object_count']
            await e.call('insert_nsc_objects',dict(request=dict(at=count+1,count=2)))
            detector=count+1
            await e.call('update_nsc_objects',dict(request=dict(changes=[dict(
                object=detector,object_type='DetectorRectangle',z=6+origin_shift,
                data=dict(NumberXPixels=7,NumberYPixels=5))])))
            after=await pure_rays(e,detector,origin_shift,'converted')
        else:
            after=await sequential(e)
        compare(e,after,before,'converted')
        saved=str(e.folder/f'converted-{mode}.zos')
        objects_before=await e.call('get_nsc_objects',dict(request=dict(start=1,count=20,**selection)))
        await e.call('save_lens_as',dict(path=saved))
        await e.call('open_lens',dict(path=saved))
        objects_after=await e.call('get_nsc_objects',dict(request=dict(start=1,count=20,**selection)))
        (e.folder/'reload-properties.json').write_text(json.dumps(dict(before=objects_before,after=objects_after),indent=2),encoding='utf-8')
        compare_saved(e,persisted_optics(objects_after),persisted_optics(objects_before))
        compare(e,await pure_rays(e,detector,origin_shift,'reloaded') if mode=='pure' else await sequential(e),before,'reloaded')
        await e.call('open_lens',dict(path=conversion['checkpoint']))
        compare_saved(e,await e.call('get_surfaces'),baseline_surfaces,'restored surfaces')
        assert await e.call('get_merit_function')==baseline_merit
        restored=await e.call('get_system_settings')
        for key in ['lens_units','configuration','polarization','wavelengths']:
            if key in baseline_settings:compare_saved(e,restored[key],baseline_settings[key],'restored '+key)
        compare(e,await sequential(e),before,'restored')
    asyncio.run(execute('conversion277_'+mode,work))
    if blocked:pytest.xfail(blocked[0])
