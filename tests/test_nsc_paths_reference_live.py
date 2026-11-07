"""Independent flux and reference-frame checks for NSC path analyses."""
import asyncio
import json
import time
import pytest
from support.native import execute
from support.nsc import setup,update,trace


@pytest.mark.zemax
def test_path_sources_threshold_reload_and_recovery():
    async def work(e):
        await setup(e,3)
        await update(e,[
            dict(object=1,object_type='SourceRay',x=-.2,data=dict(NumberOfAnalysisRays=10,Power=.25,ZCosine=1)),
            dict(object=2,object_type='SourceRay',x=.2,data=dict(NumberOfAnalysisRays=10,Power=.75,ZCosine=1)),
            dict(object=3,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5)),
        ])
        saved=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        await trace(e,'two_sources')
        for threshold in [0,.5]:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='path_analysis',path=str(e.folder/'two_sources.zrd'),relative_minimum_flux=threshold))))
            classified=sum(r['flux_out_w']for r in result['rows'])
            # The threshold is branch-end / that branch's launch energy.
            # Both lossless branches have relative flux 1 despite unequal sources.
            e.check('classified flux '+str(threshold),classified,1)
            assert sorted(r['source']for r in result['rows'])==[1,2]
            assert result['uncategorized'] is None
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('paths063_threshold',work))


@pytest.mark.zemax
def test_single_reference_frame_polarization_and_truncation():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(ZCosine=1)),
                        dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5))])
        saved=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        request=dict(kind='nsc_single_ray_trace',reference_object=2,x=.2,y=-.3,z=-10,use_polarization=True)
        result=await e.finish(await e.call('run_analysis',dict(request=request)))
        hit=next(r for r in result['rows']if r['hit_object']==2)
        for axis,target in dict(x=.2,y=-.3,z=10,l=0,m=0,n=1,intensity=1,path_length=10).items():
            e.check('reference ray '+axis,hit[axis],target)
        assert [r['native_segment_index']for r in result['rows']]==list(range(1,len(result['rows'])+1))
        assert any(a['kind']=='zrd'for a in result['artifacts'])
        small=await e.finish(await e.call('run_analysis',dict(request=request|dict(max_segments=1))))
        assert small['summary']['truncated'] and len(small['rows'])==1
        for r in [result,small]:
            status=await e.call('get_task_status',dict(task_id=r['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
            await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=0,count=1))
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('single063_reference',work))


@pytest.mark.zemax
def test_path_and_single_cancellation_recovery():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=200000,ZCosine=1)),
                        dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5))])
        await trace(e,'cancellation',max_segments=1)
        baseline=await e.call('get_nsc_objects',dict(request={}))
        records=[]
        critical=e.folder/'cancel.CRS'
        critical.write_text('1000 4 20261105 4 0 0 0\n! X Y Z L M N intensity wavelength field type Xtarget Ytarget Ztarget Ltarget Mtarget Ntarget\n'+('0 0 0 0 0 1 1 .55 0 7 0 0 20 0 0 1\n'*1000),encoding='ascii')
        for request in [dict(kind='path_analysis',path=str(e.folder/'cancellation.zrd')),dict(kind='nsc_single_ray_trace'),dict(kind='critical_ray_trace',path=str(critical))]:
            task=await e.call('run_analysis',dict(request=request))
            was_running=task['state']=='running'
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+90
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
            records.append(dict(kind=request['kind'],initial_running=was_running,terminal=task['state'],closed=task['close_attempted']))
            await e.call('get_task_result',dict(task_id=task['task_id']))
            assert await e.call('get_nsc_objects',dict(request={}))==baseline
        (e.folder/'cancellation.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_single_ray_trace'))))
    asyncio.run(execute('paths063_cancel',work))


@pytest.mark.zemax
def test_path_uncategorized_flux_against_independent_database_sum():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10,ZCosine=1),sources=dict(RandomPolarization=False,Jx=1,Jy=0)),
                        dict(object=2,object_type='RectangularVolume',z=5,material='N-BK7',data=dict(X1HalfWidth=10,Y1HalfWidth=10,X2HalfWidth=10,Y2HalfWidth=10,ZLength=2)),
                        dict(object=3,object_type='DetectorRectangle',z=12,data=dict(NumberXPixels=7,NumberYPixels=5))])
        baseline=await e.call('get_nsc_objects',dict(request={}))
        _,segments=await trace(e,'loss',use_polarization=True,split_rays=False)
        reference=sum(r['Intensity']for r in segments if r['HitObject']==3)
        assert .8<reference<.99
        for threshold in [0,1]:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='path_analysis',path=str(e.folder/'loss.zrd'),relative_minimum_flux=threshold))))
            if threshold==0:
                e.check('lossy classified / independent ZRD',sum(r['flux_out_w']for r in result['rows']),reference)
                assert result['uncategorized'] is None
            else:
                assert result['rows']==[]
                assert result['uncategorized'] is not None,result.get('uncategorized_native_message')
                e.check('uncategorized / independent ZRD',result['uncategorized']['total_path_flux_w'],reference)
            assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('paths063_uncategorized',work))
