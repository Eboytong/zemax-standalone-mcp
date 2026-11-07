import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_system_check_native_report_and_preservation():
    async def work(e):
        for sample in [False,True]:
            if sample:
                await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
            else:
                await e.call('new_system')
            before=await e.call('get_system_settings')
            surfaces=await e.call('get_surfaces')
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='system_check'))))
            assert result['rows'] and result['analysis_kind']=='system_check'
            if not sample:
                assert any('系统孔径是零' in r['text'] for r in result['rows'])
            task=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=task,start=1,count=3))
            assert page['rows']==result['rows'][1:4]
            status=await e.call('get_task_status',dict(task_id=task))
            assert status['state']=='succeeded' and status['close_attempted']
            assert await e.call('get_system_settings')==before
            assert await e.call('get_surfaces')==surfaces
            e.checks.append(dict(sample=sample,rows=len(result['rows']),closed=status['close_attempted']))
    asyncio.run(execute('systemcheck080',work))
