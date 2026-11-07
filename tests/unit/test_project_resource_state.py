from pathlib import Path
from types import SimpleNamespace as N
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import SaveLens
from zemax_mcp.errors import ZemaxError

class Project:
    IsProjectDirectory=True
    def __init__(self,path):self.SystemFile=str(path);self.selection='ED01.ABGF';self.saved=[]
    def SaveAs(self,path):
        self.saved.append(Path(path))
        if not (Path(path).parent/'ABg_Data').is_dir():self.selection=None
        self.SystemFile=path


def setup(tmp_path):
    original=tmp_path/'source';original.mkdir();(original/'ABg_Data').mkdir()
    (original/'lens.zos').touch()
    system=Project(original/'lens.zos')
    b=Backend(Config(Path('unused'),tmp_path),N(system=system))
    b.directory=tmp_path/'session';b.directory.mkdir()
    return b,system


def test_project_working_copy_and_checkpoint_keep_selection(tmp_path):
    b,system=setup(tmp_path)
    b._working_copy()
    assert b.work_path.parent!=tmp_path/'source'
    assert system.selection=='ED01.ABGF'
    b._checkpoint('test')
    assert system.selection=='ED01.ABGF'
    assert system.saved[-2].parent==b.work_path.parent


def test_project_export_stages_resources_before_save(tmp_path):
    b,system=setup(tmp_path);b._working_copy()
    b.save_lens_as(SaveLens(path=str(tmp_path/'export/lens.zos')))
    assert system.selection=='ED01.ABGF'
    assert system.SystemFile==str(b.work_path)


def test_project_export_resource_conflict_precedes_save(tmp_path):
    b,system=setup(tmp_path);b._working_copy()
    target=tmp_path/'export';(target/'ABg_Data').mkdir(parents=True)
    count=len(system.saved)
    with pytest.raises(ZemaxError)as error:b.save_lens_as(SaveLens(path=str(target/'lens.zos')))
    assert error.value.code=='OUTPUT_EXISTS'
    assert len(system.saved)==count


def test_project_copy_rejects_recursive_destination(tmp_path):
    source=tmp_path/'source';(source/'ScatterData').mkdir(parents=True)
    with pytest.raises(ZemaxError)as error:Backend._copy_project_resources(source,source/'ScatterData/nested')
    assert error.value.code=='PROJECT_COPY_FAILED'
