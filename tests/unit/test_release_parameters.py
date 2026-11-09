"""Release native sessions must resolve the selected installed package."""
from pathlib import Path
import pytest
from tests.support.native import server_parameters
from zemax_mcp.config import PROJECT_ROOT


def test_source_native_session_parameters(monkeypatch,tmp_path):
    monkeypatch.delenv("ZEMAX_TEST_WHEEL_DIR",raising=False)
    p=server_parameters(tmp_path)
    assert p.args==["-B","-m","zemax_mcp"]
    assert str(p.cwd)==str(PROJECT_ROOT) and p.env["PYTHONPATH"]==str(PROJECT_ROOT/"src")
    assert p.env['ZEMAX_STATE_DIR']==str(tmp_path/'state')


def test_installed_native_session_parameters(monkeypatch,tmp_path):
    root=tmp_path/"wheel ' installed"
    (root/"zemax_mcp").mkdir(parents=True)
    (root/"zemax_mcp/__init__.py").write_text("",encoding="utf-8")
    monkeypatch.setenv("ZEMAX_TEST_WHEEL_DIR",str(root))
    p=server_parameters(tmp_path/"output")
    assert p.args[:3]==["-I","-B","-c"] and p.cwd==str(root.resolve())
    assert p.env["PYTHONPATH"]==str(root.resolve())
    assert p.env['ZEMAX_STATE_DIR']==str(tmp_path/'output'/'state')
    assert "is_relative_to" in p.args[3]
    compile(p.args[3],"installed-stdio-boot","exec")


def test_installed_native_session_requires_package(monkeypatch,tmp_path):
    monkeypatch.setenv("ZEMAX_TEST_WHEEL_DIR",str(tmp_path))
    with pytest.raises(ValueError,match="independently installed"):
        server_parameters(tmp_path/"output")


def test_clr_switch_not_forwarded_when_caller_absent(monkeypatch,tmp_path):
    monkeypatch.delenv("COMPLUS_LoadFromRemoteSources",raising=False)
    p=server_parameters(tmp_path)
    assert "COMPLUS_LoadFromRemoteSources" not in p.env


def test_clr_switch_forwarded_verbatim_when_caller_sets_it(monkeypatch,tmp_path):
    monkeypatch.setenv("COMPLUS_LoadFromRemoteSources","1")
    p=server_parameters(tmp_path)
    assert p.env["COMPLUS_LoadFromRemoteSources"]=="1"
