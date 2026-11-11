import asyncio
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_nsc_efficiency_scan_optimize_stdio():
    async def work(e):
        await e.call('new_system',dict(mode='NonSequential'))
        await e.call('insert_nsc_objects',dict(request=dict(at=1,count=4)))
        changes=[dict(object=i+1,object_type='SourceRay',x=x,y=y,data=dict(NumberOfAnalysisRays=10,Power=.25,ZCosine=1))
                 for i,(x,y) in enumerate([(-.5,-.5),(.5,-.5),(-.5,.5),(.5,.5)])]
        changes.append(dict(object=5,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=2,NumberYPixels=2,XHalfWidth=1,YHalfWidth=1)))
        await e.call('update_nsc_objects',dict(request=dict(changes=changes)))
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42))))
        original=await e.call('get_nsc_objects',dict(request={}))
        detector=await e.call('get_detector_data',dict(request=dict(detector=5)))
        settings=await e.call('get_system_settings');revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='nsc_efficiency',sources=[1,2,3,4],detectors=[dict(detector=5,width=2,height=2)],
            rays_per_source=10,verification_rays_per_source=40)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        stats=result['summary']['detectors'][0]
        e.check('four sources total flux',stats['power'],1,atol=1e-8,rtol=1e-6)
        e.check('four sources efficiency',stats['efficiency'],1)
        e.check('uniform regular rays CV',stats['cv'],0)
        assert result['resources']['copy_closed'] and result['restoration']['restored']
        for row in result['grids'][0]['values']:
            for v in row:e.check('known pixel power',v,.25)
        partial=await e.finish(await e.call('run_analysis',dict(request=q|dict(detectors=[dict(detector=5,width=1,height=2)]))))
        e.check('asymmetric ROI power',partial['summary']['detectors'][0]['power'],.5)
        assert partial['grids'][0]['nx']==1 and partial['grids'][0]['ny']==2
        scan=q|dict(mode='scan',variables=[dict(object=1,cell='XPosition',minimum=-2,maximum=2,scan_values=[-2,-.5,2]),
            dict(object=1,cell='TiltY',minimum=0,maximum=2,scan_values=[0,2]),
            dict(object=1,cell='Power',minimum=.125,maximum=.25,scan_values=[.125,.25])])
        result=await e.finish(await e.call('run_analysis',dict(request=scan)))
        assert result['summary']['candidate_count']==13
        e.check('scan best efficiency',result['summary']['detectors'][0]['efficiency'],1)
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=1,count=2))
        assert len(page['rows'])==2
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'nsc-efficiency.png'))))
        assert await e.call('get_nsc_objects',dict(request={}))==original
        assert await e.call('get_system_settings')==settings
        after=await e.call('get_detector_data',dict(request=dict(detector=5)))
        assert after['values']==detector['values'] and after['total_flux']==detector['total_flux']
        assert (await e.call('get_status'))['model_revision']==revision
        for uniformity,expected in [(0,.4),(1,.25)]:
            opt=q|dict(sources=[1],mode='optimize',ranking='target_error',
                detectors=[dict(detector=5,width=2,height=2,target_power=.4,uniformity_weight=uniformity)],
                variables=[dict(object=1,cell='Power',minimum=.05,maximum=.8)])
            if uniformity==0:
                opt.update(algorithm='OrthogonalDescent',cycles='Fixed_50_Cycles')
                opt['variables']=[dict(object=1,cell='XPosition',minimum=-.8,maximum=-.2),
                    dict(object=1,cell='TiltY',minimum=-.5,maximum=.5)]+opt['variables']
            result=await e.finish(await e.call('run_analysis',dict(request=opt)))
            assert result['native_optimization']['succeeded'] and result['resources']['copy_closed']
            e.check('native optimized source power',result['summary']['best_values'][-1],expected,atol=1e-7,rtol=1e-6)
            e.check('one-ray power conservation',result['summary']['detectors'][0]['power'],expected,atol=1e-7,rtol=1e-6)
            pixels=[v for row in result['grids'][0]['values'] for v in row]
            mean=sum(pixels)/len(pixels)
            e.check('independent CV including zeros',result['summary']['detectors'][0]['cv'],math.sqrt(sum((v-mean)**2 for v in pixels)/len(pixels))/mean)
            assert result['summary']['best_score']<=result['summary']['baseline_score']
            await e.call('open_lens',dict(path=result['summary']['best_model']))
            replay=await e.finish(await e.call('run_analysis',dict(request=q|dict(sources=[1]))))
            e.check('saved candidate power',replay['summary']['source_power'],expected,atol=1e-7,rtol=1e-6)
            # Restore independent baseline for the next optimizer.
            await e.call('new_system',dict(mode='NonSequential'))
            await e.call('insert_nsc_objects',dict(request=dict(at=1,count=4)))
            await e.call('update_nsc_objects',dict(request=dict(changes=changes)))
        current=await e.call('get_nsc_objects',dict(request={}))
        for request,terminal in [(q|dict(detectors=[dict(detector=5,width=3,height=2)]),'failed'),(scan,'cancelled')]:
            t=await e.call('run_analysis',dict(request=request))
            if terminal=='cancelled':await e.call('cancel_task',dict(task_id=t['task_id']))
            for _ in range(500):
                t=await e.call('get_task_status',dict(task_id=t['task_id']))
                if t['state'] in ('failed','succeeded','cancelled'):break
                await asyncio.sleep(.02)
            assert t['state']==terminal,t
            r=await e.call('get_task_result',dict(task_id=t['task_id']))
            assert not r['resources']['cleanup_errors'] and r['restoration']['restored']
            if terminal=='failed':assert r['resources']['copy_closed']
            assert await e.call('get_nsc_objects',dict(request={}))==current
        await e.finish(await e.call('run_analysis',dict(request=q)))
    # Failure/cancellation paths use explicit terminal checks in a separate scenario below.
    asyncio.run(execute('nsc_efficiency_native',work))


@pytest.mark.zemax
def test_nsc_efficiency_random_rectangle_repeats():
    async def work(e):
        await e.call('new_system',dict(mode='NonSequential'))
        await e.call('insert_nsc_objects',dict(request=dict(at=1)))
        await e.call('update_nsc_objects',dict(request=dict(changes=[
            dict(object=1,object_type='SourceRectangle',data=dict(Power=1,NumberOfAnalysisRays=10000,XHalfWidth=1,YHalfWidth=1)),
            dict(object=2,object_type='DetectorRectangle',z=1,data=dict(NumberXPixels=8,NumberYPixels=6,XHalfWidth=10,YHalfWidth=10))])))
        q=dict(kind='nsc_efficiency',sources=[1],detectors=[dict(detector=2,width=8,height=6)],
            rays_per_source=1000,verification_rays_per_source=4000,verification_seeds=[42,43])
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        repeated=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['baseline']['grids'][0]['values']==repeated['baseline']['grids'][0]['values']
        assert result['verification'][0]['grids'][0]['values']==repeated['verification'][0]['grids'][0]['values']
        # Native SourceRectangle uses deterministic samples; different seed outputs may coincide.
        for r in result['verification']:
            assert r['trace']['dead_ray_errors']==0 and r['detectors'][0]['invalid_count']==0
            e.check('random source power',r['source_power'],1)
            e.check('rectangle received power',r['detectors'][0]['power'],1,atol=1e-8,rtol=1e-6)
        assert result['resources']['copy_closed'] and repeated['resources']['copy_closed']
    asyncio.run(execute('nsc_efficiency_random',work))


@pytest.mark.zemax
def test_nsc_efficiency_budget_and_final_readback():
    async def work(e):
        await e.call('new_system',dict(mode='NonSequential'))
        await e.call('insert_nsc_objects',dict(request=dict(at=1)))
        await e.call('update_nsc_objects',dict(request=dict(changes=[
            dict(object=1,object_type='SourceRay',data=dict(Power=1,NumberOfAnalysisRays=10,ZCosine=1)),
            dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=2,NumberYPixels=2,XHalfWidth=1,YHalfWidth=1))])))
        q=dict(kind='nsc_efficiency',sources=[1],detectors=[dict(detector=2,width=2,height=2)],rays_per_source=10,verification_rays_per_source=20,verification_seeds=[42])
        original=await e.call('get_nsc_objects',dict(request={}))
        t=await e.call('run_analysis',dict(request=q|dict(budget_seconds=.0001)))
        for _ in range(100):
            t=await e.call('get_task_status',dict(task_id=t['task_id']))
            if t['state'] in ('failed','cancelled','succeeded'):break
            await asyncio.sleep(.02)
        assert t['state']=='failed'
        r=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert r['error']['code']=='BUDGET_EXCEEDED' and r['resources']['copy_closed']
        scan=q|dict(mode='scan',variables=[dict(object=1,cell='TiltX',minimum=-1,maximum=1,scan_values=[-1,0,1])])
        r=await e.finish(await e.call('run_analysis',dict(request=scan)))
        e.check('post-update scan flux',r['summary']['detectors'][0]['power'],1)
        assert r['grids'][0]['min_x']==r['grids'][0]['x'][0]
        assert r['grids'][0]['min_y']==r['grids'][0]['y'][0]
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],item=1,path=str(e.folder/'roi.png'))))
        assert await e.call('get_nsc_objects',dict(request={}))==original
    asyncio.run(execute('nsc_efficiency_budget',work))
