"""SagTable rotational-section assumptions and explicit decentered aperture identity."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_sag_table_rejects_anisotropic_biconic_and_reuses_session():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            model='Biconic Rx100/Ry50mm then Rx=Ry50mm, conics0,semi5mm',
            requirement='SagTable positive-Y section assumes rotational symmetry',
            reference='Analytic biconic sag along axes; sphere sag after equalizing radii',
            row_atol=1e-8,row_rtol=1e-6),indent=2),encoding='utf-8')
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Biconic',radius=50,
            parameters={'1':100,'2':0},semi_diameter=5,replace_solves=True)]))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        task=await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1)))
        for _ in range(500):
            if task['state']in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='failed'and task['error']['code']=='UNSUPPORTED_MODEL',task
        failure=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={'1':50})]))
        sphere=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,samples=11))))
        assert sphere['rotational_symmetry_check']['state']=='sampled_meridians_agree'
        assert len(sphere['rotational_symmetry_check']['samples'])==24
        (e.folder/'applicability.json').write_text(json.dumps(dict(failed_task=task,failure=failure,
            symmetric_result=sphere),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        for row in sphere['rows']:
            y=row['y'];e.check('equal-radii biconic sphere sag',row['sag'],y*y/(50+math.sqrt(2500-y*y)),atol=1e-8,rtol=1e-6)
    asyncio.run(execute('sag553_biconic_applicability',work))


@pytest.mark.zemax
def test_sag_table_offset_aperture_is_not_manufacturing_area_mask():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            model='Parabola z=y^2/80,semi5mm; clear circular aperture radius2mm decenteredX1mm',
            reference='SagTable evaluates full0..5mm radial blank; direct rays independently demonstrate clipping',
            row_atol=1e-8,row_rtol=1e-6),indent=2),encoding='utf-8')
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=1),
            dict(surface=1,surface_type='EvenAspheric',radius=40,conic=-1,
                semi_diameter=5,thickness=10,replace_solves=True)]))
        q=dict(kind='sag_table',surface=1,samples=11)
        baseline=await e.finish(await e.call('run_analysis',dict(request=q)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(
            type='CircularAperture',maximum_radius=2,x_decenter=1))]))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        clipped=await e.finish(await e.call('run_analysis',dict(request=q)))
        a=clipped['actual_settings']['aperture']
        assert a['type']=='CircularAperture'and a['maximum_radius']==2 and a['x_decenter']==1
        assert clipped['actual_settings']['effective_radius_range']==[0,5]
        assert clipped['summary']==baseline['summary']
        assert clipped['slope_query_copy']['closed']and clipped['slope_query_copy']['copy_aperture']=='None'
        for row,base in zip(clipped['rows'],baseline['rows'],strict=True):
            assert row['slope_source']=='native_SSLP_unclipped_copy'
            for key in ['sag','slope','slope_difference','removal_depth']:
                e.check('aperture-independent '+key,row[key],base[key],atol=1e-8,rtol=1e-6)
            if row['y']>=2:assert row['active_model_native_slope']==0
        traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',
            start_surface=0,target_surface=1,rays=[dict(x=0,y=y,z=0,l=0,m=0,n=1)for y in [0,3]]))))
        assert [r['error_code']for r in traced['rows']]==[0,0]
        assert [r['vignette_code']==0 for r in traced['rows']]==[True,False]
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        path=str(e.folder/'offset-aperture.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert reloaded['actual_settings']['aperture']==a and reloaded['slope_query_copy']['closed']
        for row,old in zip(reloaded['rows'],clipped['rows'],strict=True):
            for key in ['sag','slope','slope_difference','removal_depth']:
                e.check('reloaded '+key,row[key],old[key],atol=1e-8,rtol=1e-6)
        (e.folder/'aperture.json').write_text(json.dumps(dict(unclipped=baseline,clipped=clipped,
            trace=traced,reloaded=reloaded),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        for row in clipped['rows']:
            e.check('full blank sag through clipped region',row['sag'],row['y']**2/80,atol=1e-8,rtol=1e-6)
            e.check('full blank slope through clipped region',row['slope'],row['y']/40,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('sag553_offset_aperture',work))


@pytest.mark.zemax
def test_sag_table_cancel_closes_active_unclipped_copy_and_reuses_session():
    import time
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',
            radius=40,conic=-1,semi_diameter=5,thickness=10,replace_solves=True,
            aperture=dict(type='CircularAperture',maximum_radius=2,x_decenter=1))]))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function');configs=await e.call('get_configurations',dict(request={}))
        task=await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,samples=10001)))
        deadline=time.monotonic()+60
        while task.get('phase')!='sampling_rows':
            assert time.monotonic()<deadline and task['state']=='running',task
            await asyncio.sleep(.02)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        result=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert task['state']=='cancelled'and result['slope_query_copy']['closed'],result
        assert result['slope_query_copy']['copy_aperture']=='None'
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        assert await e.call('get_configurations',dict(request={}))==configs
        rerun=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,samples=11))))
        assert rerun['slope_query_copy']['closed']
        (e.folder/'cancel-copy.json').write_text(json.dumps(dict(task=task,result=result,rerun=rerun),
            ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        for row in rerun['rows']:e.check('reuse unclipped slope',row['slope'],row['y']/40,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('sag558_cancel_copy',work))
