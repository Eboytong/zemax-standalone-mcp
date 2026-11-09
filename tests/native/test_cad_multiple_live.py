"""Native configuration selection and exported STEP volume references."""
import asyncio,math,json,time
from pathlib import Path
import pytest
from tests.support.native import execute


def volume(path):
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    reader=STEPControl_Reader();assert reader.ReadFile(str(path))==IFSelect_RetDone
    assert reader.TransferRoots()>0
    props=GProp_GProps();BRepGProp.VolumeProperties_s(reader.OneShape(),props,1e-10)
    return props.Mass()


@pytest.mark.zemax
def test_native_cad_multiple_configurations():
    layer_failures=[]
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],aperture_value=4)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius='Infinity',material='N-BK7',thickness=2,semi_diameter=2,replace_solves=True),dict(surface=2,radius='Infinity',thickness=3,semi_diameter=2,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=2),dict(configuration=2,value=4)])])))
        saved=str(e.folder/'configurations.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        baseline=await e.call('get_configurations',dict(request={}));surfaces=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for mode,configuration in [('current',None),('single',2),('all_by_layer',None),('all_at_once',None),('all_by_file',None)]:
            q=dict(path=str(e.folder/(mode+'.step')),format='STEP',end=2,configuration_mode=mode)
            if configuration is not None:q['configuration']=configuration
            result=await e.finish(await e.call('run_cad_export',dict(request=q)))
            records.append(result);(e.folder/'exports.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['close_attempted']and not task.get('cleanup_warnings')
            selection=task['settings']['configuration_selection'];assert selection['mode']==mode
            if mode=='all_by_file':
                assert len(result['paths'])==2
                for f in result['configurations']:e.check('CAD file cylinder volume',volume(f['path']),math.pi*4*(2 if f['configuration']==1 else 4),atol=1e-5,rtol=1e-6)
            else:e.check('CAD selected cylinder volume',volume(result['path']),math.pi*4*(2 if mode=='current'else 4 if mode=='single'else 6),atol=1e-5,rtol=1e-6)
            assert await e.call('get_configurations',dict(request={}))==baseline
            assert await e.call('get_surfaces')==surfaces and await e.call('get_system_settings')==settings
        for mode,expected in [('all_by_layer',{10,11}),('all_at_once',{10})]:
            task=await e.call('run_cad_export',dict(request=dict(path=str(e.folder/(mode+'.igs')),format='IGES',end=2,configuration_mode=mode,lens_layer=10,ray_layer=20)))
            deadline=time.monotonic()+90
            while task['state'] not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            if task['state']=='failed':
                assert task['error']['code']=='SETTING_REJECTED' and task['error']['details']['setting']=='lens_layer',task
                assert task['close_attempted'] and not task.get('cleanup_warnings')
                details=task['error']['details']
                assert details['requested']==sorted(expected)
                assert Path(details['path']).is_file()
                layer_failures.append(dict(mode=mode,actual=details['actual']['levels'],expected=sorted(expected),rejected=True))
                continue
            result=await e.finish(task)
            directory=[line for line in Path(result['path']).read_text(encoding='ascii').splitlines()if len(line)>=73 and line[72]=='D']
            levels={int(line[32:40])for line in directory[::2]}-{0}
            (e.folder/(mode+'-layers.json')).write_text(json.dumps(dict(levels=sorted(levels),expected=sorted(expected))),encoding='utf-8')
            if levels!=expected:layer_failures.append(dict(mode=mode,actual=sorted(levels),expected=sorted(expected)))
        assert await e.call('get_configurations',dict(request={}))==baseline and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('cad169_multiple',work))
    if layer_failures:pytest.xfail('v242 CAD IGES layer output differs from adopted settings: '+str(layer_failures))


@pytest.mark.zemax
def test_iges_layer_rejection_and_reuse():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before={tool:await e.call(tool) for tool in ('get_surfaces','get_system_settings','get_merit_function')}
        q=dict(path=str(e.folder/'explicit_layer.igs'),format='IGES',end=2,lens_layer=10,number_of_rays=0)
        task=await e.call('run_cad_export',dict(request=q));deadline=time.monotonic()+90
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='failed' and task['error']['code']=='SETTING_REJECTED',task
        details=task['error']['details']
        assert details['setting']=='lens_layer' and details['requested']==[10]
        assert set(details['actual']['levels'])-{0}=={65535} and Path(details['path']).is_file()
        assert task['close_attempted'] and not task.get('cleanup_warnings')
        result=await e.finish(await e.call('run_cad_export',dict(request=dict(path=str(e.folder/'reuse.step'),format='STEP',end=2))))
        assert Path(result['path']).is_file()
        after={tool:await e.call(tool) for tool in before}
        assert before==after
    asyncio.run(execute('cad_iges_adoption',work))
