import asyncio
import pytest
from support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('operand',['TTHI','CVVA'])
def test_universal_two_dimensional_thickness(operand):
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        q=dict(kind='universal_plot_2d',x=dict(surface=1,start=2,stop=6,samples=5),y=dict(surface=2,start=3,stop=5,samples=3),first_surface=1,last_surface=2)
        if operand=='CVVA':q.update(operand='CVVA',last_surface=None);q['x'].update(parameter='Radius',start=20,stop=40)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        g=r['grids'][0];assert (g['nx'],g['ny'])==(5,3)
        for j,y in enumerate(g['y']):
            for i,x in enumerate(g['x']):e.check('Universal2D independent x+y',g['values'][j][i],x+y if operand=='TTHI'else 1/x)
        task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task));assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'universal2d.png'))))
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
    asyncio.run(execute('universal206_'+operand,work))
