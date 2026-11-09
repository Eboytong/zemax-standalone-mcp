import base64
import json
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

from zemax_mcp.config import Config
from zemax_mcp.errors import ZemaxError
from zemax_mcp.macro_models import StandaloneMacro
from zemax_mcp.backend import Backend


def test_macro_request_validates_paths_and_argument_contract():
    with pytest.raises(ValueError):
        StandaloneMacro(macro_path="x.zpl", timeout_seconds=0)
    with pytest.raises(ValueError):
        StandaloneMacro(macro_path="x.zpl", arguments={"bad-name": "x"})
    with pytest.raises(ValueError):
        StandaloneMacro(macro_path="x.zpl", arguments={"Name": 'x" -bad'})
    with pytest.raises(ValueError):
        StandaloneMacro(macro_path="x.zpl", expected_output="C:/x.txt")
    with pytest.raises(ValueError):
        StandaloneMacro(macro_path="x.zpl", arguments={"Path": "a"}, expected_output="C:/x.txt",
                        output_argument_name="Path")


def test_macro_builds_documented_launch_arguments_and_persists_result(tmp_path, monkeypatch):
    install = tmp_path / "install"
    install.mkdir()
    (install / "OpticStudio.exe").write_text("", encoding="utf-8")
    powershell = tmp_path / "powershell.exe"
    powershell.write_text("", encoding="utf-8")
    macro = tmp_path / "safe.ZPL"
    macro.write_text("PRINT 'ok'", encoding="utf-8")
    expected = tmp_path / "result.txt"
    process = SimpleNamespace(returncode=None, poll=lambda: process.returncode,
                              terminate=lambda: setattr(process, "returncode", 1),
                              kill=lambda: setattr(process, "returncode", 1))
    captured = {}

    class FakePopen:
        def __init__(self, command, **kwargs):
            self.returncode = 0
            captured["command"] = command
            captured["kwargs"] = kwargs
            script = base64.b64decode(command[-1]).decode("utf-16le")
            spec_blob = re.search(r"FromBase64String\('([^']+)'\)", script).group(1)
            captured["spec"] = json.loads(base64.b64decode(spec_blob))
            kwargs["stdout"].write(b"native log")
            kwargs["stdout"].flush()
        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 1

        def kill(self):
            self.returncode = 1

        def wait(self, timeout=None):
            return self.returncode

    monkeypatch.setattr("zemax_mcp.backend.subprocess.Popen", FakePopen)
    monkeypatch.setattr("zemax_mcp.backend.shutil.which", lambda _: str(powershell))
    backend = Backend(Config(install, tmp_path / "runs"), native=SimpleNamespace(application=None))
    req = StandaloneMacro(macro_path=str(macro), arguments={"Input": "a.zos"},
                          expected_output=str(expected), output_argument_name="Output")
    task = backend.run_standalone_macro(req)
    assert captured["spec"]["arguments"][0] == f'-zpl="{macro}"'
    assert '-vInput="a.zos"' in captured["spec"]["arguments"]
    assert f'-vOutput="{expected}"' in captured["spec"]["arguments"]
    assert task["state"] == "running"
    backend.tick()
    finished = backend.get_task_status(SimpleNamespace(task_id=task["task_id"]))
    assert finished["state"] == "failed"
    assert finished["error"]["code"] == "MACRO_OUTPUT_MISSING"
    result = backend.get_task_result(SimpleNamespace(task_id=task["task_id"], start=0, count=20,
                                                      series=None, grid=None, x_start=0, y_start=0,
                                                      width=32, height=32))
    assert result["exit_code"] == 0
    saved = json.loads(Path(finished["result_path"]).read_text(encoding="utf-8"))
    assert saved["process_log"] == finished["result_artifacts"][0]["path"]


def test_macro_requires_disconnected_native_session(tmp_path):
    backend = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(application=object()))
    req = StandaloneMacro(macro_path=str(tmp_path / "x.zpl"))
    with pytest.raises(ZemaxError, match="断开"):
        backend.run_standalone_macro(req)
