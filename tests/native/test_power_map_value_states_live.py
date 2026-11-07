"""Native raw-zero identity and validity scope survive result pagination."""
import asyncio
import json
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_power_map_raw_value_states_and_paging():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5875618)],
            fields=[dict(x=0, y=0), dict(x=1, y=1)])))
        records = []
        for radius in [0, 50]:
            await e.call('update_surfaces', dict(changes=[dict(surface=1,
                radius=radius, thickness=50, material='N-BK7', semi_diameter=8,
                is_stop=True, replace_solves=True)]))
            source = str(e.folder / f'source-{radius}.zos')
            await e.call('save_lens_as', dict(path=source))
            await e.call('open_lens', dict(path=source))
            before = await e.call('get_surfaces')
            settings = await e.call('get_system_settings')
            merit = await e.call('get_merit_function')
            for kind in ['power_field_map', 'power_pupil_map']:
                for quantity in ['Power', 'EFL']:
                    q = dict(kind=kind, surface=1, quantity=quantity, offset=7,
                             x_points=3, y_points=3)
                    if kind == 'power_field_map':
                        q.update(x_field_width=2, y_field_width=2)
                    result = await e.finish(await e.call('run_analysis', dict(request=q)))
                    grid = result['grids'][0]
                    center = next(r for r in result['rows'] if r['grid_x'] == r['grid_y'] == 1)
                    assert result['native_ring_validity'] == 'unavailable'
                    assert grid['valid_mask_scope'] == result['valid_mask_scope']
                    assert center['native_query_status'] == 'returned_finite_value'
                    assert center['native_ring_validity'] == 'unavailable'
                    assert grid['valid_mask'][1][1] is True
                    if radius == 0:
                        assert center['raw_value'] == 0 and center['value'] == 7
                        assert center['raw_value_state'] == 'native_zero'
                        assert center['zero_interpretation'] == 'unresolved_native_zero_semantics'
                        assert grid['native_zero_count'] >= 1
                    else:
                        assert center['raw_value_state'] == 'finite_nonzero'
                        reference = 6.814355276657183 if quantity == 'Power' else 146.7490260488084
                        e.check(kind + ' ' + quantity, center['raw_value'], reference, atol=2e-4, rtol=2e-5)
                    task_id = result['task']['task_id']
                    page = await e.call('get_task_result', dict(task_id=task_id, start=0, count=2))
                    assert page['rows'] == result['rows'][:2]
                    region = await e.call('get_task_result', dict(task_id=task_id,
                        grid=0, x_start=1, y_start=1, width=1, height=1))
                    assert region['grid']['values'] == [[center['value']]]
                    status = await e.call('get_task_status', dict(task_id=task_id))
                    assert status['state'] == 'succeeded' and not status.get('cleanup_warnings')
                    records.append(dict(request=q, result=result, page=page, region=region, status=status))
                    (e.folder / 'value-states.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
            assert await e.call('get_surfaces') == before
            assert await e.call('get_system_settings') == settings
            assert await e.call('get_merit_function') == merit
            target = str(e.folder / f'after-{radius}.zos')
            await e.call('save_lens_as', dict(path=target))
            await e.call('open_lens', dict(path=target))
            assert await e.call('get_surfaces') == before
            assert await e.call('get_system_settings') == settings
            assert await e.call('get_merit_function') == merit

    async def guarded(e):
        try:
            await work(e)
        except BaseException:
            await e.call('disconnect', okay=False)
            raise
    asyncio.run(execute('power596_value_states', guarded))

