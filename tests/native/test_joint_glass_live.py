import asyncio
import itertools

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_joint_glass_nine_combinations_and_independent_controls():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces', dict(at=1, count=2))
        await e.call('update_system_settings', dict(settings=dict(aperture_value=5, material_catalogs=['SCHOTT'],
            fields=[dict(x=0,y=0),dict(x=0,y=2)], wavelengths=[dict(wavelength_um=w) for w in [.4861327,.5875618,.6562725]])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,is_stop=True,semi_diameter=5,radius=50,thickness=3,material='N-BK7',replace_solves=True),
            dict(surface=2,semi_diameter=5,radius=-40,thickness=2,material='N-F2',replace_solves=True),
            dict(surface=3,semi_diameter=5,radius=-150,thickness=90,replace_solves=True)]))
        original=await e.call('get_surfaces')
        slots=await e.call('get_glass_slots');assert len(slots['slots'])==2,slots
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        pools=[['N-BK7','N-BAK4','N-FK5'], ['N-F2','N-SF5','N-SF6']]
        common=dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)],catalogs=['SCHOTT'],
            variables=[dict(surface=3,cell='thickness',minimum=65,maximum=110)],objectives=[dict(metric='rms_spot')],
            cycles='Fixed_1_Cycle',nd_tolerance=1,vd_tolerance=200,max_candidates=1)
        joint=common|dict(joint_slots=[dict(group=i,materials=[dict(catalog='SCHOTT',material=m) for m in materials]) for i,materials in enumerate(pools)])
        result=await e.finish(await e.call('run_analysis',dict(request=joint)),timeout_seconds=240)
        assert result['summary']['succeeded']==9 and result['discovery']['combination_count']==9,result
        assert result['finalist_recheck']['passed'] and result['resources']['all_copies_closed']
        assert await e.call('get_surfaces')==original
        by_identity={tuple(a['identity']['material'] for a in row['assignments']):row for row in result['rows']}
        assert len(by_identity)==9
        for pair in itertools.product(*pools):
            await e.call('update_surfaces',dict(changes=[dict(surface=i+1,material=material) for i,material in enumerate(pair)]))
            independent=await e.finish(await e.call('run_analysis',dict(request=common|dict(max_relative_cost=.000001))),timeout_seconds=120)
            assert independent['summary']['succeeded']==1
            for metric,value in by_identity[pair]['after'].items():
                e.check(f'{pair} independent {metric}',value,independent['rows'][0]['after'][metric],atol=1e-8,rtol=1e-7)
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        beam=await e.finish(await e.call('run_analysis',dict(request=joint|dict(search_strategy='beam',beam_width=1))),timeout_seconds=240)
        assert 3<=beam['summary']['succeeded']<=5 and beam['finalist_recheck']['passed'],beam['summary']
        empty_beam_request=common|dict(joint_slots=[
            dict(group=0,materials=[dict(catalog='SCHOTT',material='N-BK7')],pool_size=1),
            dict(group=1,materials=[dict(catalog='SCHOTT',material='N-F2')],pool_size=1)],
            search_strategy='beam',beam_width=1,max_evaluations=5)
        empty_beam=await e.finish(await e.call('run_analysis',dict(request=empty_beam_request)),timeout_seconds=180)
        assert empty_beam['summary']['candidate_count']==1,empty_beam['summary']
        assert empty_beam['summary']['succeeded']==1 and empty_beam['summary']['termination_reason']=='completed'
        assert empty_beam['finalist_recheck']['passed'] and empty_beam['resources']['all_copies_closed']
        limited=await e.finish(await e.call('run_analysis',dict(request=joint|dict(max_evaluations=3))),timeout_seconds=180)
        assert limited['summary']['succeeded']==3 and limited['summary']['termination_reason']=='evaluation_budget'
        # Saved native candidates participate in the same persistent candidate API.
        design=result['design_id'];candidate=result['rows'][1]['candidate']['candidate_id']
        index=await e.call('manage_candidates',dict(request=dict(action='list',design_id=design)))
        assert candidate in index['candidates']
        evaluated=await e.finish(await e.call('run_candidate_evaluation',dict(request=dict(design_id=design,candidate_ids=[index['baseline_candidate_id'],candidate]))))
        assert evaluated['summary']['evaluated']==2
    asyncio.run(execute('d019_joint_glass',work))


@pytest.mark.zemax
def test_joint_glass_cancellation_closes_active_optimization_copy():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5,material_catalogs=['SCHOTT'],
            fields=[dict(x=0,y=0),dict(x=0,y=2)],wavelengths=[dict(wavelength_um=w) for w in [.4861327,.5875618,.6562725]])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,is_stop=True,semi_diameter=5,radius=50,thickness=3,material='N-BK7',replace_solves=True),
            dict(surface=2,semi_diameter=5,radius=-40,thickness=2,material='N-F2',replace_solves=True),
            dict(surface=3,semi_diameter=5,radius=-150,thickness=90,replace_solves=True)]))
        original=await e.call('get_surfaces')
        request=dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)],
            catalogs=['SCHOTT'],variables=[dict(surface=3,cell='thickness',minimum=65,maximum=110)],
            objectives=[dict(metric='rms_spot')],cycles='Fixed_50_Cycles',nd_tolerance=1,vd_tolerance=200,
            joint_slots=[dict(group=0,materials=[dict(catalog='SCHOTT',material='N-BK7'),dict(catalog='SCHOTT',material='N-BAK4')]),
                dict(group=1,materials=[dict(catalog='SCHOTT',material='N-F2')])],
            search_strategy='beam',beam_width=1,max_evaluations=8,budget_per_candidate_seconds=120,total_budget_seconds=600)
        task=await e.call('run_analysis',dict(request=request))
        deadline=asyncio.get_running_loop().time()+90
        while task['state']=='running' and not (task.get('active_step') or {}).get('kind')=='glass_native_optimization':
            assert asyncio.get_running_loop().time()<deadline,task
            await asyncio.sleep(.05)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='running' and task['active_step']['state']=='running',task
        await e.call('cancel_task',dict(task_id=task['task_id']))
        while task['state'] not in ['succeeded','failed','cancelled']:
            assert asyncio.get_running_loop().time()<deadline
            await asyncio.sleep(.05)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        result=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert result['completed'] is False
        assert result['resources']['copies_created']==result['resources']['copies_closed']
        assert result['resources']['all_copies_closed']
        assert await e.call('get_surfaces')==original
    asyncio.run(execute('d019_joint_glass_cancel',work))
