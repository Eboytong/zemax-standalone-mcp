import asyncio,json,math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_dual_fsm_native_calibration_and_closed_loop():
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1,count=7))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2)))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,thickness=10,semi_diameter=10,replace_solves=True),
            dict(surface=2,surface_type='CoordinateBreak',thickness=0,replace_solves=True),
            dict(surface=3,material='MIRROR',thickness=0,semi_diameter=10,replace_solves=True),
            dict(surface=4,surface_type='CoordinateBreak',parameters={6:1},thickness=-50,replace_solves=True),
            dict(surface=5,surface_type='CoordinateBreak',thickness=0,replace_solves=True),
            dict(surface=6,material='MIRROR',thickness=0,semi_diameter=10,replace_solves=True),
            dict(surface=7,surface_type='CoordinateBreak',parameters={6:1},thickness=50,replace_solves=True),
            dict(surface=8,thickness=50,semi_diameter=10,replace_solves=True)]))
        source=await e.call('get_surfaces');revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='fsm_control',start_surface=1,mirrors=[dict(tilt_surface=2,mirror_surface=3,return_surface=4),
            dict(tilt_surface=5,mirror_surface=6,return_surface=7)],observation_surfaces=[8,9],
            disturbances=[[.01,-.005,.0001,-.00005]]*20,sample_period_seconds=.001,gain=.5,
            residual_tolerance=1e-6,validation_tolerance=1e-6)
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=240)
        assert r['resources']['copy_closed'] and r['summary']['converged']
        assert r['summary']['native_validation_passed']
        rad=math.pi/180
        expected=[[0,-200*rad,0,100*rad],[200*rad,0,-100*rad,0],
                  [0,-300*rad,0,200*rad],[300*rad,0,-200*rad,0]]
        input_map=[[1,0,110,0],[0,1,0,110],[1,0,160,0],[0,1,0,160]]
        for i in range(4):
            for j in range(4):
                e.check('reflection double-angle lever response',r['response_matrix'][i][j],expected[i][j],atol=1e-7,rtol=1e-7)
                e.check('folded geometric propagation response',r['disturbance_matrix'][i][j],input_map[i][j],atol=1e-8,rtol=1e-7)
        initial=r['rows'][0]['residual']
        for k,row in enumerate(r['rows']):
            for a,c in zip(row['native_residual'],initial):e.check('native geometric feedback decay',a,c*.5**k,atol=1e-6,rtol=1e-6)
        assert max(map(abs,r['rows'][-1]['native_residual']))<1e-6
        assert await e.call('get_surfaces')==source and (await e.call('get_status'))['model_revision']==revision
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=2,count=3));assert len(page['rows'])==3
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'fsm.png'))))
        (e.folder/'fsm-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        fine=await e.finish(await e.call('run_analysis',dict(request=q|dict(disturbances=q['disturbances'][:2],
            probe_angle_deg=.00005,probe_height=.00005,probe_slope=.0000005))),timeout_seconds=180)
        for i in range(4):
            for j in range(4):e.check('FSM calibration step convergence',fine['response_matrix'][i][j],r['response_matrix'][i][j],atol=1e-7,rtol=1e-7)
        delayed=await e.finish(await e.call('run_analysis',dict(request=q|dict(disturbances=q['disturbances'][:10],
            delay_samples=1,gain=.2,actuator_time_constant_seconds=.001,measurement_noise_std=[1e-8]*4,seed=17))),timeout_seconds=180)
        assert delayed['summary']['native_validation_passed'] and delayed['summary']['actuator_discrete_alpha']<1
        saturated=await e.finish(await e.call('run_analysis',dict(request=q|dict(disturbances=q['disturbances'][:5],
            limits_deg=[1e-5]*4,probe_angle_deg=1e-6))),timeout_seconds=180)
        assert saturated['summary']['saturated_samples']>0 and not saturated['summary']['converged']
        assert await e.call('get_surfaces')==source
        for request,state in [(q|dict(observation_surfaces=[8,99]),'failed'),(q,'cancelled')]:
            t=await e.call('run_analysis',dict(request=request))
            if state=='cancelled':await e.call('cancel_task',dict(task_id=t['task_id']))
            for _ in range(1000):
                t=await e.call('get_task_status',dict(task_id=t['task_id']))
                if t['state'] in ['succeeded','failed','cancelled']:break
                await asyncio.sleep(.02)
            assert t['state']==state,t
            failed=await e.call('get_task_result',dict(task_id=t['task_id']));assert not failed['resources']['cleanup_errors']
        await e.call('update_surfaces',dict(changes=[dict(surface=8,thickness=0)]))
        failed=await e.call('run_analysis',dict(request=q|dict(disturbances=q['disturbances'][:2])))
        for _ in range(1000):
            failed=await e.call('get_task_status',dict(task_id=failed['task_id']))
            if failed['state'] in ['succeeded','failed','cancelled']:break
            await asyncio.sleep(.02)
        assert failed['state']=='failed'
        result=await e.call('get_task_result',dict(task_id=failed['task_id']))
        assert result['error']['code']=='UNOBSERVABLE_FSM' and result['resources']['copy_closed'],result
    asyncio.run(execute('fsm_control',work))
