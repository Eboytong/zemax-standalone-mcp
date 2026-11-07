"""Universal operands and merit targets with independent geometric references."""
import asyncio
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_universal_operand_and_merit_targets():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=2,semi_diameter=10,replace_solves=True),dict(surface=2,thickness=4,semi_diameter=10,replace_solves=True)]))
        await e.call('update_merit_function',dict(mode='replace',operands=[dict(type='TTHI',parameters={'2':1,'3':2},target=1,weight=1)]))
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before=[await e.call(name)for name in ['get_surfaces','get_system_settings','get_merit_function']]
        target=dict(mode='operand',operand='REAY',parameters=[1,1,0,0,0,.5])
        q=dict(kind='universal_plot_1d',category='System',parameter='Aperture',start=4,stop=8,samples=3,target=target)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert r['series'][0]['y_unit']=='Millimeters'
        for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('REAY plane pupil height aperture/4',y[0],x/4)
        q=dict(kind='universal_plot_2d',x=dict(category='System',parameter='Aperture',start=4,stop=8,samples=5),
            y=dict(category='System',parameter='XField',selection=1,start=-1,stop=1,samples=3),target=target)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        g=r['grids'][0];assert(g['nx'],g['ny'])==(5,3)
        for row in g['values']:
            for x,v in zip(g['x'],row):e.check('REAY grid plane pupil height aperture/4',v,x/4)
        for dimensions in [1,2]:
            for line in [0,1]:
                target=dict(mode='merit',line=line)
                if dimensions==1:q=dict(kind='universal_plot_1d',surface=1,start=2,stop=4,samples=3,target=target)
                else:q=dict(kind='universal_plot_2d',x=dict(surface=1,start=2,stop=6,samples=5),y=dict(surface=2,start=3,stop=5,samples=3),target=target)
                r=await e.finish(await e.call('run_analysis',dict(request=q)))
                if dimensions==1:
                    for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('Merit scalar selected line or weighted residual',y[0],x+4-(1 if line==0 else 0))
                else:
                    g=r['grids'][0]
                    for y,row in zip(g['y'],g['values']):
                        for x,v in zip(g['x'],row):e.check('Merit grid selected line or weighted residual',v,x+y-(1 if line==0 else 0))
                state=await e.call('get_task_status',dict(task_id=r['task']['task_id']))
                assert state['close_attempted']and not state.get('cleanup_warnings')
        task=r['task']['task_id']
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'merit.png'))))
        after=[await e.call(name)for name in ['get_surfaces','get_system_settings','get_merit_function']]
        for merit in [before[2],after[2]]:
            for row in merit['operands']:
                row.pop('value');row.pop('contribution')
        assert before==after
    asyncio.run(execute('universal235_targets',work))
