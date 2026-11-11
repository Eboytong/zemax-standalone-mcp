import asyncio,json
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_uniform_thermal_compensation_stdio():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,temperature_c=20,
            material_catalogs=['SCHOTT'],adjust_index_to_environment=True)))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius=50,thickness=3,material='N-BK7',semi_diameter=5,replace_solves=True),
            dict(surface=2,radius=-50,thickness=47.6,tce=100,semi_diameter=5,replace_solves=True)]))
        temperatures=[20,-20,60]
        operands=[dict(type='TEMP',cells=[dict(configuration=i,value=t) for i,t in enumerate(temperatures,1)])]
        for code,surface,value in [('CRVT',1,.02),('CRVT',2,-.02),('THIC',1,3),('THIC',2,47.6)]:
            operands.append(dict(type=code,parameters={1:surface},cells=[dict(configuration=1,value=value)]+
                [dict(configuration=i,solve=dict(mode='thermal_pickup',configuration=1)) for i in [2,3]]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True) for _ in range(2)])))
        await e.call('update_configurations',dict(request=dict(operands=operands)))
        source=await e.call('get_surfaces');configs=await e.call('get_configurations',dict(request={}))
        settings=await e.call('get_system_settings');revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='thermal_compensation',configurations=[1,2,3],compensation_surface=2,
            minimum_gap=40,maximum_gap=60,replace_compensation_solves=True,cycles='Fixed_10_Cycles')
        for request,expected in [(q|dict(replace_compensation_solves=False),'failed'),
                                 (q|dict(configurations=[1,2,9]),'failed'),(q,'cancelled')]:
            task=await e.call('run_analysis',dict(request=request))
            if expected=='cancelled':await e.call('cancel_task',dict(task_id=task['task_id']))
            for _ in range(1000):
                task=await e.call('get_task_status',dict(task_id=task['task_id']))
                if task['state'] in ['succeeded','failed','cancelled']:break
                await asyncio.sleep(.02)
            assert task['state']==expected,task
            result=await e.call('get_task_result',dict(task_id=task['task_id']))
            assert result['resources']['all_copies_closed']
            if expected=='failed':
                assert result['error']['code'] in ['SOLVE_PROTECTED','INDEX_OUT_OF_RANGE'],result
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        assert r['resources']['all_copies_closed']
        assert r['summary']['max_rms_after'] < r['summary']['max_rms_before']*.1,r['summary']
        for row,temp in zip(r['before'],temperatures):
            e.check('actual thermal configuration temperature',row['temperature_c'],temp)
            assert row['adjust_index_to_environment']
        # Independent paraxial thick-lens EFL using actual catalog index and thermally adopted radii.
        for state in r['after']:
            a,c=state['surfaces'];n=a['indices'][0];r1=a['radius'];r2=c['radius'];thickness=a['thickness']
            power=(n-1)*(1/r1-1/r2)+(n-1)**2*thickness/(n*r1*r2)
            e.check('thermal thick-lens EFL',state['effective_focal_length'],1/power,atol=1e-8,rtol=1e-6)
            scale=1+(state['temperature_c']-20)*7.1e-6
            # Native material CTE is read from the installed SCHOTT catalog.
            selected=False
            for line in (Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig',errors='replace').splitlines():
                if line.startswith('NM '):selected=line.split()[1]=='N-BK7'
                if selected and line.startswith('ED '):
                    scale=1+(state['temperature_c']-20)*float(line.split()[1])*1e-6;break
            e.check('heated lens front radius',r1,50*scale)
            e.check('heated lens center thickness',thickness,3*scale)
        assert await e.call('get_surfaces')==source
        assert await e.call('get_configurations',dict(request={}))==configs
        assert await e.call('get_system_settings')==settings
        assert (await e.call('get_status'))['model_revision']==revision
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=1,count=1));assert len(page['rows'])==1
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'thermal.png'))))
        (e.folder/'thermal-result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        # Reopen the saved native candidate and compare each temperature after persistence.
        await e.call('open_lens',dict(path=r['summary']['recommended_model']))
        reread=await e.finish(await e.call('run_analysis',dict(request=q|dict(optimize=False))))
        for old,new in zip(r['after'],reread['after']):
            for key in ['gap','rms_spot','rms_wavefront','effective_focal_length']:
                e.check('saved thermal candidate '+key,new[key],old[key])
    asyncio.run(execute('thermal_compensation',work))
