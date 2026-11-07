"""Separate refractive wavefront fitting from multiple-element Cooke behavior."""
import asyncio
import json

import numpy as np
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('angle',[3,6])
def test_quick_yield_refractive_fit_diagnostic(angle):
    async def work(e):
        conditions=dict(hypothesis='A simple refractor distinguishes generic refractive fitting from Cooke multi-element residuals',
            model=f'N-BK7 plano-convex R50mm,thickness5mm,clear semi6mm,entrance pupil10mm;fields0/{angle}degrees;lambda.55um',
            input_source='Owned model with installed SCHOTT catalog; native RMSWavefront quick focus establishes baseline',
            reference='64 equal-area radial midpoint rings by64 azimuths, independently traced OPD population RMS after piston subtraction',
            secondary_diagnostic='Least-squares linear pupil tilt removed; raw-piston reference retained separately',
            tilt_hypothesis='568 observed equivalence;572 repeats3degree and independently tests6degree against the unchanged tolerance',
            tolerance='1e-5 waves +1%*reference; unchanged',
            discriminant='Compare Standard/VeryHigh against batch and GaussQuad10 at both fields. Passing simple refractor separates the retained Cooke failure from refraction alone.')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],
            aperture_value=10,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0),dict(x=0,y=angle)])))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius=50,thickness=5,material='N-BK7',semi_diameter=6,is_stop=True,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=95,material='',semi_diameter=10,replace_solves=True),
            dict(surface=3,semi_diameter=30,replace_solves=True)]))
        focus=await e.finish(await e.call('run_quick_focus',dict(criterion='RMSWavefront',use_centroid=False,replace_solve=True)))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
            dict(type='TTHI',param1=2,param2=0,minimum=0,maximum=0)])))
        snapshots={name:await e.call(name,args)for name,args in [
            ('get_surfaces',{}),('get_system_settings',{}),('get_merit_function',{}),
            ('get_configurations',dict(request={})),('get_tolerances',dict(request={}))]}
        reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',
            wavelength=1,data_type='Wavefront',reference='ChiefRay',method='GaussQuad',rings=10,field_density=5))))
        rings=64;angles=64
        nodes=[(float(np.sqrt((j+.5)/rings)*np.cos(2*np.pi*k/angles)),
                float(np.sqrt((j+.5)/rings)*np.sin(2*np.pi*k/angles)))for j in range(rings)for k in range(angles)]
        records=[]
        for field,hy in [(1,0),(2,1)]:
            batch=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(opd=True,
                rays=[dict(hx=0,hy=hy,px=x,py=y,wavelength=1)for x,y in nodes]))))
            assert len(batch['rows'])==len(nodes)and all(not r['error_code']and not r['vignette_code']for r in batch['rows'])
            wave=np.asarray([r['opd']for r in batch['rows']]);expected=float(wave.std())
            design=np.column_stack((np.ones(len(nodes)),np.asarray(nodes)))
            coefficients=np.linalg.lstsq(design,wave,rcond=None)[0]
            residual=wave-design@coefficients
            gauss=reference['series'][0]['y'][0 if field==1 else -1][0]
            record=dict(field=field,normalized_field_y=hy,batch_reference_rms=expected,
                gauss_quad_rms=gauss,tilt_removed_rms=float(residual.std()),piston_tilt_coefficients=coefficients.tolist(),batch=batch,results=[])
            records.append(record)
            for precision in ['Standard','VeryHigh']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='quick_yield',wavelength=1,
                    field=field,configuration=1,pupil_sampling=10,precision=precision,compensator_strategy='Ignore'))))
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded'and task['close_attempted']and not task.get('cleanup_warnings')
                error=max(abs(v-expected)for v in result['series'][0]['x'])
                record['results'].append(dict(precision=precision,result=result,task=task,maximum_error=error,
                    tolerance=1e-5+.01*abs(expected),numerically_passed=error<=1e-5+.01*abs(expected),
                    tilt_removed_error=max(abs(v-record['tilt_removed_rms'])for v in result['series'][0]['x'])))
                (e.folder/'refractive.json').write_text(json.dumps(dict(conditions=conditions,focus=focus,
                    reference=reference,records=records),ensure_ascii=False,indent=2),encoding='utf-8')
            for name,before in snapshots.items():
                assert await e.call(name,dict(request={})if name in {'get_configurations','get_tolerances'}else{})==before
        await e.call('disconnect')
        for record in records:e.check('field'+str(record['field'])+' uniform-area batch versus GaussQuad',
            record['gauss_quad_rms'],record['batch_reference_rms'],atol=1e-5,rtol=.01)
        for record in records:
            for result in record['results']:
                for value in result['result']['series'][0]['x']:
                    e.check('field'+str(record['field'])+' '+result['precision']+' piston/tilt removed RMS',
                        value,record['tilt_removed_rms'],atol=1e-5,rtol=.01)
    asyncio.run(execute('quickyield572_refractive_'+str(angle),work))
