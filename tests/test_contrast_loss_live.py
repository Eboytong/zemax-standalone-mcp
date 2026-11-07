"""Native Contrast Loss output identities and settings combinations."""
import asyncio
import json
from pathlib import Path

import pytest
from support.native import execute


@pytest.mark.zemax
def test_contrast_loss_native_outlets():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for patch in [dict(frequency=0),dict(frequency=50),dict(frequency=50,normalize=False,show_opd=True)]:
            q=dict(kind='contrast_loss',sampling='S_11x11')|patch
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            records.append(dict(request=q,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('contrast_loss311',work))
