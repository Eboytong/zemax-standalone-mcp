"""Matrix native result contract discovery; empty outlets remain unaccepted."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_matrix_spot_native_outlet_probe():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)])))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces');records=[]
        for kind,color in [('configuration_matrix_spot','Config'),('matrix_spot','Waves')]:
            task=await e.call('run_analysis',dict(request=dict(kind=kind,color_rays_by=color)))
            while task['state']not in {'succeeded','failed','cancelled'}:
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['close_attempted']
            if task['state']=='failed':
                assert task['error']['code']=='EXPORT_FAILED',task
                records.append(dict(kind=kind,status='output limitation reproduced; numerical acceptance open',task=task))
            else:
                records.append(await e.finish(task))
            assert await e.call('get_system_settings')==baseline
            assert await e.call('get_surfaces')==surfaces
        (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('matrix088_outlets',work))
