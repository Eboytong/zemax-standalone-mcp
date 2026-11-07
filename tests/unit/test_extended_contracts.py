import math,struct
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.models import COMMAND_MODELS,SolveSpec
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.configuration_models import ConfigurationPatch
from zemax_mcp.errors import ZemaxError
from zemax_mcp.physical_optics import read_beam
from zemax_mcp.tolerance_models import ToleranceSummary

@pytest.mark.parametrize("command,args",[
 ("run_global_optimization",{"runtime_seconds":0}),
 ("run_hammer_optimization",{"runtime_seconds":float("nan")}),
 ("run_tolerance_analysis",{"mode":"inverse_limit"}),
 ("run_tolerance_analysis",{"mode":"monte_carlo","samples":2,"save_samples":3}),
 ("generate_tolerances",{}),
 ("run_nsc_ray_trace",{"split_rays":True}),
 ("run_batch_ray_trace",{"input_mode":"Direct","rays":[{"px":0}]}),
 ("run_batch_ray_trace",{"input_mode":"Direct","rays":[{"x":0,"y":0,"z":0,"l":0,"m":0,"n":2}]}),
 ("run_batch_ray_trace",{"rays":[{}],"polarization":{"jx":0,"jy":0}}),
 ("run_batch_ray_trace",{"rays":[{}],"polarization":{},"opd":True}),
 ("run_pop",{"x_width":0}),
 ("get_beam_file",{"path":"a.zbf","count":1001}),
 ("run_cad_export",{"path":"a.step","number_of_rays":1001}),
 ("run_analysis",{"request":{"kind":"fft_psf","sampling":"S_16384x16384"}}),
 ("run_analysis",{"request":{"kind":"geometric_mtf","image_delta":1}}),
 ("run_analysis",{"request":{"kind":"zernike_fringe","obscuration":.5}}),
 ("run_configuration_evaluation",{"configurations":[1,1],"evaluation":{"merit":True}}),
])
def test_invalid_extended_request(command,args):
    with pytest.raises(ValidationError):COMMAND_MODELS[command].model_validate(args)

def test_marginal_zone_defaults_and_negative_range():
    assert SolveSpec(mode="marginal_ray_height",height=0).pupil_zone==0
    assert SolveSpec(mode="marginal_ray_height",height=0,pupil_zone=-.7).pupil_zone==-.7

def test_multistart_surface_omission_roundtrip():
    q=COMMAND_MODELS["run_multistart_optimization"].model_validate(dict(starts=[[dict(surface=1,radius=10)]],evaluation=dict(merit=True)))
    assert COMMAND_MODELS["run_multistart_optimization"].model_validate(q.model_dump(exclude_unset=True)).starts[0][0].radius==10

def test_mce_batch_cycle_rejected_before_mutation(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path))
    cell=NS(Solve="Fixed",IsActive=True,IsReadOnly=False,Header="c")
    row=NS(GetOperandCell=lambda _:cell)
    b.native=NS(system=NS(MCE=NS(NumberOfOperands=1,NumberOfConfigurations=2,GetOperandAt=lambda _:row)))
    q=ConfigurationPatch(operands=[dict(operand=1,cells=[dict(configuration=1,solve=dict(mode="config_pickup",operand=1,configuration=2)),dict(configuration=2,solve=dict(mode="config_pickup",operand=1,configuration=1))])])
    with pytest.raises(ZemaxError,match="循环"):b._validate_config_graph(q,2)
    assert b.revision==0

def test_tolerance_summary_uses_requested_denominator(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path))
    b._full_result=lambda _:{"task":{"kind":"tolerance_analysis"},"rows":[{"index":0,"values":[1.]},{"index":1,"values":[None]},{"index":2,"values":[3.]}],"summary":{"requested_samples":4,"native_traceable_trials":4,"columns":[{"is_operand":False}]}}
    r=b.summarize_tolerance_results(ToleranceSummary(task_id="t",criterion_column=0,threshold=2,unit="mm"))
    assert r["pass_fraction_of_requested"]==.25 and r["missing"]==1 and r["nonfinite_indices"]==[1]
    assert r["quantiles"]["0.5"]==2

def test_tolerance_summary_rejects_operand_column(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path));b._full_result=lambda _:{"task":{"kind":"tolerance_analysis"},"summary":{"columns":[{"is_operand":True}]}}
    with pytest.raises(ZemaxError):b.summarize_tolerance_results(ToleranceSummary(task_id="t",criterion_column=0,threshold=1,unit="mm"))

def test_zbf_sample_pages_and_components(tmp_path):
    path=tmp_path/"sample.zbf"
    header=struct.pack("<9i20d",1,2,2,1,0,0,0,0,0,*([1.]*20))
    ex=[(float(i),float(-i))for i in range(4)];ey=[(10.+i,20.+i)for i in range(4)]
    path.write_bytes(header+b"".join(struct.pack("<dd",*x)for x in ex+ey))
    r=read_beam(path,1,2)
    assert r["rows"][0]==dict(index=1,ex_real=1.,ex_imag=-1.,ey_real=11.,ey_imag=21.)
    assert r["next_start"]==3 and r["total"]==4

def test_zbf_unknown_format_is_explicit(tmp_path):
    path=tmp_path/"bad.zbf";path.write_bytes(struct.pack("<9i20d",99,2,2,0,0,0,0,0,0,*([0.]*20)))
    with pytest.raises(ZemaxError,match="version=1"):read_beam(path)


@pytest.mark.parametrize("traceable",[None,0,1,True,3])
def test_tolerance_summary_requires_known_all_traceable(tmp_path,traceable):
    b=Backend(Config(Path("unused"),tmp_path))
    b._full_result=lambda _:{"task":{"kind":"tolerance_analysis"},"rows":[{"index":0,"values":[1.]},{"index":1,"values":[None]}],"summary":{"requested_samples":2,"native_traceable_trials":traceable,"columns":[{"is_operand":False}]}}
    with pytest.raises(ZemaxError)as error:
        b.summarize_tolerance_results(ToleranceSummary(task_id="t",criterion_column=0,threshold=2,unit="mm"))
    assert error.value.code=="SAMPLE_STATUS_UNAVAILABLE"


def test_tolerance_summary_large_finite_mean(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path))
    b._full_result=lambda _:{"task":{"kind":"tolerance_analysis"},"rows":[{"index":0,"values":[1e308]},{"index":1,"values":[1e308]}],"summary":{"requested_samples":2,"native_traceable_trials":2,"columns":[{"is_operand":False}]}}
    r=b.summarize_tolerance_results(ToleranceSummary(task_id="t",criterion_column=0,threshold=1e308,unit="mm"))
    assert r["mean"]==1e308 and r["quantiles"]["0.5"]==1e308
    assert r["pass_fraction_scope"]=="complete_requested_sample_set"
