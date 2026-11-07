"""POP staging failures must release only files owned by the request."""
from pathlib import Path
from types import SimpleNamespace as N

import pytest

from zemax_mcp.physical_optics import PhysicalOpticsMixin
from zemax_mcp.pop_models import Pop
import zemax_mcp.physical_optics as pop_module


class AnalysisNotStarted(RuntimeError):
    pass


class StagingBackend(PhysicalOpticsMixin):
    def __init__(self, directory):
        self.opened_analyses = 0
        def create_analysis(_):
            self.opened_analyses += 1
            raise AnalysisNotStarted("analysis creation failed")
        self.system = N(LDE=N(NumberOfSurfaces=3),
                        SystemData=N(Fields=N(NumberOfFields=1),
                                     Wavelengths=N(NumberOfWavelengths=1)),
                        Analyses=N(New_Analysis=create_analysis))
        self.native = N(application=N(POPDir=str(directory)),
                        api=N(Analysis=N(AnalysisIDM=N(PhysicalOpticsPropagation=1))))

    def _require_sequential(self):
        pass

    def _require_work(self):
        pass

    def _row(self, index):
        return N()


@pytest.fixture
def staging(tmp_path):
    directory = tmp_path / "pop"
    directory.mkdir()
    source = tmp_path / "beam.zbf"
    source.write_bytes(b"input fixture")
    return StagingBackend(directory), directory, source


@pytest.mark.parametrize("role", ["beam", "fiber", "multimode"])
@pytest.mark.parametrize("failure", ["partial_copy", "source_open"])
def test_pop_staging_failure_removes_current_owned_input(staging, monkeypatch, role, failure):
    backend, directory, source = staging
    if role == "multimode":
        source = source.with_suffix(".zmm")
        source.write_bytes(b"multimode fixture")
    options = dict(beam_type="File", beam_file=str(source))
    if role == "fiber":
        options = dict(fiber_type="File", fiber_file=str(source))
    elif role == "multimode":
        options["beam_type"] = "Multimode"
    original_open = Path.open
    if failure == "source_open":
        def failed_open(path, mode="r", *args, **kwargs):
            if path == source and mode == "rb":
                raise OSError("injected source open failure")
            return original_open(path, mode, *args, **kwargs)
        monkeypatch.setattr(Path, "open", failed_open)
    else:
        def interrupted_copy(source_stream, destination_stream):
            destination_stream.write(b"partial")
            raise OSError("injected copy failure")
        monkeypatch.setattr(pop_module.shutil, "copyfileobj", interrupted_copy)
    with pytest.raises(OSError, match="injected"):
        backend.run_pop(Pop(**options))
    assert list(directory.glob("mcp_input_*")) == []
    assert source.is_file()
    assert backend.opened_analyses == 0


def test_pop_second_input_failure_cleans_both_owned_files(staging, monkeypatch):
    backend, directory, source = staging
    copied = []
    def interrupted_second_copy(source_stream, destination_stream):
        copied.append(Path(destination_stream.name))
        destination_stream.write(b"partial")
        if len(copied) == 2:
            raise OSError("second copy failed")
    monkeypatch.setattr(pop_module.shutil, "copyfileobj", interrupted_second_copy)
    with pytest.raises(OSError, match="second copy"):
        backend.run_pop(Pop(beam_type="File", beam_file=str(source),
                            fiber_type="File", fiber_file=str(source)))
    assert len(copied) == 2
    assert all(not path.exists() for path in copied)
    assert backend.opened_analyses == 0


def test_pop_analysis_creation_failure_cleans_staged_inputs(staging):
    backend, directory, source = staging
    with pytest.raises(AnalysisNotStarted):
        backend.run_pop(Pop(beam_type="File", beam_file=str(source),
                            fiber_type="File", fiber_file=str(source)))
    assert list(directory.glob("mcp_input_*")) == []
    assert source.is_file()
    assert backend.opened_analyses == 1


def test_pop_staging_collision_preserves_existing_file(staging, monkeypatch):
    backend, directory, source = staging
    monkeypatch.setattr(pop_module.uuid, "uuid4", lambda: N(hex="collision"))
    collision = directory / "mcp_input_collision.zbf"
    collision.write_bytes(b"pre-existing file")
    with pytest.raises(FileExistsError):
        backend.run_pop(Pop(beam_type="File", beam_file=str(source)))
    assert collision.is_file()
    assert backend.opened_analyses == 0
