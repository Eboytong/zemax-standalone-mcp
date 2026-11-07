"""Isolated DLL metadata must not suppress native value readback or accept unknown files."""
from pathlib import Path
from types import SimpleNamespace as N
import subprocess

import pytest

from zemax_mcp.errors import ZemaxError
from zemax_mcp import pop_dll


class BrokenNames:
    @property
    def NumberOfParameters(self):
        raise RuntimeError("native metadata view-model failure")

    def GetParameterName(self, i):
        raise AssertionError("count failed first")


def test_dll_metadata_uses_isolated_query_only_after_api_failure(monkeypatch):
    seen=[]
    monkeypatch.setattr(pop_dll,"installed_names",lambda root,name: seen.append((root,name)) or ["Wx","Wy"])
    names,source=pop_dll.parameter_names(BrokenNames(),"beam","DLL","C:/data","beamsamp1.DLL")
    assert names==["Wx","Wy"] and seen==[("C:/data","beamsamp1.DLL")]
    assert "view-model" in source["api_metadata_error"]
    assert source["source"]=="isolated installed DLL UserParamNames"


def test_non_dll_metadata_failure_is_not_suppressed():
    with pytest.raises(ZemaxError) as error:
        pop_dll.parameter_names(BrokenNames(),"beam","File",None,None)
    assert error.value.code=="POP_PARAMETER_QUERY_FAILED"


@pytest.mark.parametrize("name",["../beamsamp1.dll","unknown.dll","C:/other/beamsamp1.dll",None])
def test_unknown_dll_is_rejected_before_process_start(tmp_path,name):
    with pytest.raises(ZemaxError):pop_dll.installed_names(tmp_path,name)


@pytest.mark.parametrize("reply",["null","[]",'["Wx",3]','[" "]',"invalid JSON"])
def test_invalid_isolated_metadata(tmp_path,monkeypatch,reply):
    root=tmp_path/"DLL/PhysicalOptics";root.mkdir(parents=True);(root/"beamsamp1.DLL").touch()
    monkeypatch.setattr(pop_dll.subprocess,"run",lambda *a,**k:N(returncode=0,stdout=reply,stderr=""))
    with pytest.raises(ZemaxError) as error:pop_dll.installed_names(tmp_path,"beamsamp1.DLL")
    assert error.value.code=="POP_PARAMETER_QUERY_FAILED"


@pytest.mark.parametrize("failure",["timeout","crash"])
def test_isolated_failure_is_structured(tmp_path,monkeypatch,failure):
    root=tmp_path/"DLL/PhysicalOptics";root.mkdir(parents=True);(root/"beamsamp1.DLL").touch()
    def run(*a,**k):
        if failure=="timeout":raise subprocess.TimeoutExpired(a[0],10)
        return N(returncode=3221225477,stdout="",stderr="native exception")
    monkeypatch.setattr(pop_dll.subprocess,"run",run)
    with pytest.raises(ZemaxError):pop_dll.installed_names(tmp_path,"beamsamp1.DLL")


def test_api_metadata_is_preferred():
    settings=N(NumberOfParameters=2,GetParameterName=lambda i:("Wx","Wy")[i])
    names,source=pop_dll.parameter_names(settings,"beam","DLL",None,"beamsamp1.DLL")
    assert names==["Wx","Wy"] and source["source"]=="ZOS-API"


@pytest.mark.parametrize("count",[-1,1002])
def test_invalid_native_parameter_count_is_rejected(count):
    settings=N(NumberOfParameters=count,GetParameterName=lambda i:"parameter")
    with pytest.raises(ZemaxError):pop_dll.parameter_names(settings,"beam","File",None,None)


@pytest.mark.parametrize("directory",[None,"missing"])
def test_missing_data_directory_is_structured(tmp_path,directory):
    with pytest.raises(ZemaxError) as error:pop_dll.installed_names(None if directory is None else tmp_path/"missing","beamsamp1.DLL")
    assert error.value.code=="INVALID_RESOURCE"
