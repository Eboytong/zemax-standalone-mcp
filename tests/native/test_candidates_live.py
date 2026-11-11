import asyncio

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_candidates_branch_evaluate_compare_restore_stdio():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces', dict(at=1, count=2))
        await e.call('update_system_settings', dict(settings=dict(aperture_value=5,
            material_catalogs=['SCHOTT'], wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=50, thickness=3, material='N-BK7', semi_diameter=5, replace_solves=True),
            dict(surface=2, radius=-50, thickness=48, semi_diameter=5, replace_solves=True)]))
        baseline = await e.call('get_surfaces')
        create = await e.call('manage_candidates', dict(request=dict(action='create', label='baseline',
            evaluation=dict(spot=dict(reference='Centroid', ray_density=6)))))
        design = create['design_id']; root = create['candidate']['candidate_id']
        saved = [root]
        for label, patch in [('A', dict(surface=1, radius=45)),
                             ('B', dict(surface=1, material='N-F2')),
                             ('C', dict(surface=2, thickness=49))]:
            branch = await e.call('manage_candidates', dict(request=dict(action='branch',
                design_id=design, parent_candidate_id=root, label=label)))
            key = branch['candidate']['candidate_id']
            selected = await e.call('manage_candidates', dict(request=dict(action='select', design_id=design, candidate_id=key)))
            assert selected['selected']['candidate_id'] == key
            await e.call('update_surfaces', dict(changes=[patch]))
            current = await e.call('manage_candidates', dict(request=dict(action='checkpoint', design_id=design,
                candidate_id=key, label=label+' modified', modification_summary=str(patch))))
            saved.append(current['candidate']['candidate_id'])
        result = await e.finish(await e.call('run_candidate_evaluation', dict(request=dict(design_id=design, candidate_ids=saved))))
        assert result['summary']['evaluated'] == 4 and result['restoration']['restored']
        for key in saved[1:]:
            comparison = await e.call('manage_candidates', dict(request=dict(action='compare', design_id=design,
                left_candidate_id=root, right_candidate_id=key)))
            assert comparison['compatible'] and comparison['metrics']
            assert comparison['design_differences']['left'] != comparison['design_differences']['right']
        await e.call('manage_candidates', dict(request=dict(action='restore', design_id=design, candidate_id=root)))
        assert await e.call('get_surfaces') == baseline
        page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=1, count=1))
        assert page['rows'][0]['candidate_id'] == saved[1]
        index = await e.call('manage_candidates', dict(request=dict(action='list', design_id=design)))
        assert index['candidates'][root]['evaluation']['state'] == 'succeeded'
        await e.call('export_evaluation_report', dict(task_ids=[result['task']['task_id']], title='候选比较'))
        # Contract mismatch fails with a named origin, then restores the active model.
        await e.call('update_system_settings', dict(settings=dict(wavelengths=[dict(wavelength_um=.6)])))
        changed = await e.call('manage_candidates', dict(request=dict(action='checkpoint', design_id=design,
            candidate_id=root, label='different wavelength', modification_summary='wavelength .6um')))
        changed_id = changed['candidate']['candidate_id']
        t = await e.call('run_candidate_evaluation', dict(request=dict(design_id=design, candidate_ids=[changed_id])))
        for _ in range(200):
            t = await e.call('get_task_status', dict(task_id=t['task_id']))
            if t['state'] in {'failed', 'succeeded', 'cancelled'}:
                break
            await asyncio.sleep(.02)
        assert t['state'] == 'failed', t
        failed = await e.call('get_task_result', dict(task_id=t['task_id']))
        assert failed['error']['code'] == 'EVALUATION_CONDITIONS_CHANGED' and failed['restoration']['restored']
        await e.call('manage_candidates', dict(request=dict(action='restore', design_id=design, candidate_id=root)))
        t = await e.call('run_candidate_evaluation', dict(request=dict(design_id=design, candidate_ids=saved)))
        await e.call('cancel_task', dict(task_id=t['task_id']))
        for _ in range(200):
            t = await e.call('get_task_status', dict(task_id=t['task_id']))
            if t['state'] in {'failed', 'succeeded', 'cancelled'}:
                break
            await asyncio.sleep(.02)
        assert t['state'] == 'cancelled', t
        cancelled = await e.call('get_task_result', dict(task_id=t['task_id']))
        assert cancelled['restoration']['restored']
        assert await e.call('get_surfaces') == baseline
    asyncio.run(execute('d018_candidates', work))
