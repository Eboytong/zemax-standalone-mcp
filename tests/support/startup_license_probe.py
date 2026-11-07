"""Correlate a completed startup attempt with the local licensing debug log."""
import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re

STAMP = re.compile(r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+(\S+)')
PID = re.compile(r'\b(\d+):ANSYS OPTICSTUDIO:')
TAIL_BYTES = 256 * 1024


def owned_pids(supervisor):
    result={int(supervisor['child_pid'])}
    stop=supervisor.get('owned_tree_stop',{})
    if stop.get('returncode') == 0:
        for line in stop.get('stdout','').splitlines():
            match=re.search(r'\bPID\s+(\d+)',line)
            if match:result.add(int(match.group(1)))
    return result


def correlate(text, pids, start, end):
    """The native log timestamps are local wall-clock times, to second precision."""
    events=[]
    current=None
    for line in text.splitlines():
        stamp=STAMP.match(line)
        if stamp:
            current=None
            when=datetime.strptime(stamp.group(1),'%Y/%m/%d %H:%M:%S')
            pid=PID.search(line)
            if pid and int(pid.group(1)) in pids and start <= when <= end:
                current=dict(timestamp=when.isoformat(),pid=int(pid.group(1)),action=stamp.group(2),lines=[line])
                events.append(current)
        elif current is not None and line.strip():
            current['lines'].append(line)
    return events


def collect(folder, log_path=None):
    folder=Path(folder)
    supervisor=json.loads((folder/'supervisor.json').read_text(encoding='utf-8'))
    trace=[]
    for line in (folder/'stages.jsonl').read_text(encoding='utf-8').splitlines():
        try:trace.append(json.loads(line))
        except json.JSONDecodeError:continue
    pids=owned_pids(supervisor)
    result=dict(source='existing attempt and read-only bounded licensing log tail',owned_pids=sorted(pids),
                ownership_source='child_pid and first PID per successful owned-tree taskkill output line',
                native_startup_attempted=False,tail_byte_limit=TAIL_BYTES)
    starts=[]
    for event in trace:
        if event.get('timestamp'):
            starts.append(datetime.fromisoformat(event['timestamp']).astimezone().replace(tzinfo=None)-timedelta(seconds=event.get('elapsed_seconds',0)))
    if not starts:
        return dict(result,state='missing_trace_timestamps',events=[])
    start=min(starts)-timedelta(seconds=1)
    end=min(starts)+timedelta(seconds=supervisor['elapsed_seconds']+1)
    result.update(window_start_local=start.isoformat(),window_end_local=end.isoformat())
    if log_path is None:
        log_path=Path(os.environ['TEMP'])/'.ansys'/f"licdebug.{os.environ['COMPUTERNAME']}.ANSYS OPTICSTUDIO.242.out"
    path=Path(log_path)
    result['log_path']=str(path)
    try:
        with path.open('rb') as stream:
            stream.seek(0,2);size=stream.tell();offset=max(0,size-TAIL_BYTES);stream.seek(offset)
            text=stream.read(TAIL_BYTES).decode('utf-8',errors='replace')
        result.update(log_size_bytes=size,read_offset_bytes=offset,events=correlate(text,pids,start,end),state='read')
    except OSError as exc:
        result.update(state='read_failed',error=dict(type=type(exc).__name__,message=str(exc)),events=[])
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=Path,required=True)
    parser.add_argument('--log',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=collect(args.attempt,args.log)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(state=result['state'],owned_pids=result['owned_pids'],events=len(result['events']),output=str(args.output)),ensure_ascii=False))
