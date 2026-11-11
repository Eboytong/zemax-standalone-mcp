import asyncio,json,math
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_tolerance_budget_native_cost_and_independent_samples():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={1:50},thickness=50,semi_diameter=5,replace_solves=True)]))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='TTHI',param1=1,param2=0,minimum=-.1,maximum=.1)])))
        baseline_path=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=baseline_path))
        source=await e.call('get_surfaces');tde=await e.call('get_tolerances',dict(request={}));merit=await e.call('get_merit_function')
        q=dict(kind='tolerance_budget',processes=[dict(operand=1,name='image spacing',unit='mm',minimum_half_width=.01,
            maximum_half_width=.2,reference_half_width=.01,variable_cost=100)],allocations=[[.01],[.05],[.2]],currency='CNY',
            costing_unit='piece',criterion_unit='native RMS length',threshold=.001,target_yield=.8,
            screening_samples=32,validation_samples=64,save_validation_samples=2,sampling=1,budget_seconds=180)
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=240)
        (e.folder/'budget-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        assert r['summary']['baseline_restored']
        assert await e.call('get_surfaces')==source
        assert await e.call('get_tolerances',dict(request={}))==tde
        assert (await e.call('get_merit_function'))['operands']==merit['operands']
        for row,cost in zip(r['rows'],[100,20,5]):e.check('known cost',row['cost']['total'],cost)
        e.check('sensitivity analytic defocus',r['sensitivity']['results'][0]['effects'][0]['maximum'],.01/(50*math.sqrt(2)),atol=1e-10,rtol=1e-7)
        assert r['summary']['recommended_index']==1,r['summary']
        assert r['rows'][0]['interval']['passed']==32 and r['rows'][1]['interval']['passed']==32
        assert not r['rows'][2]['feasible']
        validation=r['independent_validation'];assert validation['seed']==314159 and validation['feasible']
        assert len(validation['saved_samples'])==2
        for row in r['rows']:
            native=await e.call('get_task_result',dict(task_id=row['task_id']))
            assert native['summary']['actual']['MonteCarloStatistic']=='Uniform'
            assert native['summary']['random_seed']['tde_seed_operands'][0]['parameters']['1']==42
        await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=1,count=1))
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'cost.png'))))
        await e.call('open_lens',dict(path=r['rows'][1]['path']))
        saved=await e.call('get_tolerances',dict(request={}));assert saved['rows'][1]['minimum']==-.05 and saved['rows'][1]['maximum']==.05
        # Saved Monte Carlo models carry the actual sampled thickness for independent ray-RMS reference.
        trials=await e.call('get_task_result',dict(task_id=validation['task_id'],start=0,count=64))
        for index,path in enumerate(validation['saved_samples']):
            await e.call('open_lens',dict(path=path))
            surface=(await e.call('get_surfaces',dict(start=1,count=1)))['surfaces'][0]
            delta=surface['cells']['thickness']['value']-50
            assert abs(delta)<=.05+1e-10
            actual=trials['rows'][index]['values'][0]
            expected=abs(delta)/(50*math.sqrt(2))
            e.check('saved trial analytic uniform pupil RMS',actual,expected,atol=1e-10,rtol=1e-7)
            radius=math.sqrt(.5)
            rays=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=[dict(px=x,py=y) for x,y in [(radius,0),(-radius,0),(0,radius),(0,-radius)]]))))
            traced=math.sqrt(sum(ray['position'][0]**2+ray['position'][1]**2 for ray in rays['rows'])/4)
            e.check('saved trial independent native rays',traced,expected,atol=1e-10,rtol=1e-7)
        await e.call('open_lens',dict(path=baseline_path))
        for request,state in [(q,'cancelled'),(q|dict(budget_seconds=1e-9),'failed'),
            (q|dict(processes=[q['processes'][0]|dict(operand=99)]),'failed')]:
            task=await e.call('run_analysis',dict(request=request))
            if state=='cancelled':await e.call('cancel_task',dict(task_id=task['task_id']))
            for _ in range(1000):
                task=await e.call('get_task_status',dict(task_id=task['task_id']))
                if task['state'] in ['succeeded','failed','cancelled']:break
                await asyncio.sleep(.02)
            assert task['state']==state,task
            result=await e.call('get_task_result',dict(task_id=task['task_id']))
            assert result['restoration']['restored'] and await e.call('get_tolerances',dict(request={}))==tde
        nofit=await e.finish(await e.call('run_analysis',dict(request=q|dict(threshold=0))),timeout_seconds=180)
        assert nofit['summary']['recommended_index'] is None and nofit['independent_validation'] is None
        compensation=await e.finish(await e.call('run_analysis',dict(request=q|dict(compensation='ParaxialFocus',screening_samples=16,validation_samples=16,target_yield=.7))),timeout_seconds=180)
        assert compensation['summary']['recommended_index']==2
        assert await e.call('get_tolerances',dict(request={}))==tde
        await e.call('new_system')
    asyncio.run(execute('tolerance_budget',work))
