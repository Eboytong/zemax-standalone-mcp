"""Disk history preserves request identity, data paging and uncertain execution."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.history import RequestJournal, write_json
from zemax_mcp.history_models import TaskHistory, HistoricalResult, RequestStatus
from zemax_mcp.errors import ZemaxError

SESSION='a'*32
TASK='b'*32

@pytest.fixture
def b(tmp_path):return Backend(Config(tmp_path,tmp_path/'runs'))

def result(b,version=0,state='succeeded'):
    data=dict(task=dict(task_id=TASK,kind='test',state=state,request_id='request1',created_at='2026-11-05T01:00:00Z'),context=dict(session_id=SESSION),artifacts=[],rows=[dict(i=i)for i in range(5)])
    if version:data['result_schema_version']=version
    write_json(b.config.output_dir/SESSION/(TASK+'.json'),data)
    return data

@pytest.mark.parametrize('model,payload',[
    (RequestStatus,dict(request_id='../bad')),(RequestStatus,dict(request_id='a/b')),
    (HistoricalResult,dict(session_id='bad',task_id=TASK)),
    (HistoricalResult,dict(session_id=SESSION,task_id=TASK,grid=0,width=1000,height=1000)),
    (HistoricalResult,dict(session_id=SESSION,task_id=TASK,grid=0,series=0)),
    (TaskHistory,dict(count=0)),(TaskHistory,dict(state='whatever')),
])
def test_history_request_boundaries(model,payload):
    with pytest.raises(ValidationError):model(**payload)

def test_legacy_discovery_and_paging_after_restart(b):
    result(b)
    history=b.list_task_history(TaskHistory())
    assert history['total']==1 and history['rows'][0]['origin']=='legacy_result'
    other=Backend(b.config)
    page=other.get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK,start=2,count=2))
    assert page['rows']==[dict(i=2),dict(i=3)]and page['next_start']==4 and page['history']['result_schema_version']==0
    assert other.tasks=={} and other.active is None

def test_current_tasks_override_disk_and_filter_by_request(b):
    result(b)
    b.tasks[TASK]=dict(task_id=TASK,kind='test',state='running',request_id='request1',context=dict(session_id=SESSION))
    page=b.list_task_history(TaskHistory(request_id='request1',state='running'))
    assert page['total']==1 and page['rows'][0]['origin']=='current_worker'and page['rows'][0]['execution_state']=='running'

def test_history_running_is_unknown_without_worker(b):
    result(b,state='running')
    row=b.list_task_history(TaskHistory())['rows'][0]
    assert row['task']['state']=='running'and row['execution_state']=='unknown_after_worker_exit'

def test_bad_json_is_reported_while_other_history_is_read(b):
    result(b)
    path=b.config.output_dir/SESSION/('c'*32+'.json');path.write_text('{bad',encoding='utf-8')
    value=b.list_task_history(TaskHistory())
    assert value['total']==1 and value['errors'][0]['code']=='RESULT_UNAVAILABLE'

def test_index_provides_final_cleanup_warnings(b):
    result(b,version=1)
    task=dict(task_id=TASK,kind='test',state='succeeded',context=dict(session_id=SESSION),result_path=str(b.config.output_dir/SESSION/(TASK+'.json')),close_attempted=True,cleanup_warnings=['close rejected'])
    b._record_task_history(task)
    page=b.get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK))
    assert page['task']['close_attempted']is True
    assert page['task']['cleanup_warnings']==['close rejected']
    assert b.list_task_history(TaskHistory())['rows'][0]['close_attempted']is True

def test_failed_task_minimal_result_survives_restart(b):
    task=dict(task_id=TASK,kind='test',state='failed',context=dict(session_id=SESSION),result=dict(completed=False),error=dict(code='native',message='failure'))
    b._record_task_history(task)
    assert task['result_path']
    page=Backend(b.config).get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK))
    assert page['completed']is False and page['task']['error']['message']=='failure'

def test_future_result_version_rejected(b):
    result(b,version=99)
    with pytest.raises(ZemaxError)as exc:b.get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK))
    assert exc.value.code=='UNSUPPORTED_RESULT_VERSION'

def test_curve_history_paging(b):
    data=result(b,version=1);data.pop('rows');data['series']=[dict(series=0,description='curve',labels=['v'],x_label='x',x=list(range(5)),y=[[v]for v in range(5)])]
    write_json(b.config.output_dir/SESSION/(TASK+'.json'),data)
    page=b.get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK,series=0,start=1,count=2))
    assert page['series'][0]['x']==[1,2]and page['series'][0]['y']==[[1],[2]]and page['next_start']==3

def test_grid_history_uses_shared_region_reader(b):
    data=result(b);data['grids']=[dict(values=[[1,2,3],[4,5,6]])]
    write_json(b.config.output_dir/SESSION/(TASK+'.json'),data)
    page=b.get_historical_result(HistoricalResult(session_id=SESSION,task_id=TASK,grid=0,x_start=1,y_start=0,width=1,height=2))
    assert page['grid']['values']==[[2],[5]]and page['history']['live_native_state']=='not_observed'

def test_request_journal_tracks_completed_launch_separately(b):
    journal=RequestJournal(b.config.output_dir,b.worker_instance_id)
    rec=journal.begin('r1','run_analysis',{'request':{'kind':'x'}})
    journal.finish(rec,dict(ok=True,data=dict(task_id=TASK,state='running'),context=dict(session_id=SESSION,model_revision=2)))
    receipt=b.get_request_status(RequestStatus(request_id='r1'))
    assert receipt['state']=='returned'and receipt['task_id']==TASK and receipt['model_revision']==2
    assert receipt['observed_execution_state']=='returned'

def test_unreturned_request_after_restart_remains_unknown(b):
    journal=RequestJournal(b.config.output_dir,'prior_worker');journal.begin('r2','update_surfaces',{'changes':[]})
    receipt=b.get_request_status(RequestStatus(request_id='r2'))
    assert receipt['observed_execution_state']=='unknown_after_worker_exit'and receipt['state']=='dispatching'

def test_request_failure_cause_is_durable(b):
    journal=RequestJournal(b.config.output_dir,b.worker_instance_id);rec=journal.begin('r3','bad',{})
    journal.finish(rec,dict(ok=False,error=dict(code='NATIVE_ERROR',message='original'),context={}))
    receipt=Backend(b.config).get_request_status(RequestStatus(request_id='r3'))
    assert receipt['ok']is False and receipt['error']['message']=='original'

def test_unsafe_private_request_id_not_written(b):
    assert RequestJournal(b.config.output_dir,'w').begin('../unsafe','x',{})is None

def test_invalid_index_is_reported(b):
    write_json(b.config.output_dir/SESSION/'_task_index'/(TASK+'.json'),dict(history_schema_version=1,session_id=SESSION,task={}))
    value=b.list_task_history(TaskHistory())
    assert value['total']==0 and value['errors'][0]['code']=='INVALID_RESULT_DATA'

def test_busy_request_status_reads_receipt_without_worker_queue(b,monkeypatch):
    import asyncio
    from zemax_mcp.bridge import Bridge
    monkeypatch.setenv('ZEMAX_OUTPUT_DIR',str(b.config.output_dir))
    RequestJournal(b.config.output_dir,'busy').begin('waiting','update_surfaces',{'changes':[]})
    bridge=Bridge();bridge.pending['waiting']=None
    value=asyncio.run(bridge.request('get_request_status',dict(request_id='waiting')))
    assert value['ok']and value['data']['state']=='dispatching'and bridge.process is None

def test_queued_request_status_does_not_claim_execution(b,monkeypatch):
    import asyncio
    from zemax_mcp.bridge import Bridge
    monkeypatch.setenv('ZEMAX_OUTPUT_DIR',str(b.config.output_dir))
    bridge=Bridge();bridge.pending['waiting']=None;bridge.inflight_metadata['waiting']=dict(command='update_surfaces')
    value=asyncio.run(bridge.request('get_request_status',dict(request_id='waiting')))
    assert value['ok']and value['data']['observed_execution_state']=='queued_or_dispatching'
