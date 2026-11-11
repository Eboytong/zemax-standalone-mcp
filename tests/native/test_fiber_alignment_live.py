"""Native scalar complex overlaps, pose search, loss widths and restoration."""
import asyncio
import json
import math

import pytest

from tests.support.native import execute


def gaussian_efficiency(axis,value,w=.1,wave=.00055):
    if axis in {'x','y'}:
        return math.exp(-(value/w)**2)
    if axis=='z':
        zr=math.pi*w*w/wave
        return 1/(1+(value/(2*zr))**2)
    return math.exp(-(math.pi*w*math.sin(math.radians(value))/wave)**2)


@pytest.mark.zemax
def test_pop_fiber_alignment_stdio():
    async def work(e):
        await e.model()
        settings=dict(beam_parameters={0:.1,1:.1},fiber_type='AstigmaticGaussian',
            fiber_parameters={0:.1,1:.1,2:0,3:0,4:0,5:0},
            x_sampling='S_128x128',y_sampling='S_128x128',x_width=1,y_width=1)
        before=await e.call('get_surfaces',dict(start=1,count=2))
        for axis,span in [('x',.1),('y',.1),('z',60),('tilt_x',.1),('tilt_y',.1)]:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fiber_alignment',
                settings=settings,axes=[dict(axis=axis,values=[-span,0,span])],
                tolerance_axes=[],save_best=False))))
            for row in result['rows']:
                e.check(axis+' analytic complex overlap',row['value'],
                    gaussian_efficiency(axis,row['pose'][axis]),atol=5e-4,rtol=0)
                assert row['close_attempted']
            assert result['summary']['best']['pose'][axis]==0
        # Matching a displaced, defocused Gaussian proves native signs and pose identity.
        displaced=settings|dict(beam_type='AstigmaticGaussian',
            beam_parameters={0:.1,1:.1,2:5,3:5,4:.023,5:-.017})
        zscan=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fiber_alignment',
            settings=displaced|dict(fiber_parameters={0:.1,1:.1,4:.023,5:-.017}),
            axes=[dict(axis='z',values=[0,5,10])],tolerance_axes=[],save_best=False))))
        e.check('matching native axial waist position',zscan['summary']['best']['pose']['z'],5,atol=1e-12,rtol=0)
        e.check('matched defocused complex field',zscan['summary']['best']['value'],1,atol=5e-4,rtol=0)

        shifted=settings|dict(beam_parameters={0:.1,1:.1,2:.023,3:-.017})
        q=dict(kind='fiber_alignment',settings=shifted,
            axes=[dict(axis='x',values=[-.1,0,.1]),dict(axis='y',values=[-.1,0,.1])],
            optimization=dict(bounds=[dict(axis='x',minimum=-.1,maximum=.1),
                                     dict(axis='y',minimum=-.1,maximum=.1)],max_iterations=40),
            tolerance_axes=[dict(axis='x',values=[i*.01 for i in range(-15,16)])],
            max_evaluations=250,budget_seconds=600)
        result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=600)
        best=result['summary']['best']
        e.check('best receiver X',best['pose']['x'],.023,atol=.0003,rtol=0)
        e.check('best receiver Y',best['pose']['y'],-.017,atol=.0003,rtol=0)
        e.check('optimized coupling',best['value'],1,atol=5e-4,rtol=0)
        assert result['search']['state']=='step_tolerance'
        for crossing in result['tolerances'][0]['crossings']:
            expected=2*.1*math.sqrt(crossing['loss_db']*math.log(10)/10)
            e.check(str(crossing['loss_db'])+' dB width',crossing['width'],expected,
                    atol=0,rtol=.005)
            assert crossing['converged']
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=2,count=3))
        assert page['rows']==result['rows'][2:5]
        grid=result['grids'][0]
        region=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,
            x_start=1,y_start=1,width=2,height=3))
        assert region['grid']['values']==[r[1:3]for r in grid['values'][1:4]]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],
            item=len(result['series']),path=str(e.folder/'alignment.png'))))
        candidate=result['summary']['best_candidate']
        request=json.loads(__import__('pathlib').Path(candidate['request']).read_text(encoding='utf-8'))
        assert await e.call('get_surfaces',dict(start=1,count=2))==before
        await e.call('open_lens',dict(path=candidate['model']))
        replay=await e.finish(await e.call(request['tool'],request['arguments']))
        e.check('saved candidate replay',replay['metrics']['receiver_efficiency'],best['value'],atol=1e-8,rtol=1e-7)
        fine=request['arguments']['request']|dict(x_sampling='S_256x256',y_sampling='S_256x256')
        replay=await e.finish(await e.call('run_pop',dict(request=fine)))
        e.check('sampling refinement peak',replay['metrics']['receiver_efficiency'],best['value'],atol=5e-4,rtol=0)
        # Actual cancellation releases child analyses and preserves all source model cells.
        before=await e.call('get_surfaces',dict(start=1,count=2))
        pending=await e.call('run_analysis',dict(request=q))
        await e.call('cancel_task',dict(task_id=pending['task_id']))
        for _ in range(300):
            terminal=await e.call('get_task_status',dict(task_id=pending['task_id']))
            if terminal['state'] in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02)
        assert terminal['state']=='cancelled'
        assert await e.call('get_surfaces',dict(start=1,count=2))==before

    async def guarded(e):
        try:await work(e)
        finally:await e.call('disconnect')
    asyncio.run(execute('fiber_alignment_native',guarded))


@pytest.mark.zemax
def test_alignment_failure_reuse_and_budget():
    async def work(e):
        await e.model()
        settings=dict(fiber_type='AstigmaticGaussian',fiber_parameters={0:.1,1:.1},
            beam_parameters={0:.1,1:.1},x_width=1,y_width=1)
        q=dict(kind='fiber_alignment',settings=settings,axes=[dict(axis='x',values=[0,.1])],
            refine=False,save_best=False)
        before=await e.call('get_surfaces',dict(start=1,count=2))
        pending=await e.call('run_analysis',dict(request=q|dict(settings=settings|dict(field=2))))
        for _ in range(200):
            terminal=await e.call('get_task_status',dict(task_id=pending['task_id']))
            if terminal['state'] in {'failed','succeeded','cancelled'}:break
            await asyncio.sleep(.01)
        assert terminal['state']=='failed' and terminal['error']['code']=='INDEX_OUT_OF_RANGE'
        partial=await e.call('get_task_result',dict(task_id=pending['task_id']))
        assert partial['rows'][0]['error']['code']=='INDEX_OUT_OF_RANGE'
        good=await e.finish(await e.call('run_analysis',dict(request=q|dict(max_evaluations=2,
            tolerance_axes=[dict(axis='y',values=[-.2,0,.2])]))))
        assert good['summary']['stop_reason']=='evaluation_or_time_budget'
        assert good['summary']['evaluations']==2
        assert await e.call('get_surfaces',dict(start=1,count=2))==before
    async def guarded(e):
        try:await work(e)
        finally:await e.call('disconnect')
    asyncio.run(execute('fiber_alignment_failure_budget',guarded))
