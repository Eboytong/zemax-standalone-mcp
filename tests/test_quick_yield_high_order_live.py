"""Separate high-order fitted-wavefront effects from Cooke model complexity."""
import asyncio
import json

import numpy as np
import pytest

from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('powers',[(6,8),(10,12)],ids=['orders6_8','orders10_12'])
def test_quick_yield_high_order_fit_diagnostic(powers):
    async def work(e):
        conditions=dict(hypothesis='QuickYield fitted-wavefront approximation causes order-dependent zero-perturbation RMS error',
            input_source='Owned on-axis EvenAspheric mirror R-200mm conic-1, image-100mm, pupil5mm,lambda.55um',
            cases=[dict(power=p,parameter=p//2,coefficient=.0003125/(5**p))for p in powers],
            discriminant='Compare Standard versus VeryHigh and radial uniform-area batch OPD RMS for equal edge sag. An order-dependent residual supports fit truncation; matching both excludes this controlled explanation.',
            reference='256 radial midpoint nodes r=sqrt((j+.5)/256) on rotational pupil; population OPD RMS after piston subtraction',
            tolerance='1e-5 waves +1%*reference; unchanged',completion='Diagnostic only; Cooke acceptance remains separate')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
            dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
        records=[]
        for case in conditions['cases']:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',
                radius=-200,conic=-1,material='MIRROR',thickness=-100,semi_diameter=5,
                is_stop=True,parameters={str(p):0. for p in range(3,7)}|{str(case['parameter']):case['coefficient']},replace_solves=True)]))
            snapshots={name:await e.call(name,args)for name,args in [
                ('get_surfaces',{}),('get_system_settings',{}),('get_merit_function',{}),
                ('get_configurations',dict(request={})),('get_tolerances',dict(request={}))]}
            batch=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(opd=True,
                rays=[dict(hx=0,hy=0,px=0,py=float(np.sqrt((j+.5)/256)),wavelength=1)for j in range(256)]))))
            assert len(batch['rows'])==256 and all(not r['error_code']and not r['vignette_code']for r in batch['rows'])
            wave=np.asarray([r['opd']for r in batch['rows']]);expected=float(wave.std())
            reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',
                wavelength=1,data_type='Wavefront',reference='ChiefRay',method='GaussQuad',rings=10,field_density=5))))
            gauss=reference['series'][0]['y'][0][0]
            record=dict(case=case,batch_reference_rms=expected,batch=batch,gauss_quad=reference,results=[])
            records.append(record)
            for precision in ['Standard','VeryHigh']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='quick_yield',wavelength=1,
                    field=1,configuration=1,pupil_sampling=10,precision=precision,compensator_strategy='Ignore'))))
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded'and task['close_attempted']and not task.get('cleanup_warnings')
                error=max(abs(v-expected)for v in result['series'][0]['x'])
                record['results'].append(dict(precision=precision,result=result,task=task,
                    maximum_error=error,tolerance=1e-5+.01*abs(expected),numerically_passed=error<=1e-5+.01*abs(expected)))
                (e.folder/'high-order.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            for name,before in snapshots.items():
                assert await e.call(name,dict(request={})if name in {'get_configurations','get_tolerances'}else{})==before
            e.check('r'+str(case['power'])+' independent radial RMS versus GaussQuad',gauss,expected,atol=1e-5,rtol=.01)
        await e.call('disconnect')
    asyncio.run(execute('quickyield549_high_order_'+'_'.join(map(str,powers)),work))
