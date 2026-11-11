"""Independent catalog/Fresnel reference and native copied ghost trials."""
import asyncio
import json
import math
from pathlib import Path

import pytest

from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_ghost_plate_fresnel_candidates_and_lifecycle_stdio():
    async def work(e):
        active=False;coefficients=None;internal=None
        catalog=Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF'
        for line in catalog.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            if line.startswith('NM '):active=line.split()[1]=='N-BK7'
            if active and line.startswith('CD '):coefficients=list(map(float,line.split()[1:7]))
            if active and line.startswith('IT ') and float(line.split()[1])==.4:internal=list(map(float,line.split()[1:4]))
        assert coefficients and internal
        wavelength,catalog_transmission,reference_thickness=internal
        thickness=2
        transmission=catalog_transmission**(thickness/reference_thickness)
        n=math.sqrt(1+sum(coefficients[i]*wavelength**2/(wavelength**2-coefficients[i+1]) for i in (0,2,4)))
        reflectance=((n-1)/(n+1))**2
        expected=(1-reflectance)**2*transmission
        ghost=(1-reflectance)**2*reflectance**2*transmission**3
        await setup(e,3)
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=wavelength)])))
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=2,Power=1,ZCosine=1),sources=dict(RandomPolarization=False,Jx=1,Jy=0)),
            dict(object=2,object_type='RectangularVolume',z=5,material='N-BK7',data=dict(X1HalfWidth=10,Y1HalfWidth=10,X2HalfWidth=10,Y2HalfWidth=10,ZLength=thickness)),
            dict(object=3,object_type='DetectorRectangle',z=thickness+10,material='ABSORB',data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=3,NumberYPixels=3))])
        await trace(e,'source_buffers',use_polarization=True,split_rays=True)
        buffer=(await detector(e,3))['total_flux']
        original=await e.call('get_nsc_objects',dict(request={}));revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='ghost_diagnostics',detector=3,rays_per_source=2,
            expected_paths=[[dict(object=2,face=1),dict(object=2,face=2),dict(object=3,face=0)]],
            candidates=[dict(name='higher index',changes=[dict(object=2,material='N-F2')]),
                dict(name='miss detector',changes=[dict(object=3,x=20)]),
                dict(name='invalid coating',changes=[dict(object=2,face=1,coating='D010_MISSING_COATING')]),
                dict(name='ideal front AR',changes=[dict(object=2,face=1,coating='I.99999999')])])
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        base=r['candidates'][0]
        for name,actual,reference in [('main',base['power']['expected'],expected),('two reflection ghost',base['power']['ghost'],ghost)]:
            e.check(name,actual,reference,atol=1e-8,rtol=1e-6)
        e.check('independent detector sum',base['power']['detector'],expected+ghost,atol=1e-8,rtol=1e-6)
        e.check('native ZRD scalar precision',base['power']['read_arrivals'],base['power']['detector'],atol=1e-8,rtol=1e-6)
        assert next(p for p in base['paths'] if p['category']=='ghost')['reflection_faces']==[dict(object=2,face=2),dict(object=2,face=1)]
        assert r['candidates'][1]['actual_changes'][0]['values']['material']=='N-F2'
        assert not r['candidates'][2]['eligible']
        assert r['candidates'][3]['state']=='failed' and r['candidates'][3]['error']['code']=='INVALID_RESOURCE'
        assert r['resources']['all_copies_closed'] and not r['resources']['cleanup_errors']
        coated=r['candidates'][4]
        assert coated['state']=='succeeded' and coated['eligible']
        assert coated['actual_changes'][0]['values']['coating']=='I.99999999'
        e.check('front ideal high-transmission coating main',coated['power']['expected'],.99999999*(1-reflectance)*transmission,atol=1e-8,rtol=1e-6)
        e.check('front ideal high-transmission coating ghost',coated['power']['ghost'],0,atol=1e-8,rtol=1e-6)
        assert r['summary']['best_candidate']==4
        assert await e.call('get_nsc_objects',dict(request={}))==original
        assert (await e.call('get_status'))['model_revision']==revision
        e.check('source detector buffer preserved',(await detector(e,3))['total_flux'],buffer,atol=1e-12)
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=1,count=1));assert len(page['rows'])==1
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'ghost-powers.png'))))
        path=await e.finish(await e.call('run_analysis',dict(request=dict(kind='path_analysis',path=base['zrd']))))
        for arrival in base['paths']:
            native=[p for p in path['rows'] if p['last_object']==3 and p['hits']==len(arrival['sequence'])+1]
            assert native,path
            e.check('native PathAnalysis arrival',sum(p['flux_out_w'] for p in native),arrival['power'],atol=1e-8,rtol=1e-6)
        for option in [dict(max_paths=1),dict(minimum_relative_power=.01),dict(max_segments=3),dict(filter='H3')]:
            limited=await e.finish(await e.call('run_analysis',dict(request=q|dict(candidates=[])|option)))
            p=limited['candidates'][0]['power']
            e.check('accounted retained plus unclassified',p['retained']+p['unclassified'],p['detector'],atol=1e-12)
            if 'max_paths' in option or 'minimum_relative_power' in option:assert p['excluded']>0
            if 'max_segments' in option:assert p['unclassified']>0
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        await e.call('open_lens',dict(path=r['summary']['best_model']))
        replay=await e.finish(await e.call('run_analysis',dict(request=q|dict(candidates=[]))))
        e.check('saved model main power',replay['candidates'][0]['power']['expected'],.99999999*(1-reflectance)*transmission,atol=1e-8,rtol=1e-6)
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        for request,terminal in [(q|dict(detector=99,expected_paths=[[dict(object=99)]],candidates=[]),'failed'),(q,'cancelled')]:
            current=await e.call('get_nsc_objects',dict(request={}))
            t=await e.call('run_analysis',dict(request=request))
            if terminal=='cancelled':await e.call('cancel_task',dict(task_id=t['task_id']))
            for _ in range(1000):
                t=await e.call('get_task_status',dict(task_id=t['task_id']))
                if t['state'] in ('failed','cancelled','succeeded'):break
                await asyncio.sleep(.02)
            assert t['state']==terminal,t
            result=await e.call('get_task_result',dict(task_id=t['task_id']))
            assert result['resources']['all_copies_closed'] and not result['resources']['cleanup_errors']
            assert await e.call('get_nsc_objects',dict(request={}))==current
        # Source buffers and source revision were unchanged by the original candidate run.
        # Save/reload intentionally changes revision; test that invariant before reloading below.
        (e.folder/'fresnel-reference.json').write_text(json.dumps(dict(catalog=str(catalog),wavelength_um=wavelength,
            n=n,reflectance=reflectance,internal_transmission=transmission,thickness=thickness,
            expected=expected,ghost=ghost,source_revision=revision,source_detector_power=buffer),indent=2),encoding='utf-8')
    asyncio.run(execute('ghost_diagnostics_native',work))
