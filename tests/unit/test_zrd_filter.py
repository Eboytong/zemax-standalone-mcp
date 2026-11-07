"""Read-only native ZRD settings, path selection and bounded task contracts."""
from types import SimpleNamespace as NS

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.nonsequential import wavelength_filter_validation


class Data:
    def __init__(self, rays):
        self.rays=rays; self.ray=-1; self.segment=-1

    def ReadNextRay(self):
        self.ray+=1; self.segment=-1
        return self.ray<len(self.rays)

    def ReadNextRaySegment(self):
        self.segment+=1
        return self.segment<len(self.rays[self.ray])

    def __getattr__(self,name):
        if name=="RayNumber":return self.ray+10
        if name=="NumSegments":return len(self.rays[self.ray])
        if name=="WaveIndex":return 1
        if name=="WlUM":return .55
        return self.rays[self.ray][self.segment].get(name,0)


class Reader:
    ErrorMessage="injected native failure"
    def __init__(self,rays,ignored=None,run=True,succeeded=True,close=True):
        self.data=Data(rays); self.ignored=ignored; self.run=run; self.Succeeded=succeeded
        self.closed=0; self.started=0; self.close=close
        self.Filter=""; self.ZRDFile=""

    def __setattr__(self,name,value):
        if name==getattr(self,"ignored",None):return
        object.__setattr__(self,name,value)

    @property
    def ZRDFile(self):
        raise AttributeError("property cannot be read")

    @ZRDFile.setter
    def ZRDFile(self,value):
        self._zrd_file=value

    def RunAndWaitForCompletion(self):
        self.started+=1
        return self.run

    def GetResults(self):return self.data

    def Close(self):
        self.closed+=1
        return self.close


def backend(tmp_path, reader):
    b=Backend(Config(tmp_path,tmp_path), NS(system=NS(Mode="NonSequential",Tools=NS(OpenRayDatabaseReader=lambda:reader),
        SystemData=NS(Units=NS(LensUnits="Millimeters")))))
    b.directory=tmp_path
    b.get_system_settings=lambda _:dict(lens_units="Millimeters")
    path=tmp_path/"sample.zrd";path.write_bytes(b"ordinary fake input; no native data")
    return b,path


def complete(b,path,**args):
    response=b.dispatch("read_zrd",dict(path=str(path),**args))
    assert response["ok"],response
    task_id=response["data"]["task_id"]
    for _ in range(100):
        if not b.active:break
        b.tick()
    assert not b.active
    return b.tasks[task_id],b._full_result(task_id)


def test_ignored_setting_never_runs_reader(tmp_path):
    reader=Reader([],ignored="Filter");b,path=backend(tmp_path,reader)
    task,result=complete(b,path,filter="X_WAVERANGE(3,0.5,0.6)")
    assert task["state"]=="failed" and result["error"]["code"]=="SETTING_REJECTED"
    assert result["error"]["details"]["setting"]=="Filter"
    assert reader.started==0 and reader.closed==1 and b.revision==0


def test_native_write_only_file_property_is_not_read(tmp_path):
    reader=Reader([]);b,path=backend(tmp_path,reader)
    task,result=complete(b,path)
    assert task["state"]=="succeeded" and reader._zrd_file==str(path)


@pytest.mark.parametrize("run,succeeded",[(False,False),(False,True),(True,False)])
def test_native_failure_stays_failure_and_closes(tmp_path,run,succeeded):
    reader=Reader([],run=run,succeeded=succeeded);b,path=backend(tmp_path,reader)
    task,result=complete(b,path)
    assert task["state"]=="failed" and result["error"]["code"]=="ZRD_READ_FAILED"
    assert reader.closed==1 and not b.requires_reconnect


@pytest.mark.parametrize("expression",["","H3 & X_WAVERANGE(3,0.5,0.6)"," X_WAVERANGE(3,5e-1,6e-1) "])
def test_empty_native_selection_preserves_filter(tmp_path,expression):
    reader=Reader([]);b,path=backend(tmp_path,reader)
    task,result=complete(b,path,filter=expression)
    assert task["state"]=="succeeded" and result["completed"]
    assert reader.Filter==expression
    assert result["rows"]==[] and result["summary"]["segments"]==0
    assert result["summary"]["next_read"]is None and not result["summary"]["truncated"]
    assert result["summary"]["actual_filter"]==expression
    assert ("wavelength_filter_validation"in result["summary"])==bool(expression.strip())


def test_native_selected_path_segments_are_not_postfiltered(tmp_path):
    rays=[[dict(HitObject=1,Intensity=1.),dict(HitObject=3,Intensity=.8)]]
    reader=Reader(rays);b,path=backend(tmp_path,reader)
    task,result=complete(b,path,filter="X_WAVERANGE(3,0.5,0.6)")
    assert [r["HitObject"]for r in result["rows"]]==[1,3]
    assert result["summary"]["wavelength_filter_validation"]["fallback"].startswith("none")
    assert result["summary"]["wavelength_scope"].startswith("WlUM is the native ray-header")


@pytest.mark.parametrize("size",[1,2,3,4,20])
def test_resume_advances_across_ray_and_segment_boundaries(tmp_path,size):
    rays=[[dict(HitObject=i+1)for i in range(count)]for count in (2,3,1)]
    reader=Reader(rays);b,path=backend(tmp_path,reader)
    expected=[(r+10,s)for r,segments in enumerate(rays)for s in range(len(segments))]
    rows=[];page={};seen=set()
    for _ in range(10):
        reader.data=Data(rays)
        task,result=complete(b,path,filter="H3",max_segments=size,**page)
        assert task["state"]=="succeeded"
        rows.extend((r["RayNumber"],r["segment_index"])for r in result["rows"])
        page=result["summary"]["next_read"]
        if page is None:break
        pair=(page["start_ray"],page["start_segment"])
        assert pair not in seen
        seen.add(pair)
    else:raise AssertionError("resume loop did not advance")
    assert rows==expected


def test_out_of_range_resume_returns_empty(tmp_path):
    reader=Reader([[dict(HitObject=3)]]);b,path=backend(tmp_path,reader)
    task,result=complete(b,path,start_ray=99)
    assert task["state"]=="succeeded" and not result["rows"]


def test_cancel_boundary_closes_reader_with_partial_rows(tmp_path):
    reader=Reader([[dict(HitObject=1),dict(HitObject=3)]]*600);b,path=backend(tmp_path,reader)
    response=b.dispatch("read_zrd",dict(path=str(path)))
    task=b.tasks[response["data"]["task_id"]]
    b.tick()
    task["cancel_requested"]=True
    while b.active:b.tick()
    assert task["state"]=="cancelled" and reader.closed==1
    assert not b._full_result(task["task_id"])["completed"]


def test_large_ray_stream_finishes_in_bounded_batches(tmp_path):
    reader=Reader([[dict(HitObject=3)]]*1000);b,path=backend(tmp_path,reader)
    task,result=complete(b,path)
    assert task["state"]=="succeeded" and len(result["rows"])==1000
    assert result["summary"]["next_read"]is None


def test_large_skipped_prefix_remains_cancellable(tmp_path):
    reader=Reader([[dict(HitObject=3)]]*2000);b,path=backend(tmp_path,reader)
    response=b.dispatch("read_zrd",dict(path=str(path),start_ray=1900))
    task=b.tasks[response["data"]["task_id"]]
    b.tick();task["cancel_requested"]=True
    while b.active:b.tick()
    assert task["state"]=="cancelled" and reader.closed==1
    assert not b._full_result(task["task_id"])["rows"]


@pytest.mark.parametrize("run",[True,False])
def test_close_failure_blocks_further_work(tmp_path,run):
    reader=Reader([],run=run,close=False);b,path=backend(tmp_path,reader)
    task,result=complete(b,path)
    assert task["state"]=="failed" and result["error"]["code"]=="CLEANUP_FAILED"
    assert b.requires_reconnect and reader.closed==1
    assert b.dispatch("read_zrd",dict(path=str(path)))["error"]["code"]=="RECONNECT_REQUIRED"


def test_capability_keeps_converted_subbins_unvalidated():
    scope=wavelength_filter_validation()
    assert scope["status"]=="partial_native_validation"
    assert "sample_3"in scope["known_difference"] and "not validated"in scope["known_difference"]
