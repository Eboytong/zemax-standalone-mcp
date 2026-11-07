"""Deterministic ZRD viewer reader, filters, pagination and reuse."""
import asyncio,json,time
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update

@pytest.mark.zemax
def test_ray_database_viewer_reference():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',x=.25,y=-.5,data=dict(NumberOfAnalysisRays=3,Power=1,ZCosine=1)),dict(object=2,object_type='DetectorRectangle',z=10,material='ABSORB',data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=5,NumberYPixels=5))])
        before=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings')
        zrd=e.folder/'controlled.zrd'
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(save_zrd=str(zrd),random_seed=42))))
        q=dict(kind='ray_database_viewer',path=str(zrd))
        full=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert full['native_closed'] and full['task']['state']=='succeeded'
        assert len({r['RayNumber'] for r in full['rows']})==3
        expected=[]
        for row in full['rows']:
            if row['HitObject']==2:
                for name,value in [('X',.25),('Y',-.5),('Z',10.),('L',0),('M',0),('N',1),('Intensity',1/3)]:
                    e.check('detector '+str(row['RayNumber'])+' '+name,row[name],value,atol=1e-8,rtol=1e-7)
                expected.append(row)
        assert len(expected)==3
        rows=[];resume={}
        while True:
            result=await e.finish(await e.call('run_analysis',dict(request=q|dict(max_segments=2)|resume)))
            assert result['native_closed'];rows+=result['rows'];resume=result['summary']['next_read']
            if not resume:break
        assert [(r['RayNumber'],r['segment_index']) for r in rows]==[(r['RayNumber'],r['segment_index']) for r in full['rows']]
        for expression,count in [('H2',len(full['rows'])),('H99',0)]:
            result=await e.finish(await e.call('run_analysis',dict(request=q|dict(filter=expression))))
            assert result['summary']['actual_filter']==expression and len(result['rows'])==count
        page=await e.call('get_task_result',dict(task_id=full['task']['task_id'],start=1,count=2))
        assert page['rows']==full['rows'][1:3]
        bad=e.folder/'broken.zrd';bad.write_bytes(b'invalid database')
        response=await e.call('run_analysis',dict(request=q|dict(path=str(bad))))
        deadline=time.monotonic()+30
        while response['state'] not in ('failed','cancelled','succeeded'):
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);response=await e.call('get_task_status',dict(task_id=response['task_id']))
        assert response['state']=='succeeded',response
        failed=await e.call('get_task_result',dict(task_id=response['task_id']))
        assert failed['rows']==[] and failed['native_closed']
        assert failed['summary']['segments']==0
        await e.finish(await e.call('run_analysis',dict(request=q)))
        after=await e.call('get_nsc_objects',dict(request={}))
        assert [(r['object'],r['data']['Type'],r['data'].get('Power'),r['data'].get('NumberOfAnalysisRays'),r['data'].get('XHalfWidth')) for r in after['rows']]==[(r['object'],r['data']['Type'],r['data'].get('Power'),r['data'].get('NumberOfAnalysisRays'),r['data'].get('XHalfWidth')) for r in before['rows']]
        assert await e.call('get_system_settings')==settings
        await e.call('save_lens_as',dict(path=str(e.folder/'reload.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'reload.zos')))
        reloaded=await e.call('get_nsc_objects',dict(request={}))
        assert [(r['object'],r['data']['Type'],r['data'].get('Power'),r['data'].get('NumberOfAnalysisRays'),r['data'].get('XHalfWidth')) for r in reloaded['rows']]==[(r['object'],r['data']['Type'],r['data'].get('Power'),r['data'].get('NumberOfAnalysisRays'),r['data'].get('XHalfWidth')) for r in before['rows']]
        assert await e.call('get_system_settings')==settings
        again=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert again['rows']==full['rows']
        (e.folder/'reference.json').write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('zrd457_reference',work))



@pytest.mark.zemax
def test_viewer_cancellation_closes_native_reader():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10000,Power=1,ZCosine=1)),dict(object=2,object_type='DetectorRectangle',z=10,material='ABSORB',data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=2,NumberYPixels=2))])
        zrd=e.folder/'cancel.zrd';await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(save_zrd=str(zrd),random_seed=42))))
        q=dict(kind='ray_database_viewer',path=str(zrd),max_segments=100000)
        task=await e.call('run_analysis',dict(request=q))
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+30
        while task['state'] not in ('succeeded','failed','cancelled'):
            assert time.monotonic()<deadline
            await asyncio.sleep(.01);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        result=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert not result['completed'] and result['native_closed'],result
        resumed=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert resumed['native_closed'] and resumed['rows']
    asyncio.run(execute('zrd462_cancel',work))
