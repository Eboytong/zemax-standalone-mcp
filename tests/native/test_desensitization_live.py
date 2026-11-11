import asyncio
import json

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_native_fixed_tolerance_design_optimization_and_mc():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,material_catalogs=['SCHOTT'],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=3,material='N-BK7',is_stop=True,semi_diameter=3,replace_solves=True),
            dict(surface=2,radius=-50,thickness=47,semi_diameter=3,replace_solves=True)]))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='TTHI',param1=2,param2=0,minimum=-.2,maximum=.2)])))
        baseline=await e.call('get_surfaces');tde=await e.call('get_tolerances',dict(request={}))
        merit=await e.call('get_merit_function')
        q=dict(kind='design_desensitize',variables=[dict(surface=1,cell='radius',minimum=45,maximum=100),
            dict(surface=2,cell='radius',minimum=-100,maximum=-45),dict(surface=2,cell='thickness',minimum=40,maximum=90)],
            merit=dict(wizard=dict(kind='sequential',criterion='Wavefront',type='RMS',reference='Centroid',
                use_gaussian_quadrature=True,rings=3,assume_axial_symmetry=False,optimize_for_manufacturing_yield=True,
                manufacturing_yield_weight=1),constraints=[dict(operand='EFFL',target=75,weight=10)]),
            threshold=.002,maximum_nominal=.01,sampling=1,cycles='Fixed_10_Cycles',budget_seconds=600)
        result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=700)
        (e.folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        assert result['summary']['sensitivity_passed'] and result['summary']['nominal_passed'],result['summary']
        assert len(result['rows'])==4
        assert [r['statistics']['requested'] for r in result['rows']]==[64,256,64,256]
        assert result['restoration']['restored']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_tolerances',dict(request={}))==tde
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('d021_desensitization',work))


@pytest.mark.zemax
def test_desensitization_failure_budget_and_cancel_restore_model():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(aperture_value=2, material_catalogs=['SCHOTT'])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=50, thickness=3, material='N-BK7', is_stop=True, replace_solves=True),
            dict(surface=2, radius=-50, thickness=47, replace_solves=True)]))
        await e.call('update_tolerances', dict(request=dict(mode='replace', operands=[
            dict(type='TTHI', param1=2, param2=0, minimum=-.2, maximum=.2)])))
        async def state():
            return [await e.call('get_surfaces'), await e.call('get_merit_function'),
                    await e.call('get_tolerances', dict(request={})),
                    await e.call('get_configurations', dict(request={}))]
        baseline = await state()
        request = dict(kind='design_desensitize', variables=[dict(surface=1, cell='radius', minimum=45, maximum=100)],
            merit=dict(wizard=dict(kind='sequential', criterion='Wavefront', type='RMS',
                reference='Centroid', use_gaussian_quadrature=True, rings=3,
                optimize_for_manufacturing_yield=True, manufacturing_yield_weight=1)),
            threshold=.002, maximum_nominal=.01, sampling=1, screening_samples=5, validation_samples=5)
        async def terminal(task):
            deadline = asyncio.get_running_loop().time() + 120
            while task['state'] not in ('succeeded', 'failed', 'cancelled'):
                assert asyncio.get_running_loop().time() < deadline, task
                await asyncio.sleep(.02)
                task = await e.call('get_task_status', dict(task_id=task['task_id']))
            return task
        budget = await terminal(await e.call('run_analysis', dict(request=request | dict(budget_seconds=.001))))
        assert budget['state'] == 'failed' and budget['error']['code'] == 'BUDGET_EXCEEDED', budget
        assert await state() == baseline
        failed = await terminal(await e.call('run_analysis', dict(request=request | dict(
            variables=[dict(surface=1, cell='radius', minimum=60, maximum=100)]))))
        assert failed['state'] == 'failed' and failed['error']['code'] == 'INVALID_ARGUMENT', failed
        assert await state() == baseline
        task = await e.call('run_analysis', dict(request=request | dict(screening_samples=64, validation_samples=256)))
        deadline = asyncio.get_running_loop().time() + 60
        while task['state'] == 'running' and not task.get('active_step'):
            assert asyncio.get_running_loop().time() < deadline, task
            await asyncio.sleep(.02)
            task = await e.call('get_task_status', dict(task_id=task['task_id']))
        assert task['state'] == 'running' and task['active_step'], task
        await e.call('cancel_task', dict(task_id=task['task_id']))
        task = await terminal(task)
        assert task['state'] == 'cancelled', task
        assert await state() == baseline
        await e.call('get_task_result', dict(task_id=task['task_id']))
    asyncio.run(execute('d021_failure_budget_cancel', work))
