"""Native requested ACIS version compared with actual exported format header."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_native_acis_version_refusal_and_reuse():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');records=[]
        for fmt in ['SAT','SAB']:
            q=dict(path=str(e.folder/('explicit.'+fmt.lower())),format=fmt,end=2,file_version='V30')
            task=await e.call('run_cad_export',dict(request=q))
            for _ in range(1000):
                if task['state']in {'succeeded','failed','cancelled'}:break
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='failed'and task['error']['code']=='SETTING_REJECTED',task
            assert task['error']['details']['actual']['version_code']==500
            assert task['close_attempted']and not task.get('cleanup_warnings')
            records.append(task);(e.folder/'version-refusal.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            result=await e.finish(await e.call('run_cad_export',dict(request=dict(path=str(e.folder/('current.'+fmt.lower())),format=fmt,end=2,file_version='Current'))))
            assert result['file_metadata']['version_code']==500
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
    asyncio.run(execute('cad185_acis_readback',work))
