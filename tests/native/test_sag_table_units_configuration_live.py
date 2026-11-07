"""SagTable minimum-volume identity across lens units and active configurations."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('unit,scale', [('Millimeters',1.),('Centimeters',.1)])
def test_sag_table_lens_units_and_current_configuration(unit, scale):
    async def work(e):
        conditions=dict(input_source='owned EvenAspheric parabola, two curvature configurations',
            unit=unit, length_scale=scale, configurations=[1,2],
            reference='z=y^2/(2R), MinimumVolume sphere touches vertex and edge',
            row_tolerance='1e-8 lens units +1e-6*reference',
            slope_tolerance='1e-8 +1e-6*reference',
            state_checks='surface cells/solves, system settings, MCE, MFE, model revision',
            expected_changes='only explicit configuration selection; analysis leaves selected state unchanged')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(lens_units=unit)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',
            radius=40*scale, conic=-1,semi_diameter=5*scale,thickness=20*scale,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='CRVT',parameters={'1':1},cells=[
                dict(configuration=1,value=1/(40*scale)),dict(configuration=2,value=1/(60*scale))])])))
        records=[]
        for configuration in [1,2]:
            await e.call('set_configuration',dict(configuration=configuration))
            baseline={name:await e.call(name,args) for name,args in [
                ('get_surfaces',{}),('get_system_settings',{}),('get_merit_function',{}),
                ('get_configurations',dict(request={}))]}
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,samples=11))))
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['state']=='succeeded' and not task.get('cleanup_warnings')
            assert result['units']['length']==unit and result['units']['volume']==unit+'^3'
            assert result['actual_settings']['configuration']==configuration
            assert result['context']['configuration']==configuration
            e.check('MCE full precision radius projection',
                baseline['get_surfaces']['surfaces'][1]['cells']['radius']['value'],
                (40 if configuration==1 else 60)*scale,atol=1e-12,rtol=1e-12)
            for name,before in baseline.items():
                assert await e.call(name,dict(request={})if name=='get_configurations'else{})==before
            records.append(dict(configuration=configuration,result=result,task_status=task,
                preserved=['surface cells/solves','system settings','merit function','configurations']))
        path=str(e.folder/'two-configurations.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,samples=11))))
        assert reloaded['actual_settings']['configuration']==2
        records.append(dict(configuration=2,reloaded=True,result=reloaded))
        (e.folder/'unit-configurations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        # Finish the native lifecycle before comparing independently calculated numbers.
        await e.call('disconnect')
        for record in records:
            result=record['result'];R=(40 if record['configuration']==1 else 60)*scale
            edge=5*scale;edge_sag=edge**2/(2*R)
            radius=(edge**2+edge_sag**2)/(2*edge_sag)
            e.check('BFS analytic radius',result['summary']['radius'],radius,atol=1e-8,rtol=1e-6)
            for row in result['rows']:
                y=row['y'];root=math.sqrt(radius**2-y**2)
                expected=dict(sag=y*y/(2*R),slope=y/R,bfs_sag=y*y/(radius+root),bfs_slope=y/root)
                for key,value in expected.items():
                    e.check(f'{unit} config{record["configuration"]} {key} y={y}',row[key],value,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('sag537_'+unit,work))


@pytest.mark.zemax
def test_sag_table_composite_uses_summed_surface():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            input_source='Owned coaxial zero-thickness EvenAspheric addon/base: .001*r^2+.002*r^2',
            reference='z=.003*r^2; minimum-volume sphere through vertex and edge',
            row_atol=1e-8,row_rtol=1e-6,summary_atol=1e-6,summary_rtol=1e-5),indent=2),encoding='utf-8')
        await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,surface_type='EvenAspheric',radius='Infinity',thickness=0,
                semi_diameter=5,parameters={'1':.001},replace_solves=True),
            dict(surface=2,surface_type='EvenAspheric',radius='Infinity',thickness=10,
                semi_diameter=5,parameters={'1':.002},replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,composite=dict(is_composite_surface=True))]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=2,samples=11))))
        task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert task['state']=='succeeded'and not task.get('cleanup_warnings')
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        path=str(e.folder/'composite.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=2,samples=11))))
        assert reloaded['summary']==result['summary']and reloaded['rows']==result['rows']
        (e.folder/'composite.json').write_text(json.dumps(dict(result=result,reloaded=reloaded,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        a=.003;edge=5.;edge_sag=a*edge**2;radius=(edge**2+edge_sag**2)/(2*edge_sag)
        e.check('summed parabola BFS radius',result['summary']['radius'],radius,atol=1e-8,rtol=1e-6)
        for row in result['rows']:
            y=row['y'];root=math.sqrt(radius**2-y*y)
            for key,value in dict(sag=a*y*y,slope=2*a*y,bfs_sag=y*y/(radius+root),bfs_slope=y/root).items():
                e.check('summed parabola '+key,row[key],value,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('sag541_composite',work))
