"""Wavelength endpoints checked against independent pupil rays and scalar RMS."""
import asyncio
import json
import math
from pathlib import Path

import pytest
from support.native import execute


@pytest.mark.zemax
def test_rms_wavelength_endpoint_references():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        source=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=source));await e.call('open_lens',dict(path=source))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        waves=baseline['wavelengths'];endpoints=[min(waves,key=lambda r:r['wavelength_um']),max(waves,key=lambda r:r['wavelength_um'])]
        pupils=[(2*x/127-1,2*y/127-1)for y in range(128)for x in range(128)if (2*x/127-1)**2+(2*y/127-1)**2<=1]
        traced={};records=[]
        for wave in endpoints:
            rays=[dict(px=x,py=y,wavelength=wave['number'])for x,y in [(0,0),*pupils]]
            traced[wave['number']]=[]
            for start in range(0,len(rays),8192):
                result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays[start:start+8192],opd=True))))
                traced[wave['number']].extend(result['rows'])
        for metric in ['SpotRadius','Spot_X','Spot_Y','Wavefront','StrehlRatio']:
            request=dict(kind='rms_vs_wavelength',field=1,data_type=metric,reference='ChiefRay',sampling='S_128x128',wavelength_density=20)
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(result)
            (e.folder/'wavelength-results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            assert result['series'] and result['series'][0]['x_unit']=='micrometers'
            curve=result['series'][0]
            for at,wave in zip([0,-1],endpoints,strict=True):
                e.check('wavelength scan endpoint',curve['x'][at],wave['wavelength_um'],atol=1e-10,rtol=1e-10)
                scalar=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',wavelength=wave['number'],data_type=metric,reference='ChiefRay',sampling='S_128x128'))))
                actual=curve['y'][at][0];reference=scalar['series'][0]['y'][0][0]
                e.check('wavelength vs single-wave RMS '+metric,actual,reference,atol=1e-6,rtol=1e-6)
                if metric=='StrehlRatio':
                    assert all(0<=v<=1 for row in curve['y']for v in row if v is not None)
                    continue
                rows=traced[wave['number']];chief=rows[0];valid=[r for r in rows[1:]if r['state']=='succeeded']
                if metric=='Wavefront':
                    values=[r['opd']for r in valid];mean=sum(values)/len(values)
                    expected=math.sqrt(sum((v-mean)**2 for v in values)/len(values));atol=1e-5
                else:
                    axes=(0,1)if metric=='SpotRadius'else(0,)if metric=='Spot_X'else(1,)
                    expected=1000*math.sqrt(sum(sum((r['position'][a]-chief['position'][a])**2 for a in axes)for r in valid)/len(valid));atol=.05
                e.check('independent wavelength quadrature '+metric,actual,expected,atol=atol,rtol=.01)
            task_id=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=task_id,series=0,start=2,count=3))
            assert page['series'][0]['y']==curve['y'][2:5]
            await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/(metric+'.png')))))
            assert (await e.call('get_task_status',dict(task_id=task_id)))['close_attempted']
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_wavelength',field=0,method='GaussQuad',rings=5,use_polarization=True,show_diffraction_limit=True,use_dashes=True))))
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('rmswave079',work))


@pytest.mark.zemax
def test_rms_wavelength_failure_cancel_recovery():
    async def work(e):
        import time
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        invalid=await e.call('run_analysis',dict(request=dict(kind='rms_vs_wavelength',field=999)),okay=False)
        assert invalid['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=dict(kind='rms_vs_wavelength',sampling='S_1024x1024',wavelength_density=100)))
        running=task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+60
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
        (e.folder/'cancellation.json').write_text(json.dumps(dict(started_running=running,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_wavelength',method='GaussQuad',rings=5))))
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('rmswave079_cancel',work))
