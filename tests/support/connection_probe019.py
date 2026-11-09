from zemax_mcp.config import PROJECT_ROOT
"""Bounded, staged native probe with a separate evidence directory per attempt."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT=PROJECT_ROOT
sys.path.insert(0,str(ROOT/'src'))


def read_events(folder):
    path=folder/'stages.jsonl'
    if not path.is_file():return []
    events=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:continue
    return events


def child(folder):
    from zemax_mcp.native import NativeSession
    from zemax_mcp.config import Config
    from zemax_mcp.backend import Backend
    from zemax_mcp.errors import ZemaxError
    def observe(event):
        with (folder/'stages.jsonl').open('a',encoding='utf-8')as stream:
            stream.write(json.dumps(event,ensure_ascii=False)+'\n')
            stream.flush()
    s=NativeSession(stage_observer=observe)
    config=Config.from_env()
    backend=Backend(Config(config.install_dir,folder/'runs'),native=s)
    record=dict(closed=False,connected=False,install_dir=str(config.install_dir),
                request_sequence=['connect','new_system','get_system_settings','disconnect'],
                transport='in-process backend; real stdio acceptance follows successful startup',calls=[])
    try:
        for command in record['request_sequence'][:-1]:
            with s._stage('probe_'+command):
                response=backend.dispatch(command,{})
                record['calls'].append(dict(command=command,response=response))
                if not response['ok']:
                    error=response['error']
                    raise ZemaxError(error['code'],error['message'],**error.get('details',{}))
                if command=='connect':
                    record['connected']=True
                    record['version']=backend.version
                    record['license']=backend.license
        record['minimal_model_passed']=True
    except Exception as exc:
        record['error']=exc.as_dict()if isinstance(exc,ZemaxError)else NativeSession._error_record(exc)
    finally:
        try:
            s.disconnect()
            record['closed']=s.application is None
        except Exception as exc:
            record['close_error']=NativeSession._error_record(exc)
        record['observer_warnings']=s.observer_warnings
        record['stages']=s.stage_events
        record['status']='passed'if record.get('minimal_model_passed')and record['closed']else 'failed'
        (folder/'native.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if record['status']=='passed'else 1


def run(folder=None,startup_seconds=180,cleanup_seconds=15):
    if not 0<startup_seconds<=180 or not 0<cleanup_seconds<=15:
        raise ValueError('startup budget must be (0,180], cleanup budget (0,15] seconds')
    if folder is None:
        label=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
        folder=ROOT/'verification/development/BASE-04'/('connection-'+label)
    folder=Path(folder).resolve()
    folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    with (folder/'stdout.txt').open('w',encoding='utf-8')as out,(folder/'stderr.txt').open('w',encoding='utf-8')as err:
        process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--child','--output-dir',str(folder)],
            cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(child_pid=process.pid,startup_budget_seconds=startup_seconds,
                    cleanup_budget_seconds=cleanup_seconds,evidence_directory=str(folder))
        try:
            record['exit_code']=process.wait(timeout=startup_seconds)
            record['state']='passed'if record['exit_code']==0 else 'failed'
        except subprocess.TimeoutExpired:
            record['state']='initialization_timeout'
            deadline=time.monotonic()+cleanup_seconds
            if process.poll()is None:
                try:
                    stopped=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                        capture_output=True,text=True,encoding='oem',errors='replace',
                        timeout=max(.001,deadline-time.monotonic()),creationflags=subprocess.CREATE_NO_WINDOW)
                    record['owned_tree_stop']=dict(returncode=stopped.returncode,stdout=stopped.stdout,stderr=stopped.stderr)
                except subprocess.TimeoutExpired:
                    record['owned_tree_stop']=dict(state='cleanup_timeout')
            try:record['exit_code']=process.wait(timeout=max(.001,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:record['cleanup_pending']=True
        record['child_alive']=process.poll()is None
        record['elapsed_seconds']=time.monotonic()-start
    events=read_events(folder)
    completed=[e['stage']for e in events if e['event']=='completed']
    record['completed_stages']=completed
    record['last_event']=events[-1]if events else None
    pending={}
    for event in events:
        if event['event']=='started':pending[event['stage']]=event
        else:pending.pop(event['stage'],None)
    record['unfinished_stages']=list(pending)
    record['stdout_bytes']=(folder/'stdout.txt').stat().st_size
    record['stderr_bytes']=(folder/'stderr.txt').stat().st_size
    (folder/'supervisor.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True))
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--startup-seconds',type=float,default=180)
    parser.add_argument('--cleanup-seconds',type=float,default=15)
    parser.add_argument('--child',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.child:
        if args.output_dir is None:parser.error('child requires --output-dir')
        return child(args.output_dir)
    result=run(args.output_dir,args.startup_seconds,args.cleanup_seconds)
    return 0 if result['state']=='passed'and not result['child_alive']else 1


if __name__=='__main__':sys.exit(main())
