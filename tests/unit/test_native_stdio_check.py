import asyncio
import json
import os
import pytest
from scripts.development import native_stdio_check as probe


@pytest.mark.parametrize('rid,elevated', [(4096, False), (12288, True)])
def test_stdio_guard_keeps_non_medium_sessions_offline(tmp_path, monkeypatch, rid, elevated):
    monkeypatch.setattr(probe, 'process_context', lambda: dict(integrity_rid=rid, elevated=elevated))
    monkeypatch.setattr(probe, 'scenario', lambda *args: pytest.fail('Started stdio'))
    assert probe.run(tmp_path / 'probe') == 2
    result = json.loads((tmp_path / 'probe/result.json').read_text(encoding='utf-8'))
    assert result['state'] == 'requires_non_elevated_medium_context'


def test_stdio_failure_records_error_and_restores_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, 'process_context', lambda: dict(integrity_rid=8192, elevated=False))
    monkeypatch.setenv('COMPLUS_LoadFromRemoteSources', 'previous')
    async def fail(*args):
        assert os.environ['COMPLUS_LoadFromRemoteSources'] == '1'
        raise RuntimeError('controlled stdio failure')
    monkeypatch.setattr(probe, 'scenario', fail)
    assert probe.run(tmp_path / 'probe') == 1
    assert os.environ['COMPLUS_LoadFromRemoteSources'] == 'previous'
    result = json.loads((tmp_path / 'probe/result.json').read_text(encoding='utf-8'))
    assert result['error']['message'] == 'controlled stdio failure'


@pytest.mark.parametrize('close_fails', [False, True])
def test_analysis_failure_still_disconnects_and_records_calls(tmp_path, monkeypatch, close_fails):
    class Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    class Evidence:
        def __init__(self, *args): self.calls = []; self.checks = []
        async def finish(self, *args): pytest.fail('No task should finish after run_analysis failed')
        async def call(self, name, args=None):
            self.calls.append(name)
            if name == 'run_analysis': raise RuntimeError('analysis failure')
            if name == 'disconnect' and close_fails: raise RuntimeError('close failure')
            if name == 'get_status':
                return dict(connected=False, running_tasks=[], native_startup=dict(
                    events=[dict(stage='application_close', event='completed')]))
            return {}
    monkeypatch.setattr(probe, 'Client', Client)
    monkeypatch.setattr(probe, 'Evidence', Evidence)
    monkeypatch.setattr(probe.shutil, 'copyfile', lambda *args: None)
    record = {}
    with pytest.raises(RuntimeError, match='analysis failure'):
        asyncio.run(probe.scenario(tmp_path, record))
    assert record.get('normal_close', False) == (not close_fails)
    calls = json.loads((tmp_path / 'calls.json').read_text(encoding='utf-8'))
    if close_fails:
        assert calls[-1] == 'disconnect'
        assert record['close_error']['message'] == 'close failure'
    else:
        assert calls[-2:] == ['disconnect', 'get_status']
