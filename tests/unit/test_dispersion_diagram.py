import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import parse_dispersion_diagram,parse_dispersion_vs_wavelength
from zemax_mcp.errors import ZemaxError


def test_dispersion_diagram_request_is_typed_and_round_trips():
    request=RunAnalysis(request={"kind":"dispersion_diagram"})
    assert request.request.kind=="dispersion_diagram"
    assert RunAnalysis.model_validate(request.model_dump())==request


def test_dispersion_diagram_parses_native_material_columns_and_environment():
    text="""折射率 vs. 波长
温度: 20.0000 摄氏度
压强   : 1.0000 大气压
波长：µm
波长\t              BK7G18\tF_SILICA\t
 0.4000000\t1.5340805\t1.4701161\t
 0.5000000\t1.5214145\t1.4623265\t
 0.8000000\t1.5136518\t1.4533173\t
"""
    result=parse_dispersion_diagram(text)
    curve=result["series"][0]
    assert result["analysis_kind"]=="dispersion_diagram"
    assert result["sample_count"]==3
    assert curve["labels"]==["BK7G18","F_SILICA"]
    assert curve["x"]==[.4,.5,.8]
    assert curve["y"][0]==[1.5340805,1.4701161]
    assert curve["x_unit"]=="micrometers"
    assert curve["value_units"]==["dimensionless","dimensionless"]
    assert result["environment"]==dict(temperature_c=20.,pressure_atm=1.,source="native report preamble")


@pytest.mark.parametrize("text",[
    "unrelated report\n",
    "折射率 vs. 波长\n波长：µm\n",
    "折射率 vs. 波长\n波长\tBK7G18\n0.4 1.5\n",
    "折射率 vs. 波长\n波长\tBK7G18\n0.4 1.5\n0.3 1.4\n",
    "折射率 vs. 波长\n波长\tBK7G18\n0.4 NaN\n0.5 1.4\n",
])
def test_dispersion_diagram_rejects_invalid_native_text(text):
    with pytest.raises(ZemaxError):
        parse_dispersion_diagram(text)


def test_dispersion_diagram_rejects_malformed_row_inside_native_table():
    text="折射率 vs. 波长\n波长：µm\n波长\tBK7G18\n0.4 1.5\n0.5 NaN\n0.6 1.4\n"
    with pytest.raises(ZemaxError):
        parse_dispersion_diagram(text)


def test_dispersion_diagram_does_not_accept_untyped_fields():
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind":"dispersion_diagram","material":"BK7G18"})


def test_dispersion_vs_wavelength_request_is_typed_and_round_trips():
    request=RunAnalysis(request={"kind":"dispersion_vs_wavelength"})
    assert request.request.kind=="dispersion_vs_wavelength"
    assert RunAnalysis.model_validate(request.model_dump())==request


def test_dispersion_vs_wavelength_parses_inverse_micrometer_values():
    text="""色散 vs. 波长
温度: 20.0000 摄氏度
压强   : 1.0000 大气压
波长：µm
色散：1/um
波长\tBK7G18\t
0.4000000\t-0.1371622\t
0.4040000\t-0.1326835\t
0.4080000\t-0.1284159\t
"""
    result=parse_dispersion_vs_wavelength(text)
    curve=result["series"][0]
    assert result["analysis_kind"]=="dispersion_vs_wavelength"
    assert result["sample_count"]==3
    assert curve["labels"]==["BK7G18"]
    assert curve["x_unit"]=="micrometers"
    assert curve["value_units"]==["1/micrometer"]
    assert curve["y"]==[[-.1371622],[-.1326835],[-.1284159]]
    assert result["environment"]["temperature_c"]==20
    assert result["environment"]["pressure_atm"]==1


@pytest.mark.parametrize("text",[
    "折射率 vs. 波长\n波长：µm\n色散：1/um\n波长\tBK7G18\n0.4 -.1\n0.5 -.2\n",
    "色散 vs. 波长\n波长：µm\n色散：1/mm\n波长\tBK7G18\n0.4 -.1\n0.5 -.2\n",
    "色散 vs. 波长\n波长：µm\n色散：1/um\n波长\tBK7G18\n0.4 -.1\n0.3 -.2\n",
])
def test_dispersion_vs_wavelength_rejects_wrong_report_or_units(text):
    with pytest.raises(ZemaxError):
        parse_dispersion_vs_wavelength(text)
