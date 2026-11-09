"""Offline checks for catalog matching and the athermal display-scale contract.

No OpticStudio instance is created. Catalog text is parsed in memory; the
athermal cases use the exact native header layout (`玻璃名称  光焦 xE-3
光焦 xE-6`) recorded in the 2026-11-08 native text.
"""
from decimal import Decimal

import pytest

from zemax_mcp.analyses import parse_athermal_glass_map
from zemax_mcp.errors import ZemaxError
from tests.support.material_catalog_reference import (
    ND_TOLERANCE, VD_TOLERANCE, catalog_selection, match_rows, parse_catalog,
)

CATALOG = """CC TEST preferred, inquiry, test catalog
NM LF5HTi 2 581409.322 1.58144 40.89 0 1
NM LITHOSIL-Q 2.00000E+00 458678.220 1.45844 67.83 0 2
NM BOUNDARY 2 159196.5 1.591965 48.500 0 1
GC comment row that is not a material
"""


@pytest.fixture()
def catalog():
    return parse_catalog(CATALOG, path="TEST.AGF")


def test_catalog_identity_uses_selection_path_header_and_names(catalog):
    identity, entries = catalog
    assert identity == dict(path="TEST.AGF", header="TEST preferred, inquiry, test catalog", material_count=3)
    assert sorted(entry["catalog_name"] for entry in entries.values()) == ["BOUNDARY", "LF5HTi", "LITHOSIL-Q"]
    assert catalog_selection(["SCHOTT"]) == dict(material_catalogs=["SCHOTT"],
        source="system settings material_catalogs (no per-analysis catalog selector)")


def test_catalog_reads_scientific_formula_and_keeps_catalog_spelling(catalog):
    _, entries = catalog
    assert entries["LITHOSIL-Q"] == dict(catalog_name="LITHOSIL-Q", formula=2,
        refractive_index_nd=Decimal("1.45844"), abbe_vd=Decimal("67.83"))
    assert entries["LF5HTI"]["catalog_name"] == "LF5HTi"


def test_report_upper_case_names_match_mixed_case_catalog_names(catalog):
    _, entries = catalog
    result = match_rows([dict(material="LF5HTI", refractive_index_nd=1.58144, abbe_vd=40.89)], entries)
    assert not result["mismatched"] and not result["missing"]
    assert result["matched"][0] == dict(report_name="LF5HTI", catalog_name="LF5HTi",
        nd_error=Decimal("0E-8"), vd_error=Decimal("0.00"))


def test_display_rounding_boundary_is_exact_decimal(catalog):
    _, entries = catalog
    inside = match_rows([dict(material="BOUNDARY", refractive_index_nd=1.59196, abbe_vd=48.5)], entries)
    assert not inside["mismatched"]
    assert inside["matched"][0]["nd_error"] == ND_TOLERANCE
    outside = match_rows([dict(material="BOUNDARY", refractive_index_nd=1.59197, abbe_vd=48.506)], entries)
    assert outside["mismatched"][0]["report_name"] == "BOUNDARY"
    assert outside["mismatched"][0]["vd_error"] == Decimal("0.006")


def test_unknown_material_is_reported_with_native_name(catalog):
    _, entries = catalog
    result = match_rows([dict(material="NOT-IN-CATALOG", refractive_index_nd=1.5, abbe_vd=50)], entries)
    assert result["missing"] == [dict(report_name="NOT-IN-CATALOG")]
    assert (result["nd_tolerance"], result["vd_tolerance"]) == (str(ND_TOLERANCE), str(VD_TOLERANCE)) == ("0.000005", "0.005")


ATHERMAL_NATIVE = """无热玻璃图数据

最小波长:    0.5500
中心波长 :    0.5500
最大波长:    0.5500

                   有色的       热的
    玻璃名称    光焦 xE-3    光焦 xE-6
        BK7G18\t      -0.00000\t         -1.65
            F2\t      -0.00000\t         -1.41
找到2玻璃。
"""


def test_athermal_scales_come_from_the_native_header():
    result=parse_athermal_glass_map(ATHERMAL_NATIVE)
    assert result["native_display_scales"]==dict(chromatic_power="1e-3",thermal_power="1e-6")
    assert result["native_display_scales_source"]=="native report header (光焦 xE-n)"
    assert result["native_header"].split()[:2]==["玻璃名称","光焦"]
    assert result["native_report_count"]==result["sample_count"]==2
    assert result["wavelength_conditions"]==dict(minimum=.55,center=.55,maximum=.55)
    assert result["rows"][1]["thermal_power_per_celsius"]==pytest.approx(-1.41e-6)
    assert result["scatter"][0]["x_axis_display_scale"]=="1e-3"
    assert result["scatter"][0]["y_axis_display_scale"]=="1e-6"


def test_athermal_non_default_display_scale_is_applied_not_assumed():
    text="""无热玻璃图数据

                   有色的       热的
    玻璃名称    光焦 xE-4    光焦 xE-7
        BK7G18        12.50         -32.5
"""
    result=parse_athermal_glass_map(text)
    assert result["native_display_scales"]==dict(chromatic_power="1e-4",thermal_power="1e-7")
    assert result["rows"][0]["chromatic_power"]==pytest.approx(1.25e-3)
    assert result["rows"][0]["thermal_power_per_celsius"]==pytest.approx(-3.25e-6)


def test_athermal_header_without_display_scale_is_a_report_contract_error():
    text="""无热玻璃图数据
    玻璃名称    有色的光焦    热的光焦
        BK7G18        1.25         -3.25
"""
    with pytest.raises(ZemaxError) as excinfo:
        parse_athermal_glass_map(text)
    assert excinfo.value.code=="INVALID_RESULT_DATA"
    assert excinfo.value.details["native_scale_source"]=="native report header"
    assert excinfo.value.details["native_header"].split()[0]=="玻璃名称"


@pytest.mark.parametrize("chromatic,thermal",[("xE9999","xE-6"),("xE-9999","xE-6"),("xE-3","xE9999")])
def test_athermal_out_of_range_display_scale_is_invalid_result_data(chromatic,thermal):
    text=f"""无热玻璃图数据

                   有色的       热的
    玻璃名称    光焦 {chromatic}    光焦 {thermal}
        BK7G18        1.25         -3.25
"""
    with pytest.raises(ZemaxError) as excinfo:
        parse_athermal_glass_map(text)
    assert excinfo.value.code=="INVALID_RESULT_DATA"
    assert excinfo.value.details["native_header"].split()[:2]==["玻璃名称","光焦"]
    assert excinfo.value.details["scale_exponents"]==[chromatic[2:],thermal[2:]]
