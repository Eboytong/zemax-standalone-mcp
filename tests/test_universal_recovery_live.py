"""Native result rejection closes both adapters and leaves the source reusable."""
import asyncio,time
import pytest
from support.native import execute


@pytest.mark.zemax
def test_universal_native_result_failure_and_reuse():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');revision=(await e.call('get_status'))['model_revision']
        for dimensions in [1,2]:
            if dimensions==1:q=dict(kind='universal_plot_1d',surface=1,start=2,stop=4,samples=3,target=dict(mode='operand',operand='BLNK'))
            else:q=dict(kind='universal_plot_2d',x=dict(surface=1,start=2,stop=6,samples=5),y=dict(surface=2,start=3,stop=5,samples=3),target=dict(mode='operand',operand='BLNK'))
            state=await e.call('run_analysis',dict(request=q));task=state['task_id'];deadline=time.monotonic()+90
            while state['state']not in {'failed','cancelled','succeeded'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);state=await e.call('get_task_status',dict(task_id=task))
            assert state['state']=='failed'and state['error']['code']=='SETTING_REJECTED',state
            assert state['close_attempted']and not state.get('cleanup_warnings')
            result=await e.call('get_task_result',dict(task_id=task));assert result['completed']is False
            assert state['error']['details']['native_text_path']
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
            current=await e.call('get_status');assert current['active_task']is None and not current['requires_reconnect']and current['model_revision']==revision
            q=dict(kind='universal_plot_1d',surface=1,parameter='Radius',start=20,stop=40,samples=3,operand='CVVA',first_surface=1)
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('Post-native-failure CVVA reuse',y[0],1/x)
        assert await e.call('get_surfaces')==before
    asyncio.run(execute('universal259_recovery',work))
