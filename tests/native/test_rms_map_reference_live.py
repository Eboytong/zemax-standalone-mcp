"""Non-square RMS map axes and independent rectangular-pupil quadrature."""
import asyncio
import json
import math
from pathlib import Path

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_rms_map_native_quadrature():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_system_settings',dict(settings=dict(field_normalization='Radial',
            fields=[dict(x=0,y=0),dict(x=3,y=10),dict(x=0,y=20)],
            wavelengths=[dict(wavelength_um=.55)])))
        source=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=source));await e.call('open_lens',dict(path=source))
        baseline=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces')
        request=dict(kind='rms_field_map',field=2,wavelength=1,x_field_sampling=7,y_field_sampling=5,
            x_field_size=4,y_field_size=2,sampling='S_128x128')
        records=[];traces={}
        pupils=[(2*x/127-1,2*y/127-1)for y in range(128)for x in range(128)if (2*x/127-1)**2+(2*y/127-1)**2<=1]
        for reference in ['Centroid','ChiefRay']:
            for metric in ['SpotRadius','Spot_X','Spot_Y','Wavefront']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(**request,reference=reference,data_type=metric))))
                records.append(result)
                (e.folder/'map-results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                grid=result['grids'][0]
                assert grid['nx']==7 and grid['ny']==5 and len(grid['values'])==5
                # Native width/axes are checked before using them as ray inputs.
                e.check('center X',grid['min_x']+3*grid['dx'],3,atol=1e-10,rtol=1e-10)
                e.check('center Y',grid['min_y']+2*grid['dy'],10,atol=1e-10,rtol=1e-10)
                e.check('X full width',6*grid['dx'],8,atol=1e-10,rtol=1e-10)
                e.check('Y full width',4*grid['dy'],4,atol=1e-10,rtol=1e-10)
                for ix,iy in [(0,0),(3,2),(6,4)]:
                    x=grid['min_x']+ix*grid['dx'];y=grid['min_y']+iy*grid['dy']
                    key=(ix,iy)
                    if key not in traces:
                        rays=[dict(hx=x/20,hy=y/20,px=px,py=py,wavelength=1)for px,py in [(0,0),*pupils]]
                        traces[key]=[]
                        for start in range(0,len(rays),8192):
                            traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays[start:start+8192],opd=True))))
                            traces[key].extend(traced['rows'])
                    rows=traces[key];chief=rows[0];valid=[r for r in rows[1:]if r['state']=='succeeded']
                    assert valid and chief['state']=='succeeded'
                    if metric=='Wavefront':
                        opd=[r['opd']for r in valid];mean=sum(opd)/len(opd)
                        expected=math.sqrt(sum((v-mean)**2 for v in opd)/len(opd))
                        if reference=='Centroid':
                            # Centroid wavefront includes native tilt removal;
                            # compare its unit/range, use ChiefRay for OPD reference.
                            assert 0<=grid['values'][iy][ix]<10
                            continue
                        e.check('map OPD quadrature',grid['values'][iy][ix],expected,atol=1e-5,rtol=.01)
                    else:
                        axes=(0,1)if metric=='SpotRadius'else (0,)if metric=='Spot_X'else(1,)
                        center=[sum(r['position'][a]for r in valid)/len(valid)for a in range(2)]if reference=='Centroid'else chief['position'][:2]
                        expected=1000*math.sqrt(sum(sum((r['position'][a]-center[a])**2 for a in axes)for r in valid)/len(valid))
                        e.check('map '+reference+' '+metric,grid['values'][iy][ix],expected,atol=.05,rtol=.01)
                task_id=result['task']['task_id']
                page=await e.call('get_task_result',dict(task_id=task_id,grid=0,x_start=1,y_start=2,width=3,height=2))
                assert page['grid']['values']==[r[1:4]for r in grid['values'][2:4]]
                await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/f'{reference}_{metric}.png'))))
                assert (await e.call('get_task_status',dict(task_id=task_id)))['close_attempted']
        for options in [dict(method='GaussQuad',rings=5),dict(data_type='StrehlRatio'),dict(wavelength=0,use_polarization=True,remove_vignetting_factors=False)]:
            selected={k:v for k,v in request.items()if k!='sampling'}
            selected.update(options)
            result=await e.finish(await e.call('run_analysis',dict(request=selected)))
            if selected.get('data_type')=='StrehlRatio':
                assert all(0<=v<=1 for row in result['grids'][0]['values']for v in row if v is not None)
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('rmsmap078',work))


@pytest.mark.zemax
def test_rms_map_failure_cancel_recovery():
    async def work(e):
        import time
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        for invalid in [dict(field=999),dict(surface=999)]:
            response=await e.call('run_analysis',dict(request=dict(kind='rms_field_map',**invalid)),okay=False)
            assert response['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=dict(kind='rms_field_map',x_field_sampling=101,y_field_sampling=101,sampling='S_256x256')))
        running=task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+60
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
        (e.folder/'cancellation.json').write_text(json.dumps(dict(started_running=running,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_field_map',x_field_sampling=6,y_field_sampling=8,method='GaussQuad',rings=5))))
        assert result['grids'][0]['nx']==6 and result['grids'][0]['ny']==8
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('rmsmap078_cancel',work))
