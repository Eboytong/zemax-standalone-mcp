"""Discriminate selected wavelength and multi-wavelength fit effects in Cooke."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from support.native import execute


@pytest.mark.zemax
def test_quick_yield_cooke_wavelength_identity_diagnostic():
    async def work(e):
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        conditions=dict(hypotheses=[
            'A selected-wavelength identity/scaling difference varies with wavelength number',
            'An implicit multi-wavelength fit changes when the same selected wavelength is the sole wavelength',
            'An unchanged residual across table layouts excludes that controlled table-identity explanation'],
            input_source=str(sample),reference='512 radial equal-area midpoint OPD samples at on-axis rotational pupil; piston removed',
            tolerance='1e-5 waves +1%*reference; unchanged',precision='VeryHigh')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('open_lens',dict(path=str(sample)))
        original=(await e.call('get_system_settings'))['wavelengths']
        records=[]
        for layout in ['original','monochromatic']:
            for selected,wave in enumerate(original,1):
                await e.call('open_lens',dict(path=str(sample)))
                if layout=='monochromatic':
                    await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=wave['wavelength_um'])])))
                number=selected if layout=='original'else 1
                await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
                    dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)])))
                before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
                configs=await e.call('get_configurations',dict(request={}));merit=await e.call('get_merit_function')
                batch=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(opd=True,
                    rays=[dict(hx=0,hy=0,px=0,py=float(np.sqrt((j+.5)/512)),wavelength=number)for j in range(512)]))))
                assert all(not r['error_code']and not r['vignette_code']for r in batch['rows'])
                expected=float(np.std([r['opd']for r in batch['rows']]))
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='quick_yield',field=1,
                    wavelength=number,configuration=1,pupil_sampling=10,precision='VeryHigh',compensator_strategy='Ignore'))))
                status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert status['state']=='succeeded'and status['close_attempted']and not status.get('cleanup_warnings')
                error=max(abs(v-expected)for v in result['series'][0]['x'])
                records.append(dict(layout=layout,selected_original_number=selected,request_wavelength=number,
                    wavelength_um=wave['wavelength_um'],batch=batch,reference_rms=expected,result=result,status=status,
                    maximum_error=error,tolerance=1e-5+.01*expected,numerically_passed=error<=1e-5+.01*expected))
                (e.folder/'wavelength-identity.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
                assert await e.call('get_configurations',dict(request={}))==configs and await e.call('get_merit_function')==merit
        await e.call('disconnect')
    asyncio.run(execute('quickyield569_wavelength_identity',work))
