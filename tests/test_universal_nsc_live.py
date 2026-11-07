"""Native pure-NSC six-position scans and non-square merit grid."""
import asyncio
import pytest
from support.native import execute


@pytest.mark.zemax
def test_universal_nsc_position_axes():
    async def work(e):
        await e.call('new_system',dict(mode='NonSequential'))
        await e.call('update_nsc_objects',dict(request=dict(changes=[dict(object=1,object_type='Rectangle',x=2,y=3,z=4)])))
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before=await e.call('get_nsc_objects',dict(request={}))
        settings=await e.call('get_system_settings')
        for parameter,operand in zip(['XPosition','YPosition','ZPosition','TiltX','TiltY','TiltZ'],['NPXV','NPYV','NPZV','NTXV','NTYV','NTZV']):
            q=dict(kind='universal_plot_1d',category='NSC',object=1,parameter=parameter,start=2,stop=4,samples=3,
                target=dict(mode='operand',operand=operand,parameters=[1,1,0]))
            r=await e.finish(await e.call('run_analysis',dict(request=q)));curve=r['series'][0]
            assert curve['x_unit']==curve['y_unit']==('degrees'if parameter.startswith('Tilt')else'Millimeters')
            for x,y in zip(curve['x'],curve['y']):e.check('NSC selected position/tilt identity '+parameter,y[0],x)
            state=await e.call('get_task_status',dict(task_id=r['task']['task_id']))
            assert state['close_attempted']and not state.get('cleanup_warnings')
        for number in [1,2]:
            q=dict(kind='universal_plot_1d',category='NSC',object=1,parameter='ObjectParameter',parameter_number=number,start=2,stop=4,samples=3,
                target=dict(mode='operand',operand='NPVA',parameters=[1,1,number]))
            r=await e.finish(await e.call('run_analysis',dict(request=q)));curve=r['series'][0]
            assert curve['x_unit']==curve['y_unit']=='Millimeters'
            for x,y in zip(curve['x'],curve['y']):e.check('NSC rectangle parameter identity',y[0],x)
        q=dict(kind='universal_plot_2d',x=dict(category='NSC',object=1,parameter='XPosition',start=2,stop=6,samples=5),
            y=dict(category='NSC',object=1,parameter='YPosition',start=3,stop=5,samples=3),target=dict(mode='operand',operand='NPXV',parameters=[1,1,0]))
        r=await e.finish(await e.call('run_analysis',dict(request=q)));g=r['grids'][0]
        assert(g['nx'],g['ny'])==(5,3)
        for row in g['values']:
            for x,v in zip(g['x'],row):e.check('NSC2D X position',v,x)
        q=dict(kind='universal_plot_2d',x=dict(category='NSC',object=1,parameter='ObjectParameter',parameter_number=1,start=2,stop=6,samples=5),
            y=dict(category='NSC',object=1,parameter='ObjectParameter',parameter_number=2,start=3,stop=5,samples=3),target=dict(mode='operand',operand='NPVA',parameters=[1,1,1]))
        r=await e.finish(await e.call('run_analysis',dict(request=q)));g=r['grids'][0]
        assert(g['nx'],g['ny'])==(5,3)and g['x_unit']==g['y_unit']==g['value_unit']=='Millimeters'
        for row in g['values']:
            for x,v in zip(g['x'],row):e.check('NSC2D rectangle parameter',v,x)
        task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'nsc-grid.png'))))
        assert await e.call('get_nsc_objects',dict(request={}))==before
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('universal238_nsc',work))
