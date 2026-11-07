"""Independent analytic sag reference at every returned valid sample."""
import asyncio,math,json
import pytest
from support.native import execute
from support.nsc import setup,update

@pytest.mark.zemax
def test_nsc_surface_sag_numeric_and_zrd():
    async def work(e):
        await setup(e,1)
        await update(e,[dict(object=1,object_type='StandardLens',material='N-BK7',data=dict(Radius1=50,Clear1=5,Clear2=5,Thickness=2,Radius2=0))])
        saved=str(e.folder/'sphere.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        records=[]
        for face,keep in [(1,False),(2,False),(1,True),(2,True),(1,'offset')]:
            request=dict(kind='nsc_surface_sag',object_number=1,face_number=face,sampling='S_33x33',width=2,show_as='FalseColor')
            if keep is True:request.update(keep_zrd=True,zrd_filename=f'face{face}.zrd')
            if keep=='offset':request.update(decenter_x=.5,decenter_y=-.25)
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            g=result['grids'][0]
            errors=[0.,0.]
            for iy,row in enumerate(g['values']):
                for ix,value in enumerate(row):
                    if value is None:continue
                    x=g['min_x']+ix*g['dx'];y=g['min_y']+iy*g['dy']
                    for mode in [0,1]:
                        px,py=(x,y)if mode==0 else(g['min_x']+iy*g['dx'],g['min_y']+ix*g['dy'])
                        if keep=='offset':px+=.5;py-=.25
                        reference=50-math.sqrt(2500-px*px-py*py)if face==1 else 0
                        errors[mode]=max(errors[mode],abs(value-reference))
                        if mode==0:e.check('analytic face sag',value,reference,atol=1e-8,rtol=1e-7)
            assert result['sampling_summary']['valid_samples']==1089
            assert g['array_order']=='values[y][x]'
            if keep is True:
                database=next(a['path']for a in result['artifacts']if a['kind']=='zrd')
                rays=await e.finish(await e.call('read_zrd',dict(request=dict(path=database,max_segments=5))))
                assert rays['rows']
            await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=3,y_start=5,width=7,height=4))
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/f'face_{face}_{keep}.png'))))
            records.append(dict(face=face,keep_zrd=keep,valid_count=sum(v is not None for row in g['values']for v in row),axis_errors=errors,grid={k:v for k,v in g.items()if k!='values'},artifacts=result['artifacts']))
            assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
        task=await e.call('run_analysis',dict(request=dict(kind='nsc_surface_sag',object_number=1,face_number=0,sampling='S_33x33',width=2)))
        while task['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='failed' and task['error']['code']=='NO_RESULT_DATA' and task['close_attempted']
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_surface_sag',object_number=1,face_number=1,sampling='S_33x33',width=2))))
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
        (e.folder/'numeric-probe.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    asyncio.run(execute('sag065_numeric',work))

@pytest.mark.zemax
def test_nsc_sag_cancellation_preserves_model():
    async def work(e):
        await setup(e,1)
        await update(e,[dict(object=1,object_type='StandardLens',material='N-BK7',data=dict(Radius1=50,Clear1=5,Clear2=5,Thickness=2,Radius2=0))])
        baseline=await e.call('get_nsc_objects',dict(request={}))
        task=await e.call('run_analysis',dict(request=dict(kind='nsc_surface_sag',object_number=1,face_number=1,sampling='S_1025x1025',width=2)))
        active=task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        import time
        deadline=time.monotonic()+90
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'cancelled','succeeded'} and task['close_attempted'],task
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_surface_sag',object_number=1,face_number=1,sampling='S_33x33',width=2))))
        (e.folder/'cancellation.json').write_text(json.dumps(dict(active=active,terminal=task['state'],closed=task['close_attempted'])),encoding='utf-8')
    asyncio.run(execute('sag065_cancel',work))
