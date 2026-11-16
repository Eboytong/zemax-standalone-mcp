"""2026 R1 history round trip and both MCP tool disclosure modes."""
import asyncio
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('mode', ['full','compact'])
def test_2026r1_history_and_disclosure(mode, monkeypatch):
    monkeypatch.setenv('ZEMAX_TEST_TOOL_MODE',mode)
    async def work(e):
        tools=(await e.client.list_tools()).tools
        assert len(tools)==(107 if mode=='full' else 11)
        await e.call('search_capabilities',dict(query='光线追迹',limit=3))
        await e.model()
        task=await e.call('run_batch_ray_trace',dict(request=dict(rays=[dict(py=0)])))
        result=await e.finish(task)
        session_id=result['task']['context']['session_id']
        receipt=await e.call('get_request_status',dict(request=dict(request_id=task['request_id'])))
        assert receipt
        history=await e.call('list_task_history',dict(request=dict(session_id=session_id,count=50)))
        assert task['task_id'] in str(history)
        historical=await e.call('get_historical_result',dict(request=dict(session_id=session_id,task_id=task['task_id'])))
        assert historical
        await e.call('delete_surfaces',dict(at=1))
    asyncio.run(execute('history_modes_2026r1_'+mode,work))
