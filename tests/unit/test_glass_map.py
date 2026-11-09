import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import parse_glass_map,parse_athermal_glass_map
from zemax_mcp.errors import ZemaxError


def test_glass_map_request_round_trips():
    request=RunAnalysis(request={"kind":"glass_map"})
    assert RunAnalysis.model_validate(request.model_dump())==request


def test_glass_map_parses_nd_abbe_points_and_report_count():
    text="""玻璃图数据

    玻璃名称         折射率          阿贝数
        BK7G18       1.51975         63.58
          N-BK7       1.51680         64.17
找到2玻璃。
"""
    result=parse_glass_map(text)
    assert result["analysis_kind"]=="glass_map"
    assert result["sample_count"]==result["native_report_count"]==2
    assert result["rows"][0]==dict(index=0,material="BK7G18",refractive_index_nd=1.51975,abbe_vd=63.58,source_line=4)
    scatter=result["scatter"][0]
    assert scatter["x_label"]=="Abbe number Vd"
    assert scatter["y_label"]=="Refractive index Nd"
    assert scatter["points"][1]==dict(x=64.17,y=1.5168,label="N-BK7")
    assert scatter["x_axis_direction"]=="decreasing_left_to_right"


@pytest.mark.parametrize("text",[
    "unrelated report\n",
    "玻璃图数据\n玻璃名称 折射率\nBK7G18 1.51975 63.58\n",
    "玻璃图数据\n玻璃名称 折射率 阿贝数\nBK7G18 NaN 63.58\n",
    "玻璃图数据\n玻璃名称 折射率 阿贝数\nBK7G18 1.51975 0\n",
])
def test_glass_map_rejects_unrecognized_or_invalid_report(text):
    with pytest.raises(ZemaxError):
        parse_glass_map(text)


def test_glass_map_rejects_untyped_selection_fields():
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind":"glass_map","catalog":"SCHOTT"})


def test_athermal_glass_map_request_and_native_power_scales():
    request=RunAnalysis(request={"kind":"athermal_glass_map"})
    assert RunAnalysis.model_validate(request.model_dump())==request
    text="""无热玻璃图数据

最小波长: 0.4800
中心波长 : 0.5500
最大波长: 0.6500

    玻璃名称       有色的光焦 xE-3    热的光焦 xE-6
       N-BK7            1.25000           -3.25
         F2            -4.50000            2.00
"""
    result=parse_athermal_glass_map(text)
    assert result["analysis_kind"]=="athermal_glass_map"
    assert result["wavelength_conditions"]==dict(minimum=.48,center=.55,maximum=.65)
    assert result["sample_count"]==2
    assert result["rows"][0]["material"]=="N-BK7"
    assert result["rows"][0]["chromatic_power"]==pytest.approx(.00125)
    assert result["rows"][0]["thermal_power_per_celsius"]==pytest.approx(-3.25e-6)
    assert result["scatter"][0]["points"][0]==dict(x=.00125,y=-3.25e-6,label="N-BK7")


@pytest.mark.parametrize("text",[
    "other report\n",
    "无热玻璃图数据\n玻璃名称 有色的\nN-BK7 1 2\n",
    "无热玻璃图数据\n玻璃名称 有色的 热的\nN-BK7 NaN 2\n",
    "无热玻璃图数据\n最小波长: NaN\n玻璃名称 有色的 热的\nN-BK7 1 2\n",
])
def test_athermal_glass_map_rejects_unrecognized_or_invalid_report(text):
    with pytest.raises(ZemaxError):
        parse_athermal_glass_map(text)
