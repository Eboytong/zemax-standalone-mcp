"""Correlate licensing failures with an owned attempt, excluding historical noise."""
from datetime import datetime,timezone
import json
from support.startup_license_probe import collect,correlate,owned_pids,TAIL_BYTES


def test_owned_tree_excludes_parent_pids():
    record=dict(child_pid=10,owned_tree_stop=dict(returncode=0,stdout='成功: 已终止 PID 20 (属于 PID 10 子进程)的进程。\n成功: 已终止 PID 10 (属于 PID 999 子进程)的进程。'))
    assert owned_pids(record)=={10,20}


def test_failed_stop_output_does_not_establish_descendant_ownership():
    assert owned_pids(dict(child_pid=10,owned_tree_stop=dict(returncode=1,stdout='PID 999')))=={10}


def test_correlation_excludes_historical_and_unowned_pid():
    text='''2026/11/05 12:00:00 ERROR 20:ANSYS OPTICSTUDIO:test
 old failure
2026/11/05 12:17:42 HANDSHAKE_ERROR 20:ANSYS OPTICSTUDIO:test
 Could not make an SSL handshake with server 51820@127.0.0.1.
2026/11/05 12:18:00 CHECKOUT 999:ANSYS OPTICSTUDIO:test
 unrelated checkout
2026/11/05 12:19:02 CONNECT_ERROR 20:ANSYS OPTICSTUDIO:test
 Connection timed out.
2026/11/05 12:25:00 ERROR 20:ANSYS OPTICSTUDIO:test
 later failure
'''
    events=correlate(text,{10,20},datetime(2026,11,5,12,16),datetime(2026,11,5,12,20))
    assert [e['action'] for e in events]==['HANDSHAKE_ERROR','CONNECT_ERROR']
    assert all(e['pid']==20 for e in events)
    assert '51820@127.0.0.1' in events[0]['lines'][1]
    assert all('unrelated' not in line for e in events for line in e['lines'])


def attempt(folder):
    (folder/'supervisor.json').write_text(json.dumps(dict(child_pid=20,elapsed_seconds=180)),encoding='utf-8')
    stamp=datetime(2026,11,5,12,16,tzinfo=timezone.utc)
    (folder/'stages.jsonl').write_text(json.dumps(dict(timestamp=stamp.isoformat(),elapsed_seconds=1))+'\n{"stage":',encoding='utf-8')
    return stamp.astimezone().replace(tzinfo=None)


def test_tail_is_bounded_and_local_time_window_is_used(tmp_path):
    stamp=attempt(tmp_path)
    log=tmp_path/'native.log'
    line=f"{stamp.strftime('%Y/%m/%d %H:%M:%S')} HANDSHAKE_ERROR 20:ANSYS OPTICSTUDIO:test\n timeout\n"
    log.write_bytes(b'x'*(TAIL_BYTES+100)+b'\n'+line.encode())
    result=collect(tmp_path,log)
    assert result['state']=='read' and result['read_offset_bytes']>0
    assert result['events'][0]['timestamp']==stamp.isoformat()
    assert result['native_startup_attempted'] is False


def test_missing_log_is_recorded_without_relaunch(tmp_path):
    attempt(tmp_path)
    result=collect(tmp_path,tmp_path/'missing.log')
    assert result['state']=='read_failed' and result['events']==[]
    assert result['error']['type']=='FileNotFoundError'


def test_missing_timestamps_does_not_attribute_log_events(tmp_path):
    (tmp_path/'supervisor.json').write_text('{"child_pid":20,"elapsed_seconds":180}',encoding='utf-8')
    (tmp_path/'stages.jsonl').write_text('{"stage":"application_create"}',encoding='utf-8')
    result=collect(tmp_path,tmp_path/'unused.log')
    assert result['state']=='missing_trace_timestamps' and result['events']==[]
