"""Test whether selected-wavelength solve evaluation explains Cooke RMS mismatch."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('fixed',[False,True],ids=['dynamic_radius','fixed_radius'])
def test_quick_yield_selected_wavelength_solve_reference(fixed):
    async def work(e):
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        conditions=dict(hypothesis='QuickYield evaluates selected wavelength as primary, recomputing primary-dependent solves in its analysis model',
            factor='Retain or fix surface6 MarginalRayAngle radius solve at original primary2',
            reference='512 independent equal-area midpoint rays after selecting primary wavelength; source baseline restored between cases',
            tolerance='1e-5waves+1%reference; unchanged',fixed=fixed,
            acceptance='Both selected-wave references must pass; active original-primary error remains recorded separately')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        records=[]
        for wavelength in [1,3]:
            await e.call('open_lens',dict(path=str(sample)))
            original=await e.call('get_surfaces')
            if fixed:
                await e.call('update_surfaces',dict(changes=[dict(surface=6,replace_solves=True,
                    solves=dict(radius=dict(mode='fixed')))]))
            await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
                dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
            before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
            merit=await e.call('get_merit_function');configs=await e.call('get_configurations',dict(request={}))
            async def rms():
                batch=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(opd=True,
                    rays=[dict(hx=0,hy=0,px=0,py=float(np.sqrt((j+.5)/512)),wavelength=wavelength)for j in range(512)]))))
                assert all(not r['error_code']and not r['vignette_code']for r in batch['rows'])
                return float(np.std([r['opd']for r in batch['rows']])),batch
            active,active_batch=await rms()
            q=dict(kind='quick_yield',field=1,wavelength=wavelength,configuration=1,
                pupil_sampling=10,precision='VeryHigh',compensator_strategy='Ignore')
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['close_attempted']and not status.get('cleanup_warnings')
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit and await e.call('get_configurations',dict(request={}))==configs
            await e.call('update_system_settings',dict(settings=dict(primary_wavelength=wavelength)))
            selected_surfaces=await e.call('get_surfaces');selected_settings=await e.call('get_system_settings')
            selected,batch=await rms()
            records.append(dict(wavelength=wavelength,fixed=fixed,request=q,original_model=original,before=before,
                selected_surfaces=selected_surfaces,selected_settings=selected_settings,active_reference=active,
                active_batch=active_batch,selected_reference=selected,selected_batch=batch,result=result,status=status,
                active_error=max(abs(v-active)for v in result['series'][0]['x']),
                selected_error=max(abs(v-selected)for v in result['series'][0]['x'])))
            (e.folder/'solve-reference.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            await e.call('update_system_settings',dict(settings=dict(primary_wavelength=2)))
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        await e.call('disconnect')
        for row in records:
            for value in row['result']['series'][0]['x']:
                e.check('selected wavelength'+str(row['wavelength'])+' recomputed solve reference',value,
                    row['selected_reference'],atol=1e-5,rtol=.01)
    asyncio.run(execute('quickyield570_solve_reference_'+str(fixed),work))
