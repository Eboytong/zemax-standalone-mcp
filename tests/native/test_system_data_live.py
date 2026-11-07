import asyncio
import re
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_system_data_report_matches_controlled_settings():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(title='MCP_SystemData_081',aperture_value=12,adjust_index_to_environment=True,temperature_c=27)))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='system_data'))))
        lines=[r['text']for r in result['rows']]
        assert any('MCP_SystemData_081' in s for s in lines)
        for label,expected in [('系统孔径',12),('温度',27),('主波长',.55)]:
            line=next(s for s in lines if s.startswith(label))
            value=float(re.findall(r'[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?',line)[-1])
            e.check(label,value,expected,atol=1e-6,rtol=1e-6)
        task=result['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=task,start=2,count=5))
        assert page['rows']==result['rows'][2:7]
        status=await e.call('get_task_status',dict(task_id=task))
        assert status['close_attempted'] and status['state']=='succeeded'
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('systemdata081',work))
