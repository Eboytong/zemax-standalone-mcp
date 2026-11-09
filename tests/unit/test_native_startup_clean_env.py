"""External-runtime setup must stop before native execution on preparation failures."""
import json
from types import SimpleNamespace
import pytest
from scripts.development import native_startup_clean_env as clean


@pytest.fixture(autouse=True)
def project_root(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    root.mkdir()
    monkeypatch.setattr(clean, 'ROOT', root)


def test_low_base_context_stops_before_environment_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(clean.check, 'run', lambda *a, **kw: 2)
    monkeypatch.setattr(clean.subprocess, 'run', lambda *a, **kw: pytest.fail('Started a subprocess'))
    folder = tmp_path / 'evidence'
    assert clean.run(tmp_path / 'runtime', folder) == 2
    record = json.loads((folder / 'bootstrap.json').read_text(encoding='utf-8'))
    assert record['state'] == 'blocked_base_context' and not record['native_requested']


def test_install_failure_preserves_code_and_never_requests_native(tmp_path, monkeypatch):
    monkeypatch.setattr(clean.check, 'run', lambda *a, **kw: 0)
    calls = []
    def execute(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=7 if 'pip' in command else 0)
    monkeypatch.setattr(clean.subprocess, 'run', execute)
    folder = tmp_path / 'evidence'
    assert clean.run(tmp_path / 'runtime', folder) == 7
    record = json.loads((folder / 'bootstrap.json').read_text(encoding='utf-8'))
    assert record['failed_stage'] == 'install_dependencies'
    assert not record['native_requested'] and len(calls) == 3


def test_existing_runtime_is_reused_and_native_failure_preserved(tmp_path, monkeypatch):
    python = tmp_path / 'runtime/Scripts/python.exe'
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setattr(clean.check, 'run', lambda *a, **kw: 0)
    def execute(command, **kwargs):
        assert 'venv' not in command
        return SimpleNamespace(returncode=1 if '--output-dir' in command else 0)
    monkeypatch.setattr(clean.subprocess, 'run', execute)
    folder = tmp_path / 'evidence'
    assert clean.run(tmp_path / 'runtime', folder) == 1
    record = json.loads((folder / 'bootstrap.json').read_text(encoding='utf-8'))
    assert record['failed_stage'] == 'native_check' and record['native_requested']


def test_project_local_runtime_rejected_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='outside the project'):
        clean.run(tmp_path / '.venv', tmp_path / 'evidence')
    assert not (tmp_path / 'evidence').exists()


def test_environment_creation_error_keeps_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setattr(clean.check, 'run', lambda *a, **kw: 0)
    def execute(*args, **kwargs):
        raise OSError('controlled creation error')
    monkeypatch.setattr(clean.subprocess, 'run', execute)
    folder = tmp_path / 'evidence'
    with pytest.raises(OSError, match='controlled creation error'):
        clean.run(tmp_path / 'runtime', folder)
    record = json.loads((folder / 'bootstrap.json').read_text(encoding='utf-8'))
    assert record['failed_stage'] == 'create_environment'
    assert record['error']['message'] == 'controlled creation error'
    assert not record['native_requested']
