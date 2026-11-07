"""Explicit mixed NSC groups, crossed categories, source group restoration."""
import asyncio,math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_universal_mixed_nsc_groups():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=3))
        await e.call('update_surfaces',dict(changes=[dict(surface=i,surface_type='NonSequential',replace_solves=True)for i in [2,4]]))
        for group in [2,4]:
            await e.call('update_nsc_objects',dict(request=dict(nsc_surface=group,changes=[dict(object=1,object_type='Rectangle',x=group*10,y=3,z=4)])))
        await e.call('update_merit_function',dict(mode='replace',operands=[dict(type='NPXV',parameters={'2':group,'3':1,'4':0},target=0,weight=1)for group in [2,4]]))
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before={group:await e.call('get_nsc_objects',dict(request=dict(nsc_surface=group)))for group in [2,4]}
        surfaces=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        active=(await e.call('get_capabilities'))['active_nsc_surface'];revision=(await e.call('get_status'))['model_revision']
        for group in [2,4]:
            q=dict(kind='universal_plot_1d',category='NSC',nsc_surface=group,object=1,parameter='XPosition',start=2,stop=4,samples=3,
                target=dict(mode='operand',operand='NPXV',parameters=[group,1,0]))
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            for x,y in zip(r['series'][0]['x'],r['series'][0]['y']):e.check('Explicit NSC group position '+str(group),y[0],x)
            state=await e.call('get_task_status',dict(task_id=r['task']['task_id']))
            assert state['settings']['nsc_group']==group and state['settings']['category_index']==(3 if group==2 else 4)
            q=dict(kind='universal_plot_1d',category='NSC',nsc_surface=group,object=1,parameter='ObjectParameter',parameter_number=1,start=2,stop=4,samples=3,
                target=dict(mode='operand',operand='NPVA',parameters=[group,1,1]))
            r=await e.finish(await e.call('run_analysis',dict(request=q)));curve=r['series'][0]
            assert curve['x_unit']==curve['y_unit']=='Millimeters'
            for x,y in zip(curve['x'],curve['y']):e.check('Mixed NSC parameter '+str(group),y[0],x)
        q=dict(kind='universal_plot_2d',x=dict(category='NSC',nsc_surface=2,object=1,parameter='XPosition',start=2,stop=6,samples=5),
            y=dict(category='NSC',nsc_surface=4,object=1,parameter='XPosition',start=3,stop=5,samples=3),target=dict(mode='merit',line=0))
        r=await e.finish(await e.call('run_analysis',dict(request=q)));g=r['grids'][0]
        assert(g['nx'],g['ny'])==(5,3)
        for y,row in zip(g['y'],g['values']):
            for x,v in zip(g['x'],row):e.check('Crossed NSC group weighted merit',v,math.sqrt((x*x+y*y)/2))
        q=dict(kind='universal_plot_2d',x=dict(category='NSC',nsc_surface=4,object=1,parameter='XPosition',start=2,stop=6,samples=5),
            y=dict(surface=1,start=1,stop=3,samples=3),target=dict(mode='merit',line=0))
        r=await e.finish(await e.call('run_analysis',dict(request=q)));g=r['grids'][0]
        for row in g['values']:
            for x,v in zip(g['x'],row):e.check('NSC and Surface axes weighted merit',v,math.sqrt((20*20+x*x)/2))
        task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'mixed.png'))))
        for group in [2,4]:assert await e.call('get_nsc_objects',dict(request=dict(nsc_surface=group)))==before[group]
        assert await e.call('get_surfaces')==surfaces and await e.call('get_system_settings')==settings
        assert(await e.call('get_capabilities'))['active_nsc_surface']==active
        assert(await e.call('get_status'))['model_revision']==revision
    asyncio.run(execute('universal247_mixed',work))
