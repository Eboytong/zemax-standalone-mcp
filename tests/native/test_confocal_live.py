"""Point-fluorescence two-path PSFs with independent Fresnel quadrature."""
import asyncio
import json

import pytest

from tests.support.native import execute
from tests.support.confocal_reference import response,fwhm


@pytest.mark.zemax
def test_confocal_two_paths_pinhole_and_reference_stdio():
    async def work(e):
        paths=[]
        for finite in [False,True]:
            await e.call('new_system')
            await e.call('update_system_settings',dict(settings=dict(aperture_value=2,wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.6)])))
            changes=([dict(surface=0,thickness=100,replace_solves=True)] if finite else [])
            changes.append(dict(surface=1,surface_type='Paraxial',parameters={1:50},thickness=100 if finite else 50,semi_diameter=2,replace_solves=True))
            await e.call('update_surfaces',dict(changes=changes))
            path=e.folder/('detection.zos' if finite else 'illumination.zos');paths.append(str(path))
            await e.call('save_lens_as',dict(path=str(path)))
        source=await e.call('get_surfaces');settings=await e.call('get_system_settings');revision=(await e.call('get_status'))['model_revision']
        diameters=[4,60]
        q=dict(kind='confocal_response',illumination=dict(model=paths[0]),detection=dict(model=paths[1]),detection_magnification=-1,
            offsets_mm=[i/4 for i in range(-8,9)],pinhole_diameters_um=diameters,pupil_sampling='S_512x512',
            image_sampling='S_128x128',image_delta_um=4,window_check=True,budget_seconds=600)
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=650)
        independent=response(r,diameters);x=r['series'][0]['x']
        for j,curve in enumerate(r['summary']['curves']):
            e.check('independent confocal normalized response',max(abs(a-b) for a,b in zip(curve['relative'],independent[j])),0,atol=.005,rtol=0)
            reference_width=fwhm(x,independent[j])
            e.check('independent confocal FWHM',curve['width']['fwhm_mm']/reference_width,1,atol=.01,rtol=0)
            coarse=fwhm(x[::2],curve['relative'][::2])
            e.check('axial sampling FWHM convergence',coarse/curve['width']['fwhm_mm'],1,atol=.01,rtol=0)
            assert curve['window_check']['state']=='converged',curve['window_check']
        fine_reference=response(r,diameters,quadrature=256)
        for a,b in zip(independent,fine_reference):e.check('independent pupil quadrature convergence',max(abs(v-w) for v,w in zip(a,b)),0,atol=.002,rtol=0)
        for c in r['cases']:
            p=c['paths'][1]
            assert p['primary']['pinholes'][0]['fraction']<p['primary']['pinholes'][1]['fraction']
            z=c['offset_mm'];distance=100-z
            import math
            e.check('native isotropic collection cone',p['collection']['isotropic_fraction'],(1-distance/math.sqrt(distance*distance+1))/2,atol=1e-12)
        assert r['resources']['all_copies_closed'] and not r['resources']['cleanup_errors']
        assert await e.call('get_surfaces')==source and await e.call('get_system_settings')==settings
        assert (await e.call('get_status'))['model_revision']==revision
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=3,count=5));assert len(page['rows'])==5
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'confocal.png'))))
        # Alternate emission wavelength and explicitly incomplete scan range.
        small=q|dict(offsets_mm=[-.1,-.05,0,.05,.1],detection=dict(model=paths[1],wavelength=2),pupil_sampling='S_128x128',window_check=False)
        alternate=await e.finish(await e.call('run_analysis',dict(request=small)),timeout_seconds=180)
        assert alternate['models'][1]['wavelength_um']==.6
        assert alternate['summary']['curves'][0]['width']['state']=='range_incomplete'
        for request,state in [(small|dict(detection_magnification=-2),'failed'),(q,'cancelled'),(small|dict(budget_seconds=.0001),'failed')]:
            t=await e.call('run_analysis',dict(request=request))
            if state=='cancelled':await e.call('cancel_task',dict(task_id=t['task_id']))
            for _ in range(1000):
                t=await e.call('get_task_status',dict(task_id=t['task_id']))
                if t['state'] in ('succeeded','failed','cancelled'):break
                await asyncio.sleep(.02)
            assert t['state']==state,t
            result=await e.call('get_task_result',dict(task_id=t['task_id']))
            assert result['resources']['all_copies_closed'] and not result['resources']['cleanup_errors']
        assert await e.call('get_surfaces')==source
        await e.finish(await e.call('run_analysis',dict(request=small)),timeout_seconds=180)
        (e.folder/'independent-response.json').write_text(json.dumps(dict(offsets_mm=x,pinhole_diameters_um=diameters,response=independent,quadrature=192,finer_response=fine_reference),indent=2),encoding='utf-8')
    asyncio.run(execute('confocal_native',work))
