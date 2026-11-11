import asyncio,json
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_native_pareto_weight_grid_and_reload():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={1:50},thickness=50,semi_diameter=5,replace_solves=True)]))
        await e.call('set_variables',dict(variables=[dict(surface=1,cell='parameter_1',variable=True)]))
        await e.call('update_merit_function',dict(mode='replace',operands=[dict(type='EFFL',target=t,weight=1,parameters={3:1}) for t in [40,60]]))
        source=await e.call('get_surfaces');merit=await e.call('get_merit_function');variables=await e.call('get_variables')
        q=dict(starts=[[dict(surface=1,parameters={1:50})]],optimization=dict(cycles='Fixed_10_Cycles'),evaluation=dict(merit=True),
            pareto=dict(objectives=[dict(operand=1,target=40,scale=20,name='40mm target',maximum_error=12),
                dict(operand=2,target=60,scale=20,name='60mm target')],weight_grid=[[9,1],[1,1],[1,9]]))
        r=await e.finish(await e.call('run_multistart_optimization',dict(request=q)),timeout_seconds=180)
        assert r['summary']['candidate_count']==3 and r['summary']['succeeded']==3
        assert r['summary']['pareto_indices']==[0,1],r['summary']
        for row in r['rows']:
            terminal=await e.call('get_task_status',dict(task_id=row['optimization_task']))
            assert terminal['state']=='succeeded' and terminal['close_attempted']
        assert not r['rows'][2]['feasible'] and r['rows'][2]['constraint_violations'][0]>0
        assert r['restoration']['restored'] and r['summary']['baseline_restored']
        assert await e.call('get_surfaces')==source
        assert (await e.call('get_variables'))['variables']==variables['variables']
        for a,b in zip((await e.call('get_merit_function'))['operands'],merit['operands']):
            assert (a['type'],a['target'],a['weight'])==(b['type'],b['target'],b['weight'])
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=1,count=1));assert len(page['rows'])==1
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'pareto.png'))))
        for row,expected in zip(r['rows'],[42,50,58]):
            for value in row['values']:e.check('known weighted compromise',value,expected,atol=1e-5,rtol=1e-7)
            await e.call('open_lens',dict(path=row['path']))
            m=await e.call('evaluate_merit_function')
            for i,value in enumerate(row['values']):e.check('saved candidate objective',m['operands']['operands'][i]['value'],value)
        (e.folder/'pareto-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        task=await e.call('run_multistart_optimization',dict(request=q))
        await e.call('cancel_task',dict(task_id=task['task_id']))
        for _ in range(1000):
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
            if task['state'] in ['succeeded','failed','cancelled']:break
            await asyncio.sleep(.02)
        assert task['state']=='cancelled'
        cancelled=await e.call('get_task_result',dict(task_id=task['task_id']));assert cancelled['restoration']['restored']
        for settings,code in [(q['pareto']|dict(budget_seconds=1e-9),'BUDGET_EXCEEDED'),
                              (q['pareto']|dict(objectives=[q['pareto']['objectives'][0]|dict(operand=99),q['pareto']['objectives'][1]]),'NO_VALID_CANDIDATE')]:
            failed=await e.call('run_multistart_optimization',dict(request=q|dict(pareto=settings)))
            for _ in range(1000):
                failed=await e.call('get_task_status',dict(task_id=failed['task_id']))
                if failed['state'] in ['succeeded','failed','cancelled']:break
                await asyncio.sleep(.02)
            assert failed['state']=='failed'
            error=await e.call('get_task_result',dict(task_id=failed['task_id']))
            assert error['error']['code']==code and error['restoration']['restored'],error
    asyncio.run(execute('pareto_search',work))
