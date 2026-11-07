import csv,json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.analyses import parse_zernike,parse_psf_section
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.nsc_models import ObjectUpdates
from zemax_mcp.reports import export_saved_report
from zemax_mcp.tolerancing import distribution_scope

def test_annular_and_standard_text_layouts():
    rows=parse_zernike("Z 1\t-.1\nZ 2\t0",2)
    # The installed format includes a leading digit, and unknown formats stay raw.
    assert not rows
    assert [r["value"]for r in parse_zernike("Z 1\t-0.1\nZ 2\t0",2)]==[-.1,0]
    assert parse_zernike("Z 1 0.1 : 1\nZ 2 0.2 : R",2)[1]["polynomial"]=="R"
    assert not parse_zernike("Z 1 0.1\nZ 3 0.2",2)


def test_psf_cross_text_format_and_unrecognized_fallback():
    s=parse_psf_section("位置\n0 -1.0 1.2E-1\n1 0.0 1.0\n2 1.0 1.2E-1")
    assert s["x"]==[-1,0,1]and s["y"]==[[.12],[1],[.12]]
    assert s["x_unit"]=="micrometers"
    for text in ["unknown format","1 0 1\n2 1 0","0 0 1\n2 1 0","0 1 0\n1 0 1","0 0 1e999\n1 1 0"]:
        assert parse_psf_section(text)is None


def test_diffraction_correction_is_specific_to_geometric_analysis():
    for kind in ["geometric_through_focus_mtf","geometric_encircled_energy"]:
        q=COMMAND_MODELS["run_analysis"].model_validate(dict(request=dict(kind=kind,multiply_by_diffraction_limit=False)))
        assert q.request.multiply_by_diffraction_limit is False
    for kind in ["fft_through_focus_mtf","huygens_through_focus_mtf","diffraction_encircled_energy"]:
        with pytest.raises(ValidationError):COMMAND_MODELS["run_analysis"].model_validate(dict(request=dict(kind=kind,multiply_by_diffraction_limit=False)))


@pytest.mark.parametrize("change",[dict(width=0),dict(height=4097),dict(kind="nsc_3d",end=2),dict(kind="cross_section",viewpoint="XY")])
def test_layout_export_argument_boundaries(change):
    with pytest.raises(ValidationError):COMMAND_MODELS["run_layout_export"].model_validate(dict(path="C:/out/layout.png",**change))


def test_layout_rejects_wrong_system_mode_before_opening_tool(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path),NS(system=NS(Mode="Sequential")))
    b._require_work=lambda:None
    request=COMMAND_MODELS["run_layout_export"](path=str(tmp_path/"layout.png"),kind="nsc_3d")
    with pytest.raises(ZemaxError,match="模式"):b.run_layout_export(request)


def test_offline_report_includes_native_image_and_reports_missing_file(tmp_path):
    source=tmp_path/"layout.png";source.write_bytes(b"native image fixture")
    output=tmp_path/"report";output.mkdir()
    item=dict(task_id="layout",result=dict(artifacts=[dict(kind="native_image",path=str(source))]))
    result=export_saved_report(output,[item],"布局",False,["markdown"])
    assert any(a["kind"]=="native_image"for a in result["artifacts"])
    assert "![layout_layout.png](layout_layout.png)"in(output/"report.md").read_text(encoding="utf-8")
    source.unlink()
    with pytest.raises(ZemaxError,match="不存在"):export_saved_report(output,[item],"布局",False,["markdown"])


def test_report_exposes_pop_coupling_definition(tmp_path):
    definition=dict(receiver_efficiency="power-weighted independent component overlaps",vector_inner_product=False)
    result=export_saved_report(tmp_path,[dict(task_id="pop",result=dict(coupling_definition=definition))],"POP",False,["markdown"])
    text=(tmp_path/"report.md").read_text(encoding="utf-8")
    assert "power-weighted independent component overlaps"in text and '"vector_inner_product": false'in text

def test_stat_distribution_segments_and_ignored_row():
    def row(i,kind,params=None,ignore=False):
        return dict(operand=i,type=kind,parameters=params or {},minimum=-1,maximum=1,ignore=ignore)
    rows=[row(1,"TTHI"),row(2,"STAT",{"1":1}),row(3,"TTHI"),row(4,"STAT",{1:0,2:4}),row(5,"TTHI"),row(6,"STAT",{1:2},True),row(7,"TTHI")]
    result=distribution_scope(rows,"Normal")
    assert [r["distribution"]["type"]for r in result]==["Normal","Uniform","Normal","Normal"]
    assert result[-1]["distribution"]["sigma_extreme"]==4

@pytest.mark.parametrize("field",["ref_object","inside_of"])
def test_nsc_same_batch_cycles_rejected_without_mutation(tmp_path,field):
    cell=NS(IsActive=True,IsReadOnly=False,Solve="Fixed")
    row=NS(RefObject=0,InsideOf=0,RefObjectCell=cell,InsideOfCell=cell)
    system=NS(Mode="NonSequential",NCE=NS(NumberOfObjects=2,GetObjectAt=lambda _:row))
    b=Backend(Config(Path("unused"),tmp_path),NS(system=system))
    b._mutate=lambda _:pytest.fail("invalid relations must be rejected before mutation")
    request=ObjectUpdates(changes=[dict(object=1,**{field:2}),dict(object=2,**{field:1})])
    with pytest.raises(ZemaxError,match="循环"):b.update_nsc_objects(request)

def test_asymmetric_pop_sampling_and_window_choices():
    q=COMMAND_MODELS["run_pop_convergence"].model_validate(dict(settings={},sampling_pairs=[["S_64x64","S_128x128"],["S_128x128","S_256x256"]],widths=[[4,8]],metric="integrated_power",absolute_tolerance=1e-5,relative_tolerance=1e-5))
    assert q.sampling_pairs[0]==("S_64x64","S_128x128")
    with pytest.raises(ValidationError):COMMAND_MODELS["run_pop"].model_validate(dict(save_output_beam=False,save_all_surfaces=True))
    with pytest.raises(ValidationError):COMMAND_MODELS["run_analysis"].model_validate(dict(request=dict(kind="zernike_fringe",maximum_terms=38)))

def test_raw_result_table_preserves_sample_values(tmp_path):
    result=export_saved_report(tmp_path,[dict(task_id="mc",result=dict(rows=[dict(index=0,values=[.1,None]),dict(index=1,values=[.3,.4])]))],"公差",False,["markdown"])
    path=next(Path(a["path"])for a in result["artifacts"]if a["path"].endswith("_rows.csv"))
    with path.open(encoding="utf-8-sig",newline="")as stream:rows=list(csv.DictReader(stream))
    assert json.loads(rows[1]["values"])[1]==pytest.approx(.4)

def test_report_loads_associated_analysis_without_native_calculation(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path));b.directory=tmp_path
    b.tasks={"parent":{"state":"succeeded","result":{"rows":[{"analysis_tasks":["child"],"metrics":[]}]}},"child":{"state":"succeeded","result":{"rows":[{"term":1,"value":.125,"unit":"waves"}]}}}
    result=b.export_evaluation_report(COMMAND_MODELS["export_evaluation_report"](task_ids=["parent"]))
    assert any(a["path"].endswith("child_rows.csv")for a in result["artifacts"])

def test_example_requests_match_worker_models():
    from zemax_mcp.config import PROJECT_ROOT
    workflows=json.loads((PROJECT_ROOT/"examples/requests/extended_workflows.json").read_text(encoding="utf-8"))
    for steps in workflows.values():
        for step in steps:
            model=COMMAND_MODELS[step["tool"]];args=step.get("arguments",{})
            if "request"not in model.model_fields:args=args.get("request",args.get("settings",args))
            model.model_validate(args)

@pytest.mark.parametrize("field,attr",[("ref_object","RefObject"),("inside_of","InsideOf")])
def test_nsc_reversing_relations_does_not_create_transient_cycle(tmp_path,field,attr,monkeypatch):
    from zemax_mcp import nsc_state
    from zemax_mcp.detectors import check_setting_readback
    monkeypatch.setattr(nsc_state,'check',lambda native,row,name,value:check_setting_readback(row,name,value))
    cell=NS(IsActive=True,IsReadOnly=False,Solve="Fixed")
    rows={}
    class Row:
        ObjectData=SourcesData=TypeData=None
        RefObjectCell=InsideOfCell=cell
        def __init__(self,index):self.index=index;self.values={"RefObject":0,"InsideOf":0}
        def __getattr__(self,name):return self.values[name]
        def __setattr__(self,name,value):
            if name not in {"RefObject","InsideOf"}:return object.__setattr__(self,name,value)
            cursor=value
            while cursor:
                if cursor==self.index:raise RuntimeError("native transient cycle")
                cursor=rows[cursor].values[name]
            self.values[name]=value
    rows.update({1:Row(1),2:Row(2)});rows[1].values[attr]=2
    b=Backend(Config(Path("unused"),tmp_path),NS(system=NS(Mode="NonSequential",NCE=NS(NumberOfObjects=2,GetObjectAt=rows.__getitem__))))
    b._mutate=lambda _:None;b.get_nsc_objects=lambda _:{}
    b.update_nsc_objects(ObjectUpdates(changes=[dict(object=2,**{field:1}),dict(object=1,**{field:0})]))
    assert getattr(rows[1],attr)==0 and getattr(rows[2],attr)==1
