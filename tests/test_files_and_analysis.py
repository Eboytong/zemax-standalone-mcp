import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.files import input_path,output_path
from zemax_mcp.models import COMMAND_MODELS,TaskResult
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError

def backend(tmp_path,system):
    b=Backend(Config(Path("unused"),tmp_path),NS(system=system))
    b.directory=tmp_path;b.work_path=tmp_path/"work.zos"
    return b

@pytest.mark.parametrize("name",["relative.zos","C:/output.txt"])
def test_output_rejects_invalid_path(name):
    with pytest.raises(ZemaxError):output_path(name,{".zos"})

def test_output_default_refuses_overwrite(tmp_path):
    path=tmp_path/"design.zos";path.touch()
    with pytest.raises(ZemaxError):output_path(str(path),{".zos"})
    assert output_path(str(path),{".zos"},True)==path

def test_input_requires_existing_allowed_file(tmp_path):
    with pytest.raises(ZemaxError):input_path(str(tmp_path/"missing.mf"),{".mf"})

@pytest.mark.parametrize("close_result",[False,True])
def test_copy_close_protection(tmp_path,close_result):
    copy=NS(SaveAs=lambda _:None,Close=lambda _:close_result,SystemID=2)
    b=backend(tmp_path,NS(CopySystem=lambda:copy))
    r=b.dispatch("copy_system",dict(path=str(tmp_path/"copy.zos")))
    assert r["ok"]==close_result
    assert b.requires_reconnect != close_result
    assert b.work_path==tmp_path/"work.zos" and b.revision==0

def test_copy_save_failure_still_closes(tmp_path):
    calls=[]
    def fail(_):raise OSError("save")
    copy=NS(SaveAs=fail,Close=lambda _:calls.append("close"),SystemID=2)
    b=backend(tmp_path,NS(CopySystem=lambda:copy))
    assert not b.dispatch("copy_system",dict(path=str(tmp_path/"copy.zos")))["ok"]
    assert calls==["close"]

def test_native_close_failure_blocks_mutation(tmp_path):
    b=backend(tmp_path,NS())
    with pytest.raises(ZemaxError):b._release_owned(NS(Close=lambda:False))
    assert b.requires_reconnect

@pytest.mark.parametrize("args",[{"kind":"invalid"},{"kind":"huygens_mtf","maximum_frequency":0},{"kind":"ray_fan","number_of_rays":0},{"kind":"wavefront","unknown":1},{"kind":"zernike_standard","maximum_terms":0}])
def test_analysis_requests_invalid(args):
    with pytest.raises(ValidationError):RunAnalysis(request=args)

@pytest.mark.parametrize("args",[{"count":0},{"grid":0,"width":1000,"height":1000},{"x_start":-1}])
def test_grid_paging_invalid(args):
    with pytest.raises(ValidationError):TaskResult(task_id="t",**args)

def test_grid_region_and_summary(tmp_path):
    b=backend(tmp_path,NS())
    result={"task":{},"context":{},"artifacts":[],"grids":[{"grid":0,"nx":4,"ny":3,"values":[[10*y+x for x in range(4)]for y in range(3)]}]}
    b.tasks["t"]={"task_id":"t","state":"succeeded","result":result}
    summary=b.get_task_result(TaskResult(task_id="t"))
    assert "values" not in summary["grids"][0]
    chunk=b.get_task_result(TaskResult(task_id="t",grid=0,x_start=1,y_start=1,width=2,height=1))["grid"]
    assert chunk["values"]==[[11,12]] and chunk["next_x"]==3 and chunk["next_y"]==2
    with pytest.raises(ZemaxError):b.get_task_result(TaskResult(task_id="t",grid=2))

def test_merit_load_checkpoint_before_write(tmp_path):
    calls=[];path=tmp_path/"m.mf";path.touch()
    b=backend(tmp_path,NS(MFE=NS(LoadMeritFunction=lambda _:calls.append("load"))))
    b._mutate=lambda _:calls.append("checkpoint")
    b.get_merit_function=lambda _:{}
    assert b.dispatch("load_merit_function",dict(path=str(path)))["ok"]
    assert calls==["checkpoint","load"]

def test_project_bad_directory_does_not_mutate(tmp_path):
    b=backend(tmp_path,NS())
    r=b.dispatch("update_project_settings",dict(operation="convert",directory=str(tmp_path)))
    assert not r["ok"] and b.revision==0

def test_archive_validates_output_before_opening_tool(tmp_path):
    b=backend(tmp_path,NS())
    assert not b.dispatch("create_archive",dict(path=str(tmp_path/"bad.txt")))["ok"]
    assert b.revision==0
