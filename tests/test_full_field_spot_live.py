import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_full_field_spot_native_outlet_and_model_preservation():
    async def work(e):
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(sample)))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for field,wave,reference,exaggerate in [(1,1,'Centroid',1),(0,0,'Centroid',1),(1,1,'ChiefRay',3)]:
            q=dict(kind='full_field_spot',field=field,wavelength=wave,reference=reference,exaggerate=exaggerate)
            task=await e.call('run_analysis',dict(request=q))
            while task['state']not in {'succeeded','failed','cancelled'}:
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            if task['state']=='failed':
                assert task['error']['code']=='RESULT_UNAVAILABLE' and task['close_attempted'],task
                records.append(dict(validation='outlet limitation reproduced; numerical acceptance remains open',task=task))
                assert await e.call('get_surfaces',dict(request={}))==baseline
                continue
            result=await e.finish(task)
            assert result['rows']
            records.append(result)
            standard=await e.finish(await e.call('run_spot_analysis',dict(field=field,wavelength=wave,reference=reference,pattern='Hexapolar',ray_density=6)))
            for full,ref in zip(result['metrics'],standard['metrics']):
                for key in ['rms_radius','geo_radius']:
                    e.check('full field vs standard '+key,full[key],ref[key],atol=1e-6,rtol=1e-6)
            assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
            page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=2,count=3))
            assert page['rows']==result['rows'][2:5]
        assert await e.call('get_surfaces',dict(request={}))==baseline
        (e.folder/'reference.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('full_field074',work))
