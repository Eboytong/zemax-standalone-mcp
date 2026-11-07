import asyncio,json,time
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_zernike_field_matched_fit_references():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=20),dict(x=20,y=0),dict(x=0,y=-20),dict(x=-20,y=0)])))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved))
        records=[]
        for coefficient_type in ['Standard','Fringe','Annular']:
            obscuration=.2 if coefficient_type=='Annular'else 0
            single={}
            for field in [1,2,3,4,5]:
                single[field]=await e.finish(await e.call('run_analysis',dict(request=dict(kind='zernike_'+coefficient_type.lower(),field=field,wavelength=1,sampling='S_64x64',maximum_terms=6,obscuration=obscuration))))
            for direction,field in [('Plus_Y',2),('Plus_X',3),('Minus_Y',4),('Minus_X',5)]:
                request=dict(kind='zernike_coefficients_vs_field',coefficient_type=coefficient_type,coefficients=[4,5,6],sampling='S_64x64',field_density=5,field_scan=direction,obscuration=obscuration)
                scan=await e.finish(await e.call('run_analysis',dict(request=request)))
                records.append(dict(request=request,scan=scan,single=[single[1],single[field]]))
                (e.folder/'references.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                curve=scan['series'][0]
                assert curve['coefficient_terms']==[4,5,6] and len(curve['x'])==6
                e.check('field scan start',curve['x'][0],0)
                e.check('field scan endpoint',curve['x'][-1],-20 if direction.startswith('Minus')else 20)
                for at,ref in [(0,single[1]),(-1,single[field])]:
                    terms={r['term']:r['value']for r in ref['rows']}
                    for col,term in enumerate(curve['coefficient_terms']):
                        e.check('matched fit '+coefficient_type+direction+' Z'+str(term),curve['y'][at][col],terms[term],atol=1e-5,rtol=.01)
                task=scan['task']['task_id']
                page=await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=2))
                assert page['series'][0]['y']==curve['y'][1:3]
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/(coefficient_type+direction+'.png')))))
                assert (await e.call('get_task_status',dict(task_id=task)))['close_attempted']
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        await e.call('open_lens',dict(path=saved))
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        task=await e.call('run_analysis',dict(request=dict(kind='zernike_coefficients_vs_field',sampling='S_512x512',field_density=100)))
        running=task['state']=='running';task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+60
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
        (e.folder/'cancellation.json').write_text(json.dumps(dict(started_running=running,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='zernike_coefficients_vs_field'))))
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('zernike089_delivery',work))


@pytest.mark.zemax
def test_zernike_field_all_and_sparse_selection():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        records=[]
        for coefficient_type,terms in [('Fringe',[0]),('Standard',[4,6])]:
            r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='zernike_coefficients_vs_field',coefficient_type=coefficient_type,coefficients=terms,field_density=2))),timeout_seconds=180)
            records.append(r)
            (e.folder/'selection.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            actual=r['series'][0]['coefficient_terms']
            assert actual==list(range(1,38))if terms==[0]else actual==terms
            if terms==[0]:
                ref=await e.finish(await e.call('run_analysis',dict(request=dict(kind='zernike_fringe',field=1,wavelength=1,maximum_terms=37))))
                refs={row['term']:row['value']for row in ref['rows']}
                for col,term in enumerate(actual):e.check('all coefficients headerless mapping',r['series'][0]['y'][0][col],refs[term],atol=1e-5,rtol=.01)
    asyncio.run(execute('zernike089_selection',work))
