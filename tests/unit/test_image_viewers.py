"""Offline tests for the D005 image viewers/analyses surface and report parsers."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from zemax_mcp import image_viewers as iv  # noqa: E402
from zemax_mcp.errors import ZemaxError  # noqa: E402

KINDS = ["light_source", "bitmap_file_viewer", "beam_file_viewer",
         "partially_coherent_image", "extended_diffraction_image", "geometric_bitmap_image"]
EVIDENCE = ROOT / ".local/evidence/development/CV-02/probe442-b005"


def pc_text(pixels=(3, 3), imaging="非相干成像", aberration="包含像差", body=None):
    if body is None:
        body = "\n".join("\t".join("1.0E-01" for _ in range(pixels[0])) for _ in range(pixels[1]))
    return (
        "部分相干成像分析数据列表\n\n文件 : C:\\work\\lens.zos\n题目: TEST.\n日期 : 2026/11/8\n\n\n"
        f"0.5500 μm对于0.00 (度)。\n宽度是 1.8571 毫米, {pixels[0]} 以 {pixels[1]}像素.\n"
        f"{imaging}\n{aberration}\n" + body + "\n"
    )


def xse_text(pixels=(4, 2), gap="乘", body_rows=None):
    body_rows = pixels[1] if body_rows is None else body_rows
    body = "\n".join("\t".join("2.0E-03" for _ in range(pixels[0])) for _ in range(body_rows))
    return (
        "扩展衍射像分析数据清单\n\n文件 : C:\\work\\lens.zos\n题目: TEST.\n日期 : 2026/11/8\n\n\n"
        f"0.5500 µm. 位置: 0.00 (度)\n光源 : 0.0500 毫米 宽, 7 {gap} 7 像素\n"
        f"显示: is 0.1000 毫米 宽, {pixels[0]} {gap} {pixels[1]} 像素\n包含像差\n" + body + "\n"
    )


# --------------------------------------------------------------- interface facts


@pytest.mark.parametrize("kind", KINDS)
def test_analysis_ids_are_documented(kind):
    name, number = iv.ANALYSIS_IDS[kind]
    assert isinstance(number, int) and 61 <= number <= 96
    assert iv.analysis_id(kind) == number
    assert name.endswith(("Analysis", "Viewer"))


def test_runtime_metadata_distinguishes_topic_properties_from_documented_cfg():
    for kind in KINDS:
        surface=iv.settings_surface(kind)
        assert surface['settings_class']=='AS_Default'
        assert surface['api_properties'] is False
        assert surface['writable'] is False
        assert surface['documented_cfg_keys_available']==bool(surface['modify_settings'])
        assert surface['evidence']
    assert iv.settings_surface('extended_diffraction_image')['cfg_adoption_status']=='verified_subset'


def test_modify_settings_use_only_documented_prefixes():
    prefixes = {"extended_diffraction_image": "EXD_", "partially_coherent_image": "PCI_",
                "geometric_bitmap_image": "GBM_"}
    for kind, keys in iv.MODIFY_SETTINGS.items():
        if not keys:
            assert kind in {"light_source", "bitmap_file_viewer", "beam_file_viewer"}
            continue
        assert all(key.startswith(prefixes[kind]) for key in keys), kind
    assert set(iv.MODIFY_SETTINGS["extended_diffraction_image"]) == {
        "EXD_DISPLAYSIZE", "EXD_FIELD", "EXD_FILESIZE", "EXD_WAVE"}
    assert set(iv.MODIFY_SETTINGS["partially_coherent_image"]) == {
        "PCI_FIELD", "PCI_FILESIZE", "PCI_WAVE", "PCI_RESAMPLE", "PCI_RSNX",
        "PCI_RSNY", "PCI_RSDCX", "PCI_RSDCY", "PCI_RSDLX", "PCI_RSDLY"}
    assert set(iv.MODIFY_SETTINGS["geometric_bitmap_image"]) == {
        "GBM_FIELDSIZE", "GBM_RAYS", "GBM_XPIX", "GBM_YPIX", "GBM_XSIZ",
        "GBM_YSIZ", "GBM_INPUT", "GBM_OUTPUT", "GBM_SURFACE", "GBM_ROTATION"}


def test_foreign_key_prefixes_are_never_claimed_by_our_kinds():
    claimed = {key for keys in iv.MODIFY_SETTINGS.values() for key in keys}
    for prefix, owner in iv.FOREIGN_PREFIXES.items():
        assert not any(key.startswith(prefix) for key in claimed), (prefix, owner)
    for kind, keys in iv.MODIFY_SETTINGS.items():
        for key in keys:
            assert key[:4] == iv.KEY_ATTRIBUTION[kind]["prefix"][:4]


def test_attribution_records_the_manual_lines_that_were_checked():
    for kind in ("extended_diffraction_image", "partially_coherent_image", "geometric_bitmap_image"):
        record = iv.KEY_ATTRIBUTION[kind]
        assert record["key_lines"] and record["heading_lines"]
        assert record["heading"].endswith(("Analysis", "Energy", "Map"))
    assert iv.KEY_ATTRIBUTION["extended_diffraction_image"]["key_lines"] == "45-48"
    assert iv.KEY_ATTRIBUTION["partially_coherent_image"]["key_lines"] == "274-283"
    assert iv.KEY_ATTRIBUTION["geometric_bitmap_image"]["key_lines"] == "127-136"


def test_metadata_is_not_wired_into_product_modules():
    product = ["analyses.py", "analysis_models.py", "backend.py", "imaging.py",
               "polarization_topics.py", "models.py", "server.py"]
    root = ROOT / "src" / "zemax_mcp"
    for name in product:
        path = root / name
        if path.is_file():
            assert "image_viewers" not in path.read_text(encoding="utf-8"), name


def test_unknown_kind_and_file_raise():
    with pytest.raises(ZemaxError) as caught:
        iv.analysis_id("nope")
    assert caught.value.code == "UNKNOWN_ANALYSIS"
    with pytest.raises(ZemaxError) as caught:
        iv.source_file_identity("scan.tif")
    assert caught.value.code == "UNKNOWN_SOURCE_FILE"


# ------------------------------------------------------------------ file identity


def test_source_file_identity_containers_and_semantics():
    zbf = iv.source_file_identity("Beam.ZBF")
    assert zbf["container"] == "pop" and zbf["value_semantics"] == "relative_complex_amplitude"
    assert zbf["editable_in_place"] is False
    ima = iv.source_file_identity("letterf.ima")
    assert ima["container"] == "images" and ima["value_semantics"] == "relative_irradiance"
    assert ima["editable_in_place"] is True
    assert iv.source_file_identity("map.bim")["editable_in_place"] is False
    assert iv.source_file_identity("scene.bmp")["value_semantics"] == "rgb_intensity"
    assert iv.source_file_identity("rays.dat")["value_semantics"] == "source_ray_list_flux"
    assert iv.source_file_identity("rays.sdf")["value_semantics"] == "source_ray_list_spectral"
    assert iv.source_file_identity("rays.tm25ray")["container"] == "any"


@pytest.mark.parametrize("kind,accepted,rejected", [
    ("light_source", "rays.dat", "letterf.ima"),
    ("bitmap_file_viewer", "photo.png", "letterf.ima"),
    ("beam_file_viewer", "beam.zbf", "photo.png"),
    ("partially_coherent_image", "letterf.ima", "rays.dat"),
    ("extended_diffraction_image", "map.bim", "beam.zbf"),
    ("geometric_bitmap_image", "photo.jpg", "beam.zbf"),
])
def test_accepts_source_matches_documented_inputs(kind, accepted, rejected):
    assert iv.accepts_source(kind, accepted) is True
    assert iv.accepts_source(kind, rejected) is False


def test_partially_coherent_accepts_zbf_but_extended_does_not():
    assert iv.accepts_source("partially_coherent_image", "beam.zbf") is True
    assert iv.accepts_source("extended_diffraction_image", "beam.zbf") is False


# ----------------------------------------------------------------- declared scope


@pytest.mark.parametrize("kind", KINDS)
def test_declared_scope_stays_unverified(kind):
    scope = iv.declared_scope(kind)
    assert scope["verified"] is False
    assert scope["kind"] == kind and scope["inputs"] and scope["result_channel"]


def test_scope_records_corrected_input_definitions():
    source = iv.declared_scope("light_source")
    assert "finite conjugate systems only" in source["notes"]
    assert "SDF/TM25RAY always use file wavelengths" in source["wavelengths"]
    extended = iv.declared_scope("extended_diffraction_image")
    assert extended["coherence"].startswith("fully coherent or fully incoherent")
    coherent = iv.declared_scope("partially_coherent_image")
    assert any("ZBF complex amplitude" in item for item in coherent["inputs"])
    assert any("not a coherence length" in note for note in coherent["notes"])
    viewer = iv.declared_scope("bitmap_file_viewer")
    assert "no numeric grid" in viewer["result_channel"]


def test_result_channels_match_the_saved_probes():
    assert iv.RESULT_CHANNELS["light_source"]["messages"] == 1
    assert iv.RESULT_CHANNELS["light_source"]["data_grids"] == 0
    assert iv.RESULT_CHANNELS["bitmap_file_viewer"]["text_export"] is False
    assert iv.RESULT_CHANNELS["partially_coherent_image"]["data_grids"] == 1
    assert iv.RESULT_CHANNELS["extended_diffraction_image"]["data_grids"] == 1
    assert iv.RESULT_CHANNELS["beam_file_viewer"]["data_grids"] == 1
    assert iv.RESULT_CHANNELS["geometric_bitmap_image"]["data_grids"] == 0
    for kind in KINDS:
        assert iv.declared_scope(kind)["result_channel"]


def test_geometric_bitmap_contract_uses_native_bitmap_pixel_and_ray_semantics():
    from zemax_mcp.analyses import ANALYSES
    from zemax_mcp.analysis_models import GeometricBitmapImage

    assert ANALYSES["geometric_bitmap_image"] == "GeometricBitmapImageAnalysis"
    model = GeometricBitmapImage(kind="geometric_bitmap_image", input_file="scene.bmp")
    assert model.x_pixels == model.y_pixels == 256 and model.rotation == 0
    assert {"input_file", "field_size", "rays_per_pixel", "x_pixel_size", "y_pixel_size"} <= set(type(model).model_fields)


def test_parse_extended_report_records_physical_axes_and_pixel_sizes():
    record = iv.parse_extended_diffraction_text(xse_text(pixels=(4, 2)))
    assert record["size_units"] == "mm" and record["wavelength_units"] == "um"
    assert record["source_pixel_size"] == pytest.approx(0.05 / 7)
    assert record["display_pixel_size"] == pytest.approx(0.1 / 4)
    assert record["cell_count"] == 8
    assert record["value_semantics"] == "relative_intensity"
    assert record["minimum"] == pytest.approx(2.0e-03)
    assert record["axes"]["x"].startswith("image space")


def test_parse_partially_coherent_records_pixel_size():
    record = iv.parse_partially_coherent_text(pc_text(pixels=(3, 3)))
    assert record["pixel_size"] == pytest.approx(1.8571 / 3)
    assert record["cell_count"] == 9 and record["size_units"] == "mm"


def test_parser_rejects_non_finite_values():
    body = "1.0E-01\tNaN\n2.0E-01\t3.0E-01"
    with pytest.raises(ZemaxError) as caught:
        iv.parse_partially_coherent_text(pc_text(body=body))
    assert caught.value.code == "ANALYSIS_TEXT_NON_FINITE"


def test_parser_rejects_shape_mismatch_with_header():
    body = "\n".join("\t".join("1.0E-01" for _ in range(2)) for _ in range(2))
    with pytest.raises(ZemaxError) as caught:
        iv.parse_partially_coherent_text(pc_text(pixels=(3, 3), body=body))
    assert caught.value.code == "ANALYSIS_TEXT_SHAPE_MISMATCH"
    assert caught.value.details["grid"] == [2, 2]
    assert caught.value.details["header"] == [3, 3]

    with pytest.raises(ZemaxError) as caught:
        iv.parse_extended_diffraction_text(xse_text(pixels=(4, 2), body_rows=1))


# --------------------------------------------------------------------- parsers


def test_parse_partially_coherent_report():
    record = iv.parse_partially_coherent_text(pc_text(pixels=(3, 3)))
    assert record["wavelength_um"] == 0.55 and record["field_deg"] == 0.0
    assert record["pixels"] == [3, 3] and record["width"] == 1.8571
    assert record["imaging"] == "incoherent" and record["aberration_included"] is True
    assert record["row_count"] == 3 and record["column_count"] == 3
    assert record["normalization"] == "relative_intensity"


@pytest.mark.parametrize("imaging,expected", [
    ("非相干成像", "incoherent"), ("相干成像", "coherent"), ("部分相干成像", "partially_coherent")])
def test_parse_partially_coherent_imaging_types(imaging, expected):
    assert iv.parse_partially_coherent_text(pc_text(imaging=imaging))["imaging"] == expected


def test_parse_partially_coherent_diffraction_limited():
    record = iv.parse_partially_coherent_text(pc_text(aberration="衍射极限"))
    assert record["aberration_included"] is False


def test_parse_partially_coherent_rejects_ragged_grid():
    ragged = pc_text(body="1.0E-01\t2.0E-01\n3.0E-01")
    with pytest.raises(ZemaxError) as caught:
        iv.parse_partially_coherent_text(ragged)
    assert caught.value.code == "ANALYSIS_TEXT_RAGGED_GRID"


def test_parse_partially_coherent_rejects_empty_grid():
    with pytest.raises(ZemaxError) as caught:
        iv.parse_partially_coherent_text(pc_text(body="not numbers"))
    assert caught.value.code == "ANALYSIS_TEXT_NO_GRID"


def test_parse_partially_coherent_missing_header():
    with pytest.raises(ZemaxError) as caught:
        iv.parse_partially_coherent_text("nothing useful\n1.0 2.0\n")
    assert caught.value.code == "ANALYSIS_TEXT_NO_HEADER"


def test_parse_extended_diffraction_report():
    record = iv.parse_extended_diffraction_text(xse_text(pixels=(4, 2)))
    assert record["wavelength_um"] == 0.55 and record["field_deg"] == 0.0
    assert record["source_width"] == 0.05 and record["source_pixels"] == [7, 7]
    assert record["display_width"] == 0.1 and record["display_pixels"] == [4, 2]
    assert record["row_count"] == 2 and record["column_count"] == 4
    assert record["aberration_included"] is True


def test_parse_extended_diffraction_accepts_micro_sign_and_ascii_gap():
    record = iv.parse_extended_diffraction_text(xse_text(pixels=(2, 2), gap="x"))
    assert record["display_pixels"] == [2, 2]
    assert record["wavelength_um"] == 0.55


def test_parse_extended_diffraction_missing_header():
    with pytest.raises(ZemaxError) as caught:
        iv.parse_extended_diffraction_text("header only\n")
    assert caught.value.code == "ANALYSIS_TEXT_NO_HEADER"


def test_parse_light_source_message_is_a_documented_refusal():
    record = iv.parse_light_source_text("仅有限共轭系统可以使用该功能.\n")
    assert record["available"] is False and record["reason"] == "finite_conjugate_only"
    assert record["message"].startswith("仅有限共轭")


def test_parse_light_source_rejects_unknown_shape():
    with pytest.raises(ZemaxError) as caught:
        iv.parse_light_source_text("1.0E-01\t2.0E-01\n")
    assert caught.value.code == "ANALYSIS_TEXT_UNKNOWN_SHAPE"
    with pytest.raises(ZemaxError) as caught:
        iv.parse_light_source_text("   \n")
    assert caught.value.code == "ANALYSIS_TEXT_EMPTY"


def test_parse_report_dispatch_and_unknown_kind():
    assert iv.parse_report("light_source", "仅有限共轭系统可以使用该功能.")["reason"] == "finite_conjugate_only"
    with pytest.raises(ZemaxError) as caught:
        iv.parse_report("geometric_bitmap_image", "x")
    assert caught.value.code == "NO_ANALYSIS_TEXT_PARSER"


def png_bytes(width=4, height=3, bit_depth=8, color_type=2):
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([bit_depth, color_type, 0, 0, 0])
    return b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + ihdr + b"\x00\x00\x00\x00"


def bmp_bytes(width=5, height=-4, bit_depth=24):
    header = b"BM" + (54).to_bytes(4, "little") + b"\x00\x00\x00\x00" + (54).to_bytes(4, "little")
    dib = (40).to_bytes(4, "little") + width.to_bytes(4, "little", signed=True) + \
        height.to_bytes(4, "little", signed=True) + (1).to_bytes(2, "little") + bit_depth.to_bytes(2, "little")
    return header + dib


def jpeg_bytes(width=7, height=9):
    sof = b"\xff\xc0" + (11).to_bytes(2, "big") + bytes([8]) + height.to_bytes(2, "big") + \
        width.to_bytes(2, "big") + b"\x01\x01\x11\x00"
    return b"\xff\xd8" + b"\xff\xe0" + (16).to_bytes(2, "big") + b"\x00" * 14 + sof


def test_sniff_bitmap_header_reads_png_bmp_jpeg():
    png = iv.sniff_bitmap_header(png_bytes(4, 3, 8, 2))
    assert png == {"format": "png", "width": 4, "height": 3, "bit_depth": 8, "color_type": 2}
    bmp = iv.sniff_bitmap_header(bmp_bytes(5, -4, 24))
    assert bmp["format"] == "bmp" and bmp["width"] == 5 and bmp["height"] == 4
    assert bmp["bit_depth"] == 24 and bmp["bottom_up"] is False
    jpeg = iv.sniff_bitmap_header(jpeg_bytes(7, 9))
    assert jpeg == {"format": "jpeg", "width": 7, "height": 9, "bit_depth": 8}


def test_bitmap_identity_flags_suffix_mismatch():
    identity = iv.bitmap_identity("scene.png", png_bytes())
    assert identity["suffix_matches_header"] is True and identity["container"] == "images"
    assert identity["value_semantics"] == "rgb_intensity"
    mismatch = iv.bitmap_identity("scene.bmp", png_bytes())
    assert mismatch["suffix_matches_header"] is False
    assert mismatch["format"] == "png"


def test_sniff_bitmap_header_rejects_unknown_bytes():
    with pytest.raises(ZemaxError) as caught:
        iv.sniff_bitmap_header(b"not an image at all")
    assert caught.value.code == "UNKNOWN_BITMAP_HEADER"


# ------------------------------------------------------------- saved native reports


@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="saved 24.2 reports are not available")
def test_saved_partially_coherent_report_matches_contract():
    text = (EVIDENCE / "PartiallyCoherentImageAnalysis.txt").read_bytes().decode("utf-16")
    record = iv.parse_partially_coherent_text(text)
    assert record["wavelength_um"] == 0.55 and record["pixels"] == [13, 13]
    assert record["row_count"] == 13 and record["column_count"] == 13
    assert record["imaging"] == "incoherent" and record["aberration_included"] is True
    flat = [value for row in record["grid"] for value in row]
    assert max(flat) == pytest.approx(1.0) and min(flat) > 0.0


@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="saved 24.2 reports are not available")
def test_saved_extended_diffraction_report_matches_contract():
    text = (EVIDENCE / "ExtendedDiffractionImageAnalysis.txt").read_bytes().decode("utf-16")
    record = iv.parse_extended_diffraction_text(text)
    assert record["display_pixels"] == [256, 256]
    assert record["source_pixels"] == [7, 7] and record["source_width"] == 0.05
    assert record["row_count"] == 256 and record["column_count"] == 256
    flat = [value for row in record["grid"] for value in row]
    assert len(flat) == 65536 and max(flat) == pytest.approx(1.0)


@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="saved 24.2 reports are not available")
def test_saved_light_source_report_is_finite_conjugate_only():
    text = (EVIDENCE / "LightSourceAnalysis.txt").read_bytes().decode("utf-16")
    assert iv.parse_light_source_text(text)["reason"] == "finite_conjugate_only"
