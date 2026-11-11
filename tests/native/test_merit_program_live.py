import asyncio
import json
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_native_merit_preview_apply_reference_and_restore():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5,material_catalogs=['SCHOTT'],
            fields=[dict(x=0,y=0),dict(x=1,y=2)],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=3,material='N-BK7',is_stop=True,replace_solves=True),
            dict(surface=2,radius=-50,thickness=48,replace_solves=True)]))
        before=await e.call('get_merit_function')
        targets=[dict(kind='opd',reference=ref,rings=6,arms=32,hx=.3,hy=.7) for ref in ['chief_ray','mean','mean_remove_tilt']]
        result=await e.finish(await e.call('run_merit_program',dict(request=dict(targets=targets))),timeout_seconds=120)
        assert result['copy_closed'] and not result['applied']
        assert await e.call('get_merit_function')==before
        import numpy as np
        group=result['groups'][0];nodes=group['nodes']
        traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(
            rays=[dict(wavelength=1,hx=.3,hy=.7,px=n['px'],py=n['py']) for n in nodes],
            opd=True))),timeout_seconds=120)
        ray_opd=np.asarray([r['opd'] for r in traced['rows']],dtype=float)
        weights=np.asarray([n['area_weight'] for n in nodes],dtype=float)
        opd_by_reference={}
        for ref in ['chief_ray','mean','mean_remove_tilt']:
            match=next(g for g in result['groups'] if g['request']['reference']==ref)
            native_values=np.asarray([r['value'] for r in result['rows'][match['start']-1:match['start']-1+match['count']]])
            if ref=='chief_ray':independent=ray_opd
            elif ref=='mean':independent=ray_opd-np.average(ray_opd,weights=weights)
            else:
                matrix=np.column_stack((np.ones(len(nodes)),[n['px'] for n in nodes],[n['py'] for n in nodes]))
                beta=np.linalg.lstsq(matrix*np.sqrt(weights[:,None]),ray_opd*np.sqrt(weights),rcond=None)[0]
                independent=ray_opd-matrix@beta
            error=np.abs(native_values-independent)
            assert np.max(error)<=1e-5+.01*max(np.max(np.abs(independent)),1e-12),dict(reference=ref,max_error=float(np.max(error)))
            opd_by_reference[ref]=float(np.max(error))
        (e.folder/'opd-independent-reference.json').write_text(json.dumps(opd_by_reference,indent=2),encoding='utf-8')
        dense=await e.finish(await e.call('run_merit_program',dict(request=dict(targets=[dict(t,rings=12,arms=64) for t in targets]))),timeout_seconds=120)
        for coarse,fine in zip(result['groups'],dense['groups']):
            e.check(coarse['source']+' convergence',coarse['rms_residual_waves'],fine['rms_residual_waves'],atol=1e-5,rtol=.01)
        # The native group reference removes piston; OPDX additionally removes tilt.
        assert result['groups'][2]['rms_residual_waves']<=result['groups'][1]['rms_residual_waves']+1e-8
        applied=await e.finish(await e.call('run_merit_program',dict(request=dict(apply=True,targets=[targets[0]],
            constraints=[dict(operand='CTGT',surface=1,target=5,scale=2,weight=3)]))))
        assert applied['applied'] and applied['constraints'][0]['violation']>0
        assert applied['constraints'][0]['value']==pytest.approx(3)
        current=await e.call('get_merit_function')
        task=await e.call('run_merit_program',dict(request=dict(targets=[dict(kind='opd',wavelength=99)])))
        while task['state'] not in ['succeeded','failed','cancelled']:
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='failed'
        assert await e.call('get_merit_function')==current
        task=await e.call('run_merit_program',dict(request=dict(apply=True,targets=[dict(kind='opd',rings=32,arms=128)])))
        await e.call('cancel_task',dict(task_id=task['task_id']))
        while task['state'] not in ['succeeded','failed','cancelled']:
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled'
        assert await e.call('get_merit_function')==current
    asyncio.run(execute('d020_merit_program',work))
