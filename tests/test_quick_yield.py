import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES


def test_quick_yield_request_and_native_analysis_registration():
    request = RunAnalysis(request={"kind": "quick_yield"})
    assert request.request.field == 1
    assert request.request.wavelength == 1
    assert request.request.monte_carlo_samples == 1000
    assert ANALYSES[request.request.kind] == "QuickYield"


@pytest.mark.parametrize("patch", [
    {"field": 0},
    {"wavelength": 0},
    {"configuration": -1},
    {"monte_carlo_samples": 0},
    {"monte_carlo_samples": 999},
    {"pupil_sampling": 11},
    {"statistic": "Gaussian"},
    {"precision": "Ultra"},
    {"compensator_strategy": "Unknown"},
])
def test_quick_yield_rejects_invalid_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "quick_yield", **patch})


def test_tolerance_yield_and_histogram_requests():
    yield_request = RunAnalysis(request={"kind": "tolerance_yield", "operand": 0})
    histogram = RunAnalysis(request={"kind": "tolerance_histogram", "operand": 0,
                                    "minimum": -0.02, "maximum": 0.02, "bins": 25})
    assert yield_request.request.tolerance_file is None
    assert histogram.request.maximum > histogram.request.minimum
    assert ANALYSES["tolerance_yield"] == "ToleranceYield"
    assert ANALYSES["tolerance_histogram"] == "ToleranceHistogram"


@pytest.mark.parametrize("payload", [
    {"kind": "tolerance_histogram", "minimum": 1, "maximum": 1},
    {"kind": "tolerance_histogram", "minimum": 2, "maximum": 1},
    {"kind": "tolerance_histogram", "bins": 0},
    {"kind": "tolerance_yield", "operand": -1},
])
def test_tolerance_distribution_requests_reject_invalid_ranges(payload):
    with pytest.raises(ValidationError):
        RunAnalysis(request=payload)


@pytest.mark.parametrize('index,count,expected',[(0,1,1),(0,2,1),(1,2,2)])
def test_native_operand_one_based(index,count,expected):
    from zemax_mcp.analyses import tolerance_operand_number
    assert tolerance_operand_number(index,count)==expected


@pytest.mark.parametrize('index,count',[(0,0),(1,1),(2,2)])
def test_native_operand_bounds(index,count):
    from zemax_mcp.analyses import tolerance_operand_number
    from zemax_mcp.errors import ZemaxError
    with pytest.raises(ZemaxError)as e:tolerance_operand_number(index,count)
    assert e.value.code=='INDEX_OUT_OF_RANGE'


@pytest.mark.parametrize('drift',['Precision','field_mode','field','wavelength'])
def test_quick_yield_final_combination_rejects_drift(monkeypatch,drift):
    from types import SimpleNamespace as NS
    from zemax_mcp.analyses import verify_quick_yield
    from zemax_mcp.errors import ZemaxError
    from zemax_mcp import imaging
    q=RunAnalysis(request={'kind':'quick_yield'}).request
    settings=NS(QYField=NS(IsFieldUser=drift!='field_mode',GetFieldUser=lambda:2 if drift=='field' else 1),
                Wavelength=NS(GetWavelengthNumber=lambda:2 if drift=='wavelength' else 1))
    def check(native,s,name,value):
        if drift==name:raise ZemaxError('SETTING_REJECTED','final setting changed',setting=name)
    monkeypatch.setattr(imaging,'check',check)
    with pytest.raises(ZemaxError) as exc:verify_quick_yield(None,settings,q)
    assert exc.value.code=='SETTING_REJECTED'


def test_quick_yield_result_preserves_native_values_and_declares_units():
    from zemax_mcp.analyses import describe_quick_yield
    q=RunAnalysis(request={'kind':'quick_yield'}).request.model_dump()
    curve=dict(series=0,labels=['native yield label'],x=[.01,.02],y=[[1],[99]])
    data=dict(series=[curve]);describe_quick_yield(data,q)
    assert curve['x']==[.01,.02] and curve['y']==[[1],[99]]
    assert curve['labels']==['native yield label'] and curve['x_unit']=='waves'
    assert curve['value_units']==['percent'] and data['evaluation']['field_selection']==1
    assert 'sensitivity fit'in data['evaluation']['source']
    assert data['evaluation']['reference_equivalence']['status'].startswith('controlled empirical')


@pytest.mark.parametrize('values',[[[None]],[[101]],[[float('nan')]],[[1,2]]])
def test_quick_yield_rejects_invalid_yield_result(values):
    from zemax_mcp.analyses import describe_quick_yield
    from zemax_mcp.errors import ZemaxError
    with pytest.raises(ZemaxError) as exc:
        describe_quick_yield(dict(series=[dict(series=0,labels=['yield'],x=[.01],y=values)]),{})
    assert exc.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('x,y',[([],[]),([None],[[1]]),([-1],[[1]]),([float('nan')],[[1]]),([.1,.2],[[1]])])
def test_quick_yield_rejects_invalid_wavefront_axis(x,y):
    from zemax_mcp.analyses import describe_quick_yield
    from zemax_mcp.errors import ZemaxError
    with pytest.raises(ZemaxError)as exc:
        describe_quick_yield(dict(series=[dict(series=0,labels=['yield'],x=x,y=y)]),{})
    assert exc.value.code=='INVALID_RESULT_DATA'and exc.value.details['native_x']==x


def test_quick_yield_source_wavelength_identity_is_distinct_from_reference_equivalence():
    from zemax_mcp.analyses import describe_quick_yield
    q=RunAnalysis(request={'kind':'quick_yield','wavelength':1}).request.model_dump()
    data=dict(series=[dict(series=0,labels=['yield'],x=[.1],y=[[1]])])
    settings=dict(wavelengths=[dict(number=1,wavelength_um=.48,primary=False),dict(number=2,wavelength_um=.55,primary=True)])
    describe_quick_yield(data,q,settings)
    assert data['evaluation']['source_wavelengths']==dict(primary_number=2,selected_number=1,selected_um=.48)
    assert settings['wavelengths'][1]['primary']is True
