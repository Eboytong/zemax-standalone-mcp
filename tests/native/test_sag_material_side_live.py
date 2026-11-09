"""Native BFSD manufacturing blank changes when the glass/air side changes."""
import asyncio
import math
import time
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_sag_material_side_depth_and_state():
    async def work(e):
        for sign in (1., -1.):
            for side in ('entering', 'exiting'):
                await e.call('new_system')
                await e.call('insert_surfaces', dict(at=1))
                await e.call('update_surfaces', dict(changes=[
                    dict(surface=1, material='N-BK7' if side == 'exiting' else '', thickness=5., replace_solves=True),
                    dict(surface=2, surface_type='EvenAspheric', radius=sign*40., conic=-1.,
                         parameters={'1': sign*.0001}, semi_diameter=5., thickness=20.,
                         aperture=dict(type='CircularAperture', maximum_radius=5.),
                         material='N-BK7' if side == 'entering' else '', replace_solves=True)]))
                names = ('get_system_settings', 'get_surfaces', 'get_merit_function')
                before = {name: await e.call(name) for name in names}
                result = await e.finish(await e.call('run_analysis', dict(request=dict(kind='sag_table', surface=2, samples=17))))
                direction = 1 if side == 'entering' else -1
                assert result['manufacturing_direction']['direction'] == direction
                summary = result['summary']
                c, offset = summary['curvature'], summary['vertex_offset']
                for row in result['rows']:
                    y = row['y']
                    raw = sign*.0126*y*y
                    sphere = c*y*y/(1+math.sqrt(1-(c*y)**2))
                    expected = direction*(raw-sphere-offset)
                    e.check(f'{sign} {side} oriented removal {y}', row['removal_depth'], expected, atol=1e-8, rtol=1e-6)
                    e.check(f'{sign} {side} signed deviation {y}', row['signed_vertex_deviation'], raw-sphere-offset, atol=1e-8, rtol=1e-6)
                    assert row['removal_depth'] >= -1e-8
                # Independent BFSD documented radial summary sampling, retaining all endpoints.
                ys = [5.*i/1000 for i in range(1001)]
                depth = [direction*(sign*.0126*y*y-c*y*y/(1+math.sqrt(1-(c*y)**2))-offset) for y in ys]
                e.check(f'{sign} {side} BFSD maximum removal', summary['maximum_removal_depth'], max(depth), atol=1e-6, rtol=1e-5)
                e.check(f'{sign} {side} BFSD RMS removal', summary['rms_removal_depth'], math.sqrt(sum(y*d*d for y,d in zip(ys,depth))/sum(ys)), atol=1e-6, rtol=1e-5)
                e.check(f'{sign} {side} BFSD volume', summary['removal_volume'], 2*math.pi*.005*sum(y*d for y,d in zip(ys,depth)), atol=1e-5, rtol=1e-5)
                task = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
                assert task['state'] == 'succeeded' and not task.get('cleanup_warnings')
                for name in names:
                    assert await e.call(name) == before[name]
                page = await e.call('get_task_result', dict(task_id=task['task_id'], start=5, count=3))
                assert page['rows'] == result['rows'][5:8]
                e.checks.append(dict(label='material-side geometry and source state', sign=sign, side=side,
                                     direction=result['manufacturing_direction'], summary=summary, passed=True))
        # Last controlled case is a glass/air stop; exercise the adopted circle
        # cleanup under cancellation and persistence of the source aperture.
        path = str(e.folder / 'material-side-baseline.zos')
        await e.call('save_lens_as', dict(path=path))
        await e.call('open_lens', dict(path=path))
        reloaded = await e.finish(await e.call('run_analysis', dict(request=dict(kind='sag_table', surface=2, samples=17))))
        assert reloaded['rows'] == result['rows']
        assert reloaded['summary'] == result['summary']
        task = await e.call('run_analysis', dict(request=dict(kind='sag_table', surface=2, samples=10001)))
        deadline = time.monotonic() + 30
        while task.get('phase') != 'sampling_rows':
            assert time.monotonic() < deadline and task['state'] == 'running', task
            await asyncio.sleep(.02)
            task = await e.call('get_task_status', dict(task_id=task['task_id']))
        task = await e.call('cancel_task', dict(task_id=task['task_id']))
        while task['state'] not in {'succeeded', 'failed', 'cancelled'}:
            assert time.monotonic() < deadline
            await asyncio.sleep(.02)
            task = await e.call('get_task_status', dict(task_id=task['task_id']))
        cancelled = await e.call('get_task_result', dict(task_id=task['task_id']))
        assert task['state'] == 'cancelled' and cancelled['slope_query_copy']['closed']
        assert cancelled['slope_query_copy']['unclipped_method'].startswith('enclosing_circle_')
        reused = await e.finish(await e.call('run_analysis', dict(request=dict(kind='sag_table', surface=2, samples=17))))
        assert reused['rows'] == result['rows']
        assert reused['slope_query_copy']['closed']
        for name in names:
            assert await e.call(name) == before[name]
        e.checks.append(dict(label='enclosing stop slope copy cancel, reload and reuse', passed=True,
                             cancelled=cancelled['slope_query_copy'], reloaded=reloaded['task']['task_id']))
    asyncio.run(execute('sag_material_side', work))
