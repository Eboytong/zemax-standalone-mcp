"""Configuration row identity and independent response through real stdio."""
import asyncio
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_universal_configuration_axes():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type=kind,parameters={'1':surface},cells=[dict(configuration=c,value=value)for c in [1,2]])
                      for kind,surface,value in [('THIC',1,2),('THIC',2,4),('CRVT',1,.05)]])))
        rows=(await e.call('get_configurations',dict(request={})))['rows']
        row1,row2,curvature=[r['operand']for r in rows[-3:]]
        await e.call('set_configuration',dict(configuration=2))
        saved=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before=[await e.call(name)for name in ['get_surfaces','get_system_settings']]
        configs=await e.call('get_configurations',dict(request={}))
        for configuration,parameter,row,low,high in [(2,'THIC',row1,2,4),(1,'THIC',row1,2,4),(2,'CRVT',curvature,.02,.04)]:
            q=dict(kind='universal_plot_1d',category='Configuration',configuration=configuration,
                operand_row=row,parameter=parameter,start=low,stop=high,samples=3,
                operand='CVVA'if parameter=='CRVT'else'TTHI',first_surface=1)
            if parameter=='THIC':q['last_surface']=1
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            curve=result['series'][0]
            for x,y in zip(curve['x'],curve['y']):e.check('Configuration selected-cell response',y[0],x if configuration==2 else 2)
            state=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert state['close_attempted']and not state.get('cleanup_warnings')
            assert state['settings']['configuration']==2
            assert state['settings']['selected_configuration']==configuration
            assert curve['x_unit']==('1/Millimeters'if parameter=='CRVT'else'Millimeters')
        q=dict(kind='universal_plot_2d',first_surface=1,last_surface=2,
            x=dict(category='Configuration',configuration=2,operand_row=row1,parameter='THIC',start=2,stop=6,samples=5),
            y=dict(category='Configuration',configuration=2,operand_row=row2,parameter='THIC',start=3,stop=5,samples=3))
        result=await e.finish(await e.call('run_analysis',dict(request=q)));g=result['grids'][0]
        assert (g['nx'],g['ny'])==(5,3)
        for y,row in zip(g['y'],g['values']):
            for x,value in zip(g['x'],row):e.check('Configuration 2D thickness sum',value,x+y)
        task=result['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'configuration.png'))))
        assert [await e.call(name)for name in ['get_surfaces','get_system_settings']]==before
        assert await e.call('get_configurations',dict(request={}))==configs
    asyncio.run(execute('universal231_configuration',work))
