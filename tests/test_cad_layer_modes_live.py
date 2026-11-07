"""Separate solid/surface IGES writers in configuration-layer diagnosis."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_cad_iges_solid_surface_layer_diagnostic():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],aperture_value=4)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius='Infinity',material='N-BK7',thickness=2,semi_diameter=2,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=3,semi_diameter=2,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=2),dict(configuration=2,value=4)])])))
        path=str(e.folder/'before.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        before=dict(surfaces=await e.call('get_surfaces'),settings=await e.call('get_system_settings'),
            configurations=await e.call('get_configurations',dict(request={})),merit=await e.call('get_merit_function'))
        record=dict(hypothesis='IGES solid-body writer may use fixed65535 while surface writer adopts LensLayer and configuration layers',
            factor='surfaces_as_solids',expected=dict(all_by_layer=[10,11],all_at_once=[10]),cases=[])
        for solid in [True,False]:
            for mode in ['all_by_layer','all_at_once']:
                q=dict(path=str(e.folder/(str(solid)+'_'+mode+'.igs')),format='IGES',end=2,
                    surfaces_as_solids=solid,configuration_mode=mode,lens_layer=10,ray_layer=20)
                result=await e.finish(await e.call('run_cad_export',dict(request=q)))
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded'and task['close_attempted']and not task.get('cleanup_warnings')
                lines=[line for line in Path(result['path']).read_text(encoding='ascii').splitlines()if len(line)>=73 and line[72]=='D']
                assert len(lines)%2==0 and lines
                entries=[dict(entity_type=int(line[:8]),level=int(line[32:40]))for line in lines[::2]]
                levels=sorted({p['level']for p in entries}-{0})
                record['cases'].append(dict(request=q,actual_settings=task['settings'],entries=entries,levels=levels,
                    expected=record['expected'][mode],layer_adoption=levels==record['expected'][mode],task=task))
                (e.folder/'layers.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
                assert await e.call('get_surfaces')==before['surfaces'] and await e.call('get_system_settings')==before['settings']
                assert await e.call('get_configurations',dict(request={}))==before['configurations'] and await e.call('get_merit_function')==before['merit']
        path=str(e.folder/'after.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        assert await e.call('get_surfaces')==before['surfaces'] and await e.call('get_system_settings')==before['settings']
        assert await e.call('get_configurations',dict(request={}))==before['configurations'] and await e.call('get_merit_function')==before['merit']
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('cad585_solid_surface_layers',guarded))
