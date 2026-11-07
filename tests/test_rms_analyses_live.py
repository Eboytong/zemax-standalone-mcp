import asyncio,math
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_rms_and_five_plane_statistics():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        settings=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces')
        standard=await e.finish(await e.call('run_spot_analysis',dict(reference='Centroid',field=1,wavelength=1)))
        through=await e.finish(await e.call('run_analysis',dict(request=dict(kind='through_focus_spot',field=1,wavelength=1))))
        assert len(through['rows'])==5 and through['restoration']['restored']
        center=next(r for r in through['rows'] if r['delta_focus_um']==0)
        e.check('zero focus RMS',center['rms_radius'],standard['metrics'][0]['rms_radius'],atol=1e-6,rtol=1e-6)
        assert (await e.call('get_system_settings'))==settings
        assert (await e.call('get_surfaces'))==surfaces
        nominal=surfaces['surfaces'][-2]['cells']['thickness']['value']
        target=surfaces['surfaces'][-2]['surface']
        for plane in through['rows']:
            await e.call('update_surfaces',dict(changes=[dict(surface=target,thickness=nominal+plane['delta_focus_um']*.001,replace_solves=True)]))
            ref=await e.finish(await e.call('run_spot_analysis',dict(reference='Centroid',field=1,wavelength=1)))
            e.check('independent focal plane',plane['rms_radius'],ref['metrics'][0]['rms_radius'],atol=1e-6,rtol=1e-6)
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        for data_type in ('SpotRadius' ,'Spot_X','Spot_Y','Wavefront','StrehlRatio'):
            for kind in ('rms_vs_field','rms_vs_focus'):
                r=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,data_type=data_type,reference='ChiefRay'))))
                assert r['series']
                if data_type=='StrehlRatio':assert all(0<=v<=1 for s in r['series'] for row in s['y'] for v in row if v is not None)
        # Independent uniform pupil quadrature at the on-axis field.
        points=[(2*x/63-1,2*y/63-1) for y in range(64) for x in range(64) if (2*x/63-1)**2+(2*y/63-1)**2<=1]
        rays=[dict(px=x,py=y,wavelength=1) for x,y in points]
        traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
        valid=[r for r in traced['rows'] if r['state']=='succeeded']
        for metric in ('SpotRadius','Spot_X','Spot_Y','Wavefront'):
            r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',data_type=metric,reference='ChiefRay'))))
            if metric=='Wavefront':
                values=[x['opd'] for x in valid];mean=sum(values)/len(values);expected=math.sqrt(sum((v-mean)**2 for v in values)/len(values))
                e.check('RMS wavefront quadrature',r['series'][0]['y'][0][0],expected,atol=1e-5,rtol=.01)
            else:
                axes=(0,1) if metric=='SpotRadius' else (0,) if metric=='Spot_X' else (1,)
                expected=1000*math.sqrt(sum(sum(x['position'][a]**2 for a in axes) for x in valid)/len(valid))
                e.check('RMS pupil '+metric,r['series'][0]['y'][0][0],expected,atol=.05,rtol=.01)
        focus=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_focus',reference='ChiefRay'))))
        for index in (0,-1):
            dz=focus['series'][0]['x'][index]
            expected=1000*math.sqrt(sum((r['position'][0]+dz*r['direction'][0]/r['direction'][2])**2+(r['position'][1]+dz*r['direction'][1]/r['direction'][2])**2 for r in valid)/len(valid))
            e.check('RMS shifted pupil',focus['series'][0]['y'][index][0],expected,atol=.05,rtol=.01)
        for request in [dict(kind='rms_vs_field' ,method='GaussQuad'),dict(kind='rms_vs_field',wavelength=0),dict(kind='rms_vs_focus',wavelength=0,use_polarization=True)]:
            await e.finish(await e.call('run_analysis',dict(request=request)))
        await e.call('export_analysis_image',dict(request=dict(task_id=through['task']['task_id'],path=str(e.folder/'five-plane.png'))))
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=4,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-100,conic=-1,material='MIRROR',thickness=-50,replace_solves=True)]))
        before=await e.call('get_surfaces')
        mirror=await e.finish(await e.call('run_analysis',dict(request=dict(kind='through_focus_spot'))))
        assert mirror['restoration']['restored']
        assert (await e.call('get_surfaces'))==before
        task=await e.call('run_analysis',dict(request=dict(kind='through_focus_spot',ray_density=40)))
        for _ in range(1000):
            stage=await e.call('get_task_status',dict(task_id=task['task_id']))
            if stage.get('progress',0) is not None and stage.get('progress',0)>=20:break
            await asyncio.sleep(.02)
        assert stage['state'] not in ('failed','succeeded')
        await e.call('cancel_task',dict(task_id=task['task_id']))
        for _ in range(1000):
            status=await e.call('get_task_status',dict(task_id=task['task_id']))
            if status['state'] in ('cancelled','failed','succeeded'):break
            await asyncio.sleep(.02)
        assert status['state']=='cancelled'
        assert (await e.call('get_surfaces'))==before
    asyncio.run(execute('rms_validation',work))
