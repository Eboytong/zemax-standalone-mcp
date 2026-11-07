import asyncio
import json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_quick_yield_controlled_native():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='SEED',param1=42),dict(type='TTHI',param1=1,param2=0,minimum=-.01,maximum=.01)])))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        q=dict(kind='quick_yield',monte_carlo_samples=1000,compensator_strategy='Ignore',configuration=1)
        result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        (e.folder/'quick-yield.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        assert result.get('series') or result.get('grids') or result.get('native_preamble')
        task=result['task']['task_id'];status=await e.call('get_task_status',dict(task_id=task))
        assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('quickyield083',work))


@pytest.mark.zemax
def test_quick_yield_zero_perturbation_rms_reference():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        source_primary=next(w['number']for w in baseline['wavelengths']if w['primary'])
        # Match the controlled selected-wavelength solve reference established570/571.
        await e.call('update_system_settings',dict(settings=dict(primary_wavelength=1)))
        reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',wavelength=1,data_type='Wavefront',reference='Centroid',method='GaussQuad',rings=3,field_density=5))))
        await e.call('update_system_settings',dict(settings=dict(primary_wavelength=source_primary)))
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='quick_yield',configuration=1,compensator_strategy='Ignore'))),timeout_seconds=180)
        (e.folder/'reference.json').write_text(json.dumps(dict(reference=reference,result=result,
            reference_conditions='selected wavelength1 evaluated as primary for primary-dependent solves; original source primary restored before QuickYield'),ensure_ascii=False,indent=2),encoding='utf-8')
        expected=reference['series'][0]['y'][0][0]
        curve=result['series'][0]
        for value in curve['x']:e.check('zero perturbation RMS waves',value,expected,atol=1e-5,rtol=.01)
        assert len(curve['x'])==99
        assert [row[0]for row in curve['y']]==list(range(1,100))
        task=result['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=task,series=0,start=3,count=5))
        assert page['series'][0]['x']==curve['x'][3:8]
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'yield.png'))))
        assert (await e.call('get_task_status',dict(task_id=task)))['close_attempted']
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('quickyield084zero',work))


@pytest.mark.zemax
def test_quick_yield_reference_characterization():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
        quick=await e.finish(await e.call('run_analysis',dict(request=dict(kind='quick_yield',configuration=1,compensator_strategy='Ignore'))))
        rows=[]
        for wave in [1,2,3]:
            for ref in ['Centroid','ChiefRay']:
                for rings in [3,5,10]:
                    r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',wavelength=wave,data_type='Wavefront',reference=ref,method='GaussQuad',rings=rings,field_density=5))))
                    rows.append(dict(wavelength=wave,reference=ref,rings=rings,value=r['series'][0]['y'][0][0],settings=r['task']['settings']))
                    (e.folder/'characterization.json').write_text(json.dumps(dict(quick=quick,references=rows),ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('quickyield086_reference',work))


@pytest.mark.zemax
def test_quick_yield_controlled_mirror_reference_diagnostic():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
            dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
        records=[]
        for name,conic,thickness in [('parabola',-1,-100),('defocus',-1,-100.02),('sphere',0,-100)]:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,
                conic=conic,material='MIRROR',thickness=thickness,semi_diameter=5,
                is_stop=True,replace_solves=True)]))
            baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
            reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',
                wavelength=1,data_type='Wavefront',reference='ChiefRay',method='GaussQuad',rings=10,field_density=5))))
            expected=reference['series'][0]['y'][0][0]
            if name=='parabola':e.check('parabola exact on-axis wavefront waves',expected,0,atol=1e-5,rtol=0)
            for precision in ['Standard','VeryHigh']:
                q=dict(kind='quick_yield',wavelength=1,field=1,configuration=1,
                       pupil_sampling=10,precision=precision,compensator_strategy='Ignore')
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded' and task['close_attempted'] and not task.get('cleanup_warnings')
                values=result['series'][0]['x'];error=max(abs(v-expected) for v in values)
                records.append(dict(case=name,conic=conic,thickness=thickness,request=q,
                    reference=reference,result=result,reference_value=expected,maximum_error=error,
                    tolerance=1e-5+.01*abs(expected),reference_passed=error<=1e-5+.01*abs(expected),task=task))
                (e.folder/'controlled-mirror.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute('quickyield493_mirror',work))


@pytest.mark.zemax
def test_quick_yield_cooke_sampling_fit_diagnostic():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
            dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',
            wavelength=1,data_type='Wavefront',reference='ChiefRay',method='GaussQuad',rings=10,field_density=5))))
        expected=reference['series'][0]['y'][0][0];records=[]
        for sampling in [3,5,10]:
            for precision in ['Standard','VeryHigh']:
                q=dict(kind='quick_yield',wavelength=1,field=1,configuration=1,
                    pupil_sampling=sampling,precision=precision,compensator_strategy='Ignore')
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded' and task['close_attempted']
                error=max(abs(v-expected) for v in result['series'][0]['x'])
                records.append(dict(request=q,reference=reference,reference_value=expected,
                    result=result,error=error,tolerance=1e-5+.01*abs(expected),
                    passed=error<=1e-5+.01*abs(expected),task=task))
                (e.folder/'sampling-fit.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute('quickyield494_sampling',work))


@pytest.mark.zemax
def test_quick_yield_uniform_defocus_quantiles():
    """A monotone single thickness perturbation gives an independent uniform CDF."""
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        async def image_thickness(value):
            await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,
                conic=-1,material='MIRROR',thickness=value,semi_diameter=5,is_stop=True,replace_solves=True)]))
        await image_thickness(-100.02)
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
            dict(type='SEED',param1=42),dict(type='TTHI',param1=1,param2=0,minimum=-.002,maximum=.002)])))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        editors={name:await e.call(name,dict(request={}) if name!='get_merit_function' else {})
                 for name in ['get_tolerances','get_configurations','get_merit_function']}
        q=dict(kind='quick_yield',wavelength=1,field=1,configuration=1,pupil_sampling=10,
               precision='VeryHigh',statistic='Uniform',monte_carlo_samples=10000,compensator_strategy='Ignore')
        result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        assert result['evaluation']['unit']=='waves'
        assert result['series'][0]['x_unit']=='waves' and result['series'][0]['value_units']==['percent']
        task=result['task']['task_id'];status=await e.call('get_task_status',dict(task_id=task))
        assert status['close_attempted'] and not status.get('cleanup_warnings')
        page=await e.call('get_task_result',dict(task_id=task,series=0,start=3,count=5))
        assert page['series'][0]['x']==result['series'][0]['x'][3:8]
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'uniform-defocus.png'))))
        cancelled=await e.call('run_analysis',dict(request=q|dict(monte_carlo_samples=100000)))
        cancelled=await e.call('cancel_task',dict(task_id=cancelled['task_id']))
        for _ in range(1500):
            if cancelled['state'] in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02)
            cancelled=await e.call('get_task_status',dict(task_id=cancelled['task_id']))
        assert cancelled['state']=='cancelled',cancelled
        assert cancelled['close_attempted'] and not cancelled.get('cleanup_warnings')
        cancelled_result=await e.call('get_task_result',dict(task_id=cancelled['task_id']))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        for name,expected in editors.items():
            assert await e.call(name,dict(request={}) if name!='get_merit_function' else {})==expected
        records=[];failures=[]
        for percentile in [1,25,50,75,99]:
            # RMS increases with |defocus|; uniform thickness maps to reversed ordering.
            thickness=-100.02+.002-.004*percentile/100
            await image_thickness(thickness)
            reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='rms_vs_field',
                wavelength=1,data_type='Wavefront',reference='ChiefRay',method='GaussQuad',rings=10,field_density=5))))
            expected=reference['series'][0]['y'][0][0]
            actual=result['series'][0]['x'][percentile-1]
            records.append(dict(percentile=percentile,thickness=thickness,native=actual,
                                reference_value=expected,reference=reference,error=abs(actual-expected)))
            try:e.check('uniform defocus p'+str(percentile),actual,expected,atol=1e-5,rtol=.01)
            except AssertionError:failures.append(e.checks[-1])
        await image_thickness(-100.02)
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        await e.call('save_lens_as',dict(path=str(e.folder/'reload.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'reload.zos')))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        for name,expected in editors.items():
            assert await e.call(name,dict(request={}) if name!='get_merit_function' else {})==expected
        reuse=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        for comparison in records:
            i=comparison['percentile']-1
            # A fresh Monte Carlo draw is checked against the same analytical CDF.
            # The TDE SEED operand does not establish QuickYield draw repeatability.
            actual=reuse['series'][0]['x'][i];comparison['reloaded_native']=actual
            try:e.check('reloaded uniform p'+str(i+1),actual,comparison['reference_value'],atol=1e-5,rtol=.01)
            except AssertionError:failures.append(e.checks[-1])
        (e.folder/'uniform-defocus.json').write_text(json.dumps(dict(request=q,result=result,
            cancelled=cancelled,cancelled_result=cancelled_result,
            reloaded_result=reuse,editors=editors,
            comparisons=records,tolerance='1e-5 waves + 1% reference'),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('quickyield502_uniform',work))
