"""The manual comparison records context and preserves process-only settings."""
import json
import os
import pytest
from scripts.development import native_startup_check as check


def test_low_context_stops_before_native_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(check, 'process_context', lambda: dict(integrity_rid=4096))
    calls = []
    monkeypatch.setattr(check.probe, 'run', lambda *a, **kw: calls.append(a))
    folder = tmp_path/'check'
    assert check.run(folder) == 2 and calls == []
    result = json.loads((folder/'result.json').read_text(encoding='utf-8'))
    assert result['state'] == 'blocked_low_integrity_context' and not result['native_started']
    assert 'native_startup_clean_env.py' in result['next_action']


@pytest.mark.parametrize('rid, code', [(4096, 2), (8192, 0)])
def test_context_only_never_starts_native(tmp_path, monkeypatch, rid, code):
    monkeypatch.setattr(check, 'process_context', lambda: dict(integrity_rid=rid))
    def unexpected(*args, **kwargs):
        pytest.fail('Context-only observation started a native probe')
    monkeypatch.setattr(check.probe, 'run', unexpected)
    assert check.run(tmp_path/'context', context_only=True) == code
    result = json.loads((tmp_path/'context/result.json').read_text(encoding='utf-8'))
    assert result == dict(state='process_context_only', native_started=False,
                          normal_user_context=rid >= 8192)


def test_file_label_failure_remains_diagnostic(monkeypatch):
    import win32security
    def denied(*args):
        raise OSError('label unavailable')
    monkeypatch.setattr(win32security, 'GetFileSecurity', denied)
    assert check.file_label('controlled.exe') == dict(path='controlled.exe', error='label unavailable')


@pytest.mark.parametrize('previous', [None, '0'])
@pytest.mark.parametrize('failure', [False, True])
def test_normal_context_uses_bounded_probe_and_restores_switch(tmp_path, monkeypatch, previous, failure):
    monkeypatch.setattr(check, 'process_context', lambda: dict(integrity_rid=8192))
    key = 'COMPLUS_LoadFromRemoteSources'
    if previous is None:
        monkeypatch.delenv(key, raising=False)
    else:
        monkeypatch.setenv(key, previous)
    def probe(folder, startup_seconds, cleanup_seconds):
        assert folder == tmp_path/'check/attempt'
        assert startup_seconds == 180 and cleanup_seconds == 15
        assert os.environ[key] == '1'
        if failure:
            raise OSError('controlled observation failure')
        return dict(state='passed', child_alive=False)
    monkeypatch.setattr(check.probe, 'run', probe)
    if failure:
        with pytest.raises(OSError, match='controlled observation failure'):
            check.run(tmp_path/'check')
    else:
        assert check.run(tmp_path/'check') == 0
    assert os.environ.get(key) == previous
