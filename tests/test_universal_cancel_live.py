"""Native Universal cancellation, source preservation and following-task reuse."""
import asyncio,time
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_universal_native_cancel_and_reuse():
    async def work(e):
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(lens)))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        revision=(await e.call('get_status'))['model_revision']
        for dimensions in [1,2]:
            target=dict(mode='operand',operand='RSRE',parameters=[128,1,0,.5])
            if dimensions==1:q=dict(kind='universal_plot_1d',category='System',parameter='Aperture',start=4,stop=8,samples=1001,target=target)
            else:q=dict(kind='universal_plot_2d',x=dict(category='System',parameter='Aperture',start=4,stop=8,samples=255),y=dict(surface=6,start=40,stop=45,samples=255),target=target)
            state=await e.call('run_analysis',dict(request=q));assert state['state']=='running',state
            task=state['task_id'];state=await e.call('cancel_task',dict(task_id=task));deadline=time.monotonic()+90
            while state['state']not in {'cancelled','failed','succeeded'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);state=await e.call('get_task_status',dict(task_id=task))
            assert state['state']=='cancelled'and state['cancel_requested'],state
            assert state['close_attempted']and not state.get('cleanup_warnings')
            result=await e.call('get_task_result',dict(task_id=task));assert result['completed']is False
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
            assert(await e.call('get_status'))['model_revision']==revision
            q=dict(kind='universal_plot_1d',surface=1,parameter='Radius',start=20,stop=40,samples=3,operand='CVVA',first_surface=1)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            for x,y in zip(result['series'][0]['x'],result['series'][0]['y']):e.check('Post-cancel CVVA reuse',y[0],1/x)
            assert await e.call('get_surfaces')==before
    asyncio.run(execute('universal239_cancel',work))
