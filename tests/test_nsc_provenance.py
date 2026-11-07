"""Write adoption and offline accumulated detector attribution contracts."""
import json
from types import SimpleNamespace as N
import pytest
from support.detectors import backend, TRACE_OPTIONS
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.nonsequential import OBJECT_FIELDS


class ObjectRow:
    def __init__(self, ignored=None):
        self.ignored=ignored
        for field,attribute in OBJECT_FIELDS.items():
            object.__setattr__(self,attribute,"" if field in {"material","comment"} else 0)
            object.__setattr__(self,attribute+"Cell",N(Solve="Fixed"))
        self.ObjectData=N();self.SourcesData=N();self.TypeData=N()
    def __setattr__(self,name,value):
        if name!=getattr(self,"ignored",None):object.__setattr__(self,name,value)


@pytest.mark.parametrize("field",list(OBJECT_FIELDS))
def test_direct_attribute_rejection_stops_batch(tmp_path,field):
    b=backend(tmp_path);attribute=OBJECT_FIELDS[field]
    first,second=ObjectRow(attribute),ObjectRow()
    b._object=lambda i:first if i==1 else second
    b._guard_nsc_cell=lambda *_:None
    b.get_nsc_objects=lambda _:dict(rows=[])
    value="test" if field in {"material","comment"} else 2
    r=b.dispatch("update_nsc_objects",dict(changes=[
        dict(object=1,**{field:value}),dict(object=2,x=4)]))
    assert not r["ok"] and r["error"]["code"]=="SETTING_REJECTED"
    details=r["error"]["details"]
    assert details["field"]==field and details["object"]==1
    assert details["requested"]==value and details["partial_changes_possible"]
    assert "checkpoint" in details and b.revision==1 and second.XPosition==0


def add_trace(b,task_id,options=None,state="succeeded",error=None):
    b.tasks[task_id]=dict(state=state,error=error,finished_at="2026-10-24T00:00:00Z")
    b._detector_record(1)["traces"].append(dict(task_id=task_id,
        model_revision=b.revision,configuration=1,trace_options=dict(options or TRACE_OPTIONS)))


@pytest.mark.parametrize("key,value",[
    ("use_polarization",True),("split_rays",True),("scatter_rays",True),
    ("ignore_errors",True),("number_of_cores",2),("random_seed",42),("filter","H1")])
def test_same_model_different_options_are_mixed(tmp_path,key,value):
    b=backend(tmp_path);b._clear_detector_records()
    add_trace(b,"a");add_trace(b,"b",{**TRACE_OPTIONS,key:value})
    p=b._detector_provenance(1)
    assert p["model_matches_history"] and p["trace_options_known"]
    assert p["mixed_conditions"] and not p["complete"]
    b._clear_detector_records(1);add_trace(b,"c",{**TRACE_OPTIONS,key:value})
    assert b._detector_provenance(1)["complete"]


def test_identical_options_and_missing_options(tmp_path):
    b=backend(tmp_path);b._clear_detector_records()
    add_trace(b,"a");add_trace(b,"b")
    assert b._detector_provenance(1)["complete"]
    b._detector_record(1)["traces"][0].pop("trace_options")
    p=b._detector_provenance(1)
    assert not p["trace_options_known"] and not p["complete"]


@pytest.mark.parametrize("timing",["synchronous","asynchronous"])
@pytest.mark.parametrize("state",["failed","cancelled"])
def test_power_snapshot_and_offline_report_include_prior_state(tmp_path,monkeypatch,timing,state):
    import zemax_mcp.nonsequential as module
    b=backend(tmp_path);b._clear_detector_records()
    error=dict(code="TASK_FAILED",message="native partial propagation") if state=="failed" else None
    add_trace(b,"old",state=state,error=error)
    b.tasks["old"]["result"]=dict(completed=False,task=dict(task_id="old",state=state,error=error))
    tool=N(Succeeded=True,SetRandomSeed=lambda _:None,ResetRandomSeed=lambda:None,
        GetTotalRayEnergy=lambda:1.,DeadRayErrors=0.,DeadRayThreshold=0.)
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool)
    b.system.NCE.GetDetectorData=lambda *_:(True,1.)
    b._close_task_native=lambda _:True
    monkeypatch.setattr(module,"scalar_settings",lambda _:dict())
    holder={}
    def start(kind,native,settings,collector):
        task=dict(task_id="new",context=b.context(),settings=settings,state="running")
        b.tasks["new"]=task;holder.update(task=task,collector=collector)
        if timing=="synchronous":holder["result"]=collector(task)
        return dict(task_id="new",state="running")
    b._start_task=start
    b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"](detector_policy="accumulate"))
    result=holder.get("result") or holder["collector"](holder["task"])
    references=result["rows"][0]["trace_conditions"]
    assert len(references)==2
    assert references[0]["state"]==state and references[0]["error"]==error
    assert references[1]["state"]=="succeeded" and references[1]["trace_options"]==TRACE_OPTIONS
    assert not result["rows"][0]["complete"]
    b.tasks["new"].update(state="succeeded",result=result)
    report=b.export_evaluation_report(COMMAND_MODELS["export_evaluation_report"](task_ids=["new"]))
    paths={a["kind"]:a["path"] for a in report["artifacts"]}
    from pathlib import Path
    saved=json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert {item["task_id"] for item in saved}=={"new","old"}
    assert saved[1]["result"]["task"]["state"]==state
    markdown=Path(paths["markdown"]).read_text(encoding="utf-8")
    assert '"state": "'+state+'"' in markdown
    if error:assert error["message"] in markdown


def test_missing_related_task_preserves_snapshot_and_reports_gap(tmp_path):
    b=backend(tmp_path)
    reference=dict(task_id="missing",state="failed",error=dict(code="TASK_FAILED"))
    result=dict(rows=[dict(trace_conditions=[reference])])
    b.tasks["new"]=dict(state="succeeded",result=result)
    report=b.export_evaluation_report(COMMAND_MODELS["export_evaluation_report"](task_ids=["new"]))
    from pathlib import Path
    saved=json.loads(Path(next(a["path"] for a in report["artifacts"] if a["kind"]=="json")).read_text(encoding="utf-8"))
    assert saved[0]["result"]["unavailable_trace_tasks"][0]["state"]=="failed"
    assert "unavailable_trace_tasks" not in result


@pytest.mark.parametrize("ignore",[False,True])
def test_native_success_with_error_rays_never_claims_complete(tmp_path,monkeypatch,ignore):
    import zemax_mcp.nonsequential as module
    from zemax_mcp.errors import ZemaxError
    b=backend(tmp_path);b._clear_detector_records()
    tool=N(Succeeded=True,SetRandomSeed=lambda _:None,ResetRandomSeed=lambda:None,
        GetTotalRayEnergy=lambda:1.,DeadRayErrors=.125,DeadRayThreshold=0.)
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool)
    b.system.NCE.GetDetectorData=lambda *_:(True,.5)
    b._close_task_native=lambda _:True
    monkeypatch.setattr(module,"scalar_settings",lambda _:dict())
    holder={}
    def start(kind,native,settings,collector):
        task=dict(task_id="new",context=b.context(),settings=settings,state="running")
        b.tasks["new"]=task;holder.update(task=task,collector=collector)
        return dict(task_id="new",state="running")
    b._start_task=start
    b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"](detector_policy="accumulate",ignore_errors=ignore))
    task=holder["task"]
    if ignore:
        result=holder["collector"](task)
        assert not result["complete"] and not result["rows"][0]["complete"]
        task["state"]="succeeded"
    else:
        with pytest.raises(ZemaxError)as error:holder["collector"](task)
        assert error.value.code=="NSC_TRACE_ERRORS" and error.value.details["dead_ray_errors"]==.125
        task.update(state="failed",error=error.value.as_dict())
    assert not task["native_trace_complete"] and task["native_dead_ray_errors"]==.125
    provenance=b._detector_provenance(1)
    assert not provenance["complete"]
    assert not provenance["trace_history"][0]["native_trace_complete"]


@pytest.mark.parametrize("value",[float("nan"),float("inf"),-1.])
def test_invalid_native_error_energy_is_rejected(tmp_path,monkeypatch,value):
    import zemax_mcp.nonsequential as module
    from zemax_mcp.errors import ZemaxError
    b=backend(tmp_path)
    tool=N(Succeeded=True,SetRandomSeed=lambda _:None,ResetRandomSeed=lambda:None,
        GetTotalRayEnergy=lambda:1.,DeadRayErrors=value,DeadRayThreshold=0.)
    b.system.Tools=N(OpenNSCRayTrace=lambda:tool)
    monkeypatch.setattr(module,"scalar_settings",lambda _:dict())
    holder={}
    def start(kind,native,settings,collector):
        holder["collector"]=collector
        return dict(task_id="new",state="running")
    b._start_task=start
    b.run_nsc_ray_trace(COMMAND_MODELS["run_nsc_ray_trace"](detector_policy="accumulate",ignore_errors=True))
    with pytest.raises(ZemaxError)as error:holder["collector"]({})
    assert error.value.code=="INVALID_RESULT_DATA"
