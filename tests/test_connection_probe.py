"""Bounded probe supervision uses only the process created for that attempt."""
import json
import subprocess
from types import SimpleNamespace as N
import pytest
from support import connection_probe019 as probe


@pytest.mark.parametrize('timeout,stop_timeout',[(False,False),(True,False),(True,True)])
def test_probe_supervision_and_stage_attribution(tmp_path,monkeypatch,timeout,stop_timeout):
    launches=[];stops=[]
    class Process:
        pid=123456
        def __init__(self,args,**kwargs):
            launches.append((args,kwargs));self.waits=0;self.alive=True
            folder=tmp_path/'attempt'
            (folder/'stages.jsonl').write_text('\n'.join(json.dumps(v)for v in [
                dict(stage='environment',event='started'),dict(stage='environment',event='completed'),
                dict(stage='zos_initialize',event='started')]),encoding='utf-8')
        def wait(self,timeout):
            self.waits+=1
            if (self.waits==1 and timeout_flag)or stop_timeout:raise subprocess.TimeoutExpired('child',timeout)
            self.alive=False;return 1 if timeout_flag else 0
        def poll(self):return None if self.alive else 1 if timeout_flag else 0
    timeout_flag=timeout
    def stop(args,**kwargs):
        stops.append((args,kwargs))
        if stop_timeout:raise subprocess.TimeoutExpired(args,kwargs['timeout'])
        return N(returncode=0,stdout='owned process stopped',stderr='')
    monkeypatch.setattr(probe.subprocess,'Popen',Process)
    monkeypatch.setattr(probe.subprocess,'run',stop)
    record=probe.run(tmp_path/'attempt',startup_seconds=1,cleanup_seconds=1)
    assert len(launches)==1
    assert launches[0][0][-2:]==['--output-dir',str((tmp_path/'attempt').resolve())]
    assert launches[0][1]['creationflags']==subprocess.CREATE_NO_WINDOW
    assert record['state']==('initialization_timeout'if timeout else 'passed')
    assert record['completed_stages']==['environment']and record['unfinished_stages']==['zos_initialize']
    assert record['child_alive']is stop_timeout
    if timeout:
        assert stops[0][0]==['taskkill','/PID','123456','/T','/F']
        assert 0<stops[0][1]['timeout']<=1
    else:assert not stops
    assert (tmp_path/'attempt/supervisor.json').is_file()


def test_existing_evidence_directory_not_reused(tmp_path):
    with pytest.raises(FileExistsError):probe.run(tmp_path)


@pytest.mark.parametrize('startup,cleanup',[(0,15),(181,15),(180,0),(180,16)])
def test_probe_budget_bounds(tmp_path,startup,cleanup):
    with pytest.raises(ValueError):probe.run(tmp_path/'unused',startup,cleanup)
    assert not (tmp_path/'unused').exists()


def test_trace_reader_retains_completed_events_after_interrupted_write(tmp_path):
    (tmp_path/'stages.jsonl').write_text('{"stage":"clr_load","event":"started"}\n{"stage":',encoding='utf-8')
    assert probe.read_events(tmp_path)==[dict(stage='clr_load',event='started')]
