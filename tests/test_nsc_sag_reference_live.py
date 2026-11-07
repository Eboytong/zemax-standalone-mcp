"""Native object-face sag with controlled plane/sphere and explicit output evidence."""
import asyncio,json
import pytest
from support.native import execute
from support.nsc import setup,update

@pytest.mark.zemax
def test_nsc_plane_sphere_sag_probe():
    async def work(e):
        await setup(e,1)
        records=[]
        for kind,data in [('StandardLens',dict(Radius1=50,Clear1=5,Clear2=5,Thickness=2,Radius2=0)),('RectangularVolume',dict(X1HalfWidth=5,Y1HalfWidth=5,X2HalfWidth=5,Y2HalfWidth=5,ZLength=2))]:
            await update(e,[dict(object=1,object_type=kind,material='N-BK7',data=data)])
            for face in [0,1,2]:
                task=await e.call('run_analysis',dict(request=dict(kind='nsc_surface_sag',object_number=1,face_number=face,sampling='S_33x33',width=4,show_as='FalseColor')),okay=False)
                if task.get('ok')is False:records.append(dict(object_type=kind,face=face,error=task));continue
                import time
                deadline=time.monotonic()+90
                while task['state']not in {'succeeded','failed','cancelled'}:
                    assert time.monotonic()<deadline
                    await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
                result=await e.call('get_task_result',dict(task_id=task['task_id']))
                records.append(dict(object_type=kind,face=face,state=task['state'],closed=task.get('close_attempted'),result=result))
        (e.folder/'sag-probe.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('nsc_sag065',work))
