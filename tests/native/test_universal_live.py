import asyncio
import pytest
from tests.support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('parameter',['Thickness','Radius','Curvature'])
def test_universal_thickness_native(parameter):
    async def work(e):
        await e.model();before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        q=dict(parameter=parameter,kind='universal_plot_1d',surface=1,start=2,stop=6,samples=5,first_surface=1,last_surface=1)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('Universal TTHI',y[0],x if parameter=='Thickness'else 0)
        task=r['task']['task_id'];await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'universal.png'))))
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
    asyncio.run(execute('universal197_'+parameter,work))


@pytest.mark.zemax
@pytest.mark.parametrize('parameter',['Radius','Curvature'])
def test_universal_cvva_response(parameter):
    async def work(e):
        await e.model();before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        q=dict(kind='universal_plot_1d',surface=1,parameter=parameter,start=2,stop=4,samples=3,operand='CVVA',first_surface=1)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('CVVA independent reciprocal radius',y[0],1/x if parameter=='Radius'else x)
        assert r['series'][0]['y_unit']=='1/Millimeters'
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'cvva.png'))))
    asyncio.run(execute('universal200_cvva_'+parameter,work))
