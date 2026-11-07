"""Real stdio history survives worker restarts without starting native OpticStudio."""
import asyncio
from pathlib import Path
import sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from zemax_mcp.history import write_json, RequestJournal

SESSION='a'*32
TASK='b'*32

def test_history_across_stdio_restart(tmp_path):
    async def work():
        root=tmp_path/'runs'
        write_json(root/SESSION/(TASK+'.json'),dict(result_schema_version=1,task=dict(task_id=TASK,kind='history_fixture',state='succeeded',created_at='2026-11-05T00:00:00Z',request_id='seed'),context=dict(session_id=SESSION),artifacts=[],rows=[dict(i=i)for i in range(10)]))
        RequestJournal(root,'prior_worker').begin('interrupted','update_surfaces',{'changes':[]})
        params=StdioServerParameters(command=sys.executable,args=['-B','-m','zemax_mcp'],cwd=PROJECT_ROOT,env={'PYTHONUTF8':'1','PYTHONPATH':str(PROJECT_ROOT/'src'),'ZEMAX_OUTPUT_DIR':str(root)})
        request_id=None
        for generation in range(2):
            async with Client(params,read_timeout_seconds=45)as client:
                caps=(await client.call_tool('get_capabilities',{})).structured_content
                assert caps['ok']and caps['context']['request_id']
                if request_id is None:request_id=caps['context']['request_id']
                response=(await client.call_tool('get_request_status',dict(request=dict(request_id=request_id)))).structured_content
                assert response['ok']and response['data']['state']=='returned'and response['data']['command']=='get_capabilities'
                history=(await client.call_tool('list_task_history',dict(request=dict(session_id=SESSION)))).structured_content
                assert history['ok']and history['data']['total']==1 and history['data']['rows'][0]['task']['task_id']==TASK
                page=(await client.call_tool('get_historical_result',dict(request=dict(session_id=SESSION,task_id=TASK,start=3,count=2)))).structured_content
                assert page['ok']and page['data']['rows']==[dict(i=3),dict(i=4)]and page['data']['next_start']==5
                unknown=(await client.call_tool('get_request_status',dict(request=dict(request_id='interrupted')))).structured_content
                assert unknown['ok']and unknown['data']['observed_execution_state']=='unknown_after_worker_exit'
                status=(await client.call_tool('get_status',{})).structured_content
                assert status['ok']and status['data']['connected']is False
    asyncio.run(work())
