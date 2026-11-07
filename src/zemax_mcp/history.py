"""Durable request receipts and versioned task history without native ownership."""
import json
import logging
import os
from pathlib import Path
import re
import uuid
from .data import clean, utc_now
from .errors import ZemaxError

ID=re.compile(r'^[0-9a-f]{32}$')
REQUEST_ID=re.compile(r'^[A-Za-z0-9_-]{1,128}$')
RESULT_VERSION=1

def write_json(path, value, create_parent=True):
    path=Path(path)
    if create_parent:path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)

def read_json(path):
    try:
        if path.stat().st_size>256*1024*1024:
            raise ZemaxError('RESULT_TOO_LARGE','结果文件超过当前256MiB读取上限。',path=str(path))
        value=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value,dict):raise ValueError('JSON object required')
        return value
    except ZemaxError:raise
    except (OSError,ValueError)as exc:
        raise ZemaxError('RESULT_UNAVAILABLE','历史记录无法读取。',path=str(path),reason=str(exc)) from exc

class RequestJournal:
    def __init__(self, root, worker):self.base=Path(root).resolve();self.root=self.base/'_requests';self.worker=worker
    def begin(self, request_id, command, arguments):
        if not isinstance(request_id,str)or not REQUEST_ID.fullmatch(request_id):
            return None
        if self.root.resolve().parent!=self.base:raise ZemaxError('INVALID_HISTORY_PATH','请求回执目录超出输出根目录。')
        record=dict(schema_version=1,request_id=request_id,command=command,arguments=arguments,
            worker_instance_id=self.worker,pid=os.getpid(),state='dispatching',started_at=utc_now())
        write_json(self.root/(request_id+'.json'),record)
        return record
    def finish(self, record, response):
        if record is None:return
        context=response.get('context',{})
        data=response.get('data')or{}
        task_id=data.get('task_id')if isinstance(data,dict)else None
        if task_id is None and isinstance(data,dict):task_id=data.get('task',{}).get('task_id')
        record.update(state='returned',finished_at=utc_now(),ok=response.get('ok'),error=response.get('error'),
            session_id=context.get('session_id'),model_revision=context.get('model_revision'),task_id=task_id,
            artifacts=response.get('artifacts',[]))
        write_json(self.root/(record['request_id']+'.json'),record)

class HistoryMixin:
    def _history_root(self):return Path(self.config.output_dir).resolve()

    def _history_session(self, session_id):
        if not ID.fullmatch(str(session_id)):raise ZemaxError('INVALID_ARGUMENT','会话编号必须为32位小写十六进制。')
        root=self._history_root();folder=(root/session_id).resolve()
        if folder.parent!=root:raise ZemaxError('INVALID_HISTORY_PATH','历史会话目录超出配置输出根目录。')
        return folder

    def _record_task_history(self, task):
        session=task.get('context',{}).get('session_id')or getattr(self,'session_id',None)
        if not session or not ID.fullmatch(str(session))or not ID.fullmatch(str(task.get('task_id',''))):return
        try:
            folder=self._history_session(session)
            result_path=task.get('result_path')
            if not result_path and task.get('state')in ('failed','cancelled')and isinstance(task.get('result'),dict):
                path=folder/(task['task_id']+'.json')
                result={**task['result'],'result_schema_version':RESULT_VERSION,'task':self._task_view(task),'context':task.get('context',{}),'artifacts':[]}
                write_json(path,result);task['result_path']=str(path);result_path=str(path)
            record=dict(history_schema_version=1,result_schema_version=RESULT_VERSION,task=self._task_view(task),
                session_id=session,result_path=result_path,close_attempted=task.get('close_attempted',False),
                cleanup_warnings=task.get('cleanup_warnings',[]),recorded_at=utc_now())
            index_path=(folder/'_task_index'/(task['task_id']+'.json')).resolve()
            if not index_path.is_relative_to(self._history_root()):raise ZemaxError('INVALID_HISTORY_PATH','历史索引目录超出输出根目录。')
            write_json(index_path,record)
        except Exception as exc:
            task.setdefault('history_warnings',[]).append(str(exc))
            logging.getLogger(__name__).warning('Task history write failed: %s',exc)

    def _disk_history(self, session_id=None):
        root=self._history_root();errors=[];records=[]
        folders=[self._history_session(session_id)]if session_id else sorted((p for p in root.iterdir()if p.is_dir()and ID.fullmatch(p.name)),key=lambda p:p.name)if root.exists()else []
        for directory in folders:
            try:folder=self._history_session(directory.name)
            except ZemaxError as exc:errors.append(exc.as_dict());continue
            indexed=set()
            for path in sorted((folder/'_task_index').glob('*.json')):
                if not ID.fullmatch(path.stem):continue
                try:
                    if path.resolve().parent!=(folder/'_task_index').resolve() or not path.resolve().is_relative_to(root):raise ZemaxError('INVALID_HISTORY_PATH','历史索引路径超出根目录。')
                    record=read_json(path)
                    if record.get('history_schema_version')!=1:raise ZemaxError('UNSUPPORTED_HISTORY_VERSION','历史索引版本不支持。',path=str(path))
                    if record.get('session_id')!=folder.name or not isinstance(record.get('task'),dict) or record['task'].get('task_id')!=path.stem:raise ZemaxError('INVALID_RESULT_DATA','历史索引缺少有效任务身份。',path=str(path))
                    record['origin']='historical';records.append(record);indexed.add(path.stem)
                except ZemaxError as exc:errors.append(exc.as_dict())
            for path in sorted(folder.glob('*.json')):
                if not ID.fullmatch(path.stem)or path.stem in indexed:continue
                try:
                    if path.resolve().parent!=folder:raise ZemaxError('INVALID_HISTORY_PATH','历史结果路径超出会话目录。')
                    result=read_json(path)
                    task=result.get('task')
                    if not isinstance(task,dict)or task.get('task_id')!=path.stem:continue
                    records.append(dict(history_schema_version=0,result_schema_version=result.get('result_schema_version',0),task=task,session_id=folder.name,result_path=str(path),origin='legacy_result',close_attempted=None,cleanup_warnings=[],recorded_at=task.get('finished_at',task.get('created_at'))))
                except ZemaxError as exc:errors.append(exc.as_dict())
        return records,errors

    def list_task_history(self, req):
        records,errors=self._disk_history(req.session_id)
        current={}
        for task_id,task in self.tasks.items():
            session=task.get('context',{}).get('session_id')or getattr(self,'session_id',None)
            current[(session,task_id)]=dict(session_id=session,task=self._task_view(task),origin='current_worker',result_path=task.get('result_path'))
        combined={(r['session_id'],r['task']['task_id']):r for r in records}
        combined.update(current)
        rows=[]
        for record in combined.values():
            task=record['task']
            if req.session_id and record['session_id']!=req.session_id:continue
            if req.request_id and task.get('request_id')!=req.request_id:continue
            if req.kind and task.get('kind')!=req.kind:continue
            if req.state and task.get('state')!=req.state:continue
            view={**record,'execution_state':task.get('state')if record['origin']=='current_worker'or task.get('state')in ('succeeded','failed','cancelled')else 'unknown_after_worker_exit'}
            rows.append(view)
        rows.sort(key=lambda r:(r['task'].get('created_at',''),r['task']['task_id']),reverse=True)
        end=min(req.start+req.count,len(rows))
        return dict(rows=rows[req.start:end],total=len(rows),next_start=end if end<len(rows)else None,errors=errors,history_root=str(self._history_root()))

    def get_historical_result(self, req):
        if req.grid is not None and req.width*req.height>10000:raise ZemaxError('INVALID_ARGUMENT','网格区域每次最多10000个值。')
        folder=self._history_session(req.session_id)
        path=(folder/(req.task_id+'.json')).resolve()
        if path.parent!=folder:raise ZemaxError('INVALID_HISTORY_PATH','历史结果超出会话目录。')
        result=read_json(path)
        if result.get('task',{}).get('task_id')!=req.task_id:raise ZemaxError('INVALID_RESULT_DATA','历史结果任务编号不匹配。')
        version=result.get('result_schema_version',0)
        if version not in (0,RESULT_VERSION):raise ZemaxError('UNSUPPORTED_RESULT_VERSION','历史结果版本暂不支持。',actual=version,supported=[0,RESULT_VERSION])
        index_path=folder/'_task_index'/(req.task_id+'.json')
        if index_path.is_file():
            if not index_path.resolve().is_relative_to(self._history_root()):raise ZemaxError('INVALID_HISTORY_PATH','历史索引路径超出配置根目录。')
            record=read_json(index_path)
            result['task']=record['task']
        result.update(history=dict(origin='disk',session_id=req.session_id,live_native_state='not_observed',result_schema_version=version))
        if req.series is not None:
            series=result.get('series',[])
            if req.series>=len(series):raise ZemaxError('INDEX_OUT_OF_RANGE','历史曲线编号越界。')
            item=series[req.series];end=min(req.start+req.count,len(item['x']))
            return {**{k:result[k]for k in ('task','context','artifacts','history')if k in result},'series':[{**item,'x':item['x'][req.start:end],'y':item['y'][req.start:end]}], 'total':len(item['x']), 'next_start':end if end<len(item['x'])else None}

        return self._page_task_result(result,req)

    def get_request_status(self, req):
        path=(self._history_root()/'_requests'/(req.request_id+'.json')).resolve()
        if path.parent!=(self._history_root()/'_requests').resolve() or not path.is_relative_to(self._history_root()):raise ZemaxError('INVALID_HISTORY_PATH','请求回执路径无效。')
        record=read_json(path)
        if record.get('request_id')!=req.request_id:raise ZemaxError('INVALID_RESULT_DATA','回执请求编号不匹配。')
        state=record.get('state')
        if state not in ('dispatching','returned'):raise ZemaxError('INVALID_RESULT_DATA','请求回执状态无效。',actual=state)
        if state=='dispatching'and record.get('worker_instance_id')!=getattr(self,'worker_instance_id',None):state='unknown_after_worker_exit'
        record['observed_execution_state']=state
        if record.get('task_id')in self.tasks:record['task']=self._task_view(self.tasks[record['task_id']])
        return record
