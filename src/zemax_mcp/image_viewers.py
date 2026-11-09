"""Extended-scene image analyses and file viewers with documented-only surfaces.

All facts here are taken from the installed 2024 R2 documentation and from probes
that already ran natively; nothing is guessed:

* ``ZOSAPI.Analysis.AnalysisIDM`` defines LightSourceAnalysis (63),
  BitmapFileViewer (62), PartiallyCoherentImageAnalysis (64),
  ExtendedDiffractionImageAnalysis (65), GeometricBitmapImageAnalysis (61) and
  BeamFileViewer (96).
* On the installed 24.2 build all six instantiated ``AS_Default`` in the
  2026-11-09 runtime probe. GeometricBitmapImageAnalysis has no GetFileNames
  selector; its settings must not be confused with GeometricImageAnalysis.
  Documented CFG keys are recorded separately from typed API properties.

Attribution rule for the Programming-tab MODIFYSETTINGS listing
(``BASE-01/manual349-modifysettings.txt``): in that export each analysis's key
block is printed immediately **before** the analysis heading, so the heading
that follows a block names its owner.  Anchors: ``DVW_OUTPUTFILE`` (line 40)
precedes the ``Detector Viewer`` heading (line 41); ``XSE_`` (51-62) precedes
``Extended Source Encircled Energy`` (63-64); ``PPM_`` (286-295) precedes
``Polarization Pupil Map`` (296), which ``polarization.py`` already drives with
exactly those keys.  Reading the heading above a block instead mis-assigns it.
"""
import re

from .errors import ZemaxError

ANALYSIS_IDS = {
    "light_source": ("LightSourceAnalysis", 63),
    "bitmap_file_viewer": ("BitmapFileViewer", 62),
    "partially_coherent_image": ("PartiallyCoherentImageAnalysis", 64),
    "extended_diffraction_image": ("ExtendedDiffractionImageAnalysis", 65),
    "geometric_bitmap_image": ("GeometricBitmapImageAnalysis", 61),
    "beam_file_viewer": ("BeamFileViewer", 96),
}

#: documented MODIFYSETTINGS keys per analysis, each verified against the key
#: block that precedes its own heading in manual349-modifysettings.txt.
MODIFY_SETTINGS = {
    "extended_diffraction_image": {
        "EXD_DISPLAYSIZE": "display size",
        "EXD_FIELD": "field number",
        "EXD_FILESIZE": "file size",
        "EXD_WAVE": "wavelength number",
    },
    "partially_coherent_image": {
        "PCI_FIELD": "field number",
        "PCI_FILESIZE": "file size",
        "PCI_WAVE": "wavelength number",
        "PCI_RESAMPLE": "resample image flag",
        "PCI_RSNX": "resample number x",
        "PCI_RSNY": "resample number y",
        "PCI_RSDCX": "resample decenter x",
        "PCI_RSDCY": "resample decenter y",
        "PCI_RSDLX": "resample delta x",
        "PCI_RSDLY": "resample delta y",
    },
    "geometric_bitmap_image": {
        "GBM_FIELDSIZE": "field Y size",
        "GBM_RAYS": "rays per source pixel",
        "GBM_XPIX": "number of X pixels",
        "GBM_YPIX": "number of Y pixels",
        "GBM_XSIZ": "X pixel size",
        "GBM_YSIZ": "Y pixel size",
        "GBM_INPUT": "input file name",
        "GBM_OUTPUT": "output file name",
        "GBM_SURFACE": "surface number",
        "GBM_ROTATION": "rotation setting",
    },
    "light_source": {},
    "bitmap_file_viewer": {},
    "beam_file_viewer": {},
}

#: provenance of each attribution: key block lines and the heading that owns it.
KEY_ATTRIBUTION = {
    "extended_diffraction_image": {"prefix": "EXD_", "key_lines": "45-48", "heading_lines": "49-50",
                                   "heading": "Extended Diffraction Image Analysis"},
    "partially_coherent_image": {"prefix": "PCI_", "key_lines": "274-283", "heading_lines": "284-285",
                                 "heading": "Partially Coherent Image Analysis"},
    "geometric_bitmap_image": {"prefix": "GBM_", "key_lines": "127-136", "heading_lines": "137-138",
                              "heading": "Geometric Bitmap Image Analysis"},
    "light_source": {"prefix": None, "key_lines": None, "heading_lines": None,
                     "heading": "Light Source Analysis"},
    "bitmap_file_viewer": {"prefix": None, "key_lines": None, "heading_lines": None,
                           "heading": "Bitmap File Viewer"},
    "beam_file_viewer": {"prefix": None, "key_lines": None, "heading_lines": None,
                         "heading": "Beam File Viewer"},
}

#: prefixes owned by other analyses; they must never appear under our kinds.
FOREIGN_PREFIXES = {
    "XSE_": "Extended Source Encircled Energy (key lines 51-62, heading 63-64)",
    "PPM_": "Polarization Pupil Map (key lines 286-295, heading 296; used by polarization.py)",
    "IMA_": "Geometric Image Analysis (key lines 139-146, heading 147)",
    "POP_": "PhysicalOpticsPropagation (key lines 297-300, heading 301)",
    "TFM_": "FFT Through Focus MTF (key lines 148-157, heading 158)",
    "MTF_": "MTF - FFT (key lines 252-261, heading 262)",
    "LSF_": "FFT Line/Edge Spread (key lines 65-73, heading 74)",
    "PSF_": "FFT PSF (key lines 75-82, heading 83)",
}

#: file suffix -> (container, value semantics, editable in place)
SOURCE_FILES = {
    ".zbf": ("pop", "relative_complex_amplitude", False),
    ".ima": ("images", "relative_irradiance", True),
    ".bim": ("images", "relative_irradiance", False),
    ".bmp": ("images", "rgb_intensity", False),
    ".jpg": ("images", "rgb_intensity", False),
    ".jpeg": ("images", "rgb_intensity", False),
    ".png": ("images", "rgb_intensity", False),
    ".dat": ("any", "source_ray_list_flux", False),
    ".sdf": ("any", "source_ray_list_spectral", False),
    ".tm25ray": ("any", "source_ray_list_spectral", False),
}

ACCEPTS = {
    "light_source": (".dat", ".sdf", ".tm25ray"),
    "bitmap_file_viewer": (".bmp", ".jpg", ".jpeg", ".png"),
    "beam_file_viewer": (".zbf",),
    "ima_bim_viewer": (".ima", ".bim"),
    "partially_coherent_image": (".ima", ".bim", ".zbf"),
    "extended_diffraction_image": (".ima", ".bim"),
    "geometric_bitmap_image": (".bmp", ".jpg", ".jpeg", ".png"),
}

#: result channel actually observed in the saved 24.2 probes (probe442-b005 and
#: bitmap-viewer-repeat-20261108), so nothing about the channel is assumed.
RESULT_CHANNELS = {
    "light_source": {"data_grids": 0, "messages": 1, "text_export": True,
                     "note": "the supplied system reports only the finite-conjugate refusal message"},
    "bitmap_file_viewer": {"data_grids": 0, "messages": 0, "text_export": False,
                           "note": "no numeric grid and no text export; the image window is the only channel"},
    "beam_file_viewer": {"data_grids": 1, "messages": 0, "text_export": True,
                         "note": "default grid/report available; report says no file defined, so input identity remains unconfirmed"},
    "partially_coherent_image": {"data_grids": 1, "messages": 0, "text_export": True,
                                 "note": "one numeric grid plus the text report"},
    "extended_diffraction_image": {"data_grids": 1, "messages": 0, "text_export": True,
                                   "note": "one numeric grid plus the text report"},
    "geometric_bitmap_image": {"data_grids": 0, "messages": 0, "text_export": True,
                               "note": "RGB text and native BMP provide three checked channel grids; no structured native grid"},
}

_NUMBER = re.compile(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?")
_NON_FINITE = re.compile(r"^(?:[-+]?(?:nan|inf(?:inity)?)|1\.#qnan|-?1\.#ind)$", re.IGNORECASE)
_PIXELS = re.compile(r"(\d+)\s*[乘以x×]\s*(\d+)")
_LOCATION = re.compile(r"位置\s*[:：]\s*([-+]?\d*\.?\d+)\s*\(度\)")
_TARGET = re.compile(r"对于\s*([-+]?\d*\.?\d+)\s*\(度\)")
_UM = re.compile(r"([-+]?\d*\.?\d+)\s*(?:µm|μm|um|微米)")

COHERENCE_TEXT = {
    "部分相干成像": "partially_coherent",
    "非相干成像": "incoherent",
    "相干成像": "coherent",
}


def analysis_id(kind):
    try:
        return ANALYSIS_IDS[kind][1]
    except KeyError:
        raise ZemaxError("UNKNOWN_ANALYSIS", "未登记的图像分析种类。", kind=kind,
                         known=sorted(ANALYSIS_IDS)) from None


def settings_surface(kind):
    """Describe observed runtime settings and separately documented CFG keys."""
    known=ANALYSIS_IDS[kind]
    return dict(kind=kind,native_id=known[0],analysis_id=known[1],
                settings_class='AS_Default',api_properties=False,
                api_surface_status='observed_no_topic_properties',
                evidence='development/evidence/D005/runtime-contracts-20261109.md',
                modify_settings=dict(MODIFY_SETTINGS[kind]),
                writable=False,
                documented_cfg_keys_available=bool(MODIFY_SETTINGS[kind]),
                cfg_adoption_status='verified_subset' if kind in {'extended_diffraction_image','partially_coherent_image','geometric_bitmap_image'}
                                    else 'no_documented_keys')



def source_file_identity(name):
    """Classify an analysis input file by its documented container and meaning."""
    lowered = str(name).strip().lower()
    for suffix, (folder, semantics, editable) in SOURCE_FILES.items():
        if lowered.endswith(suffix):
            return {"name": str(name), "suffix": suffix, "container": folder,
                    "value_semantics": semantics, "editable_in_place": editable}
    raise ZemaxError("UNKNOWN_SOURCE_FILE", "未登记的分析输入文件类型。",
                     name=str(name), known=sorted(SOURCE_FILES))


def accepts_source(kind, name):
    try:
        suffix = source_file_identity(name)["suffix"]
    except ZemaxError:
        return False
    return suffix in ACCEPTS[kind]


def sniff_bitmap_header(data):
    """Read only the header of a BMP/PNG/JPEG file; the viewer does no processing."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 33:
        return {"format": "png",
                "width": int.from_bytes(data[16:20], "big"),
                "height": int.from_bytes(data[20:24], "big"),
                "bit_depth": data[24], "color_type": data[25]}
    if data[:2] == b"BM" and len(data) >= 30:
        width = int.from_bytes(data[18:22], "little", signed=True)
        height = int.from_bytes(data[22:26], "little", signed=True)
        return {"format": "bmp", "width": abs(width), "height": abs(height),
                "bit_depth": int.from_bytes(data[28:30], "little"), "bottom_up": height > 0}
    if data[:2] == b"\xff\xd8":
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                return {"format": "jpeg",
                        "height": int.from_bytes(data[index + 5:index + 7], "big"),
                        "width": int.from_bytes(data[index + 7:index + 9], "big"),
                        "bit_depth": data[index + 4]}
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                index += 2
                continue
            length = int.from_bytes(data[index + 2:index + 4], "big")
            index += 2 + max(length, 2)
    raise ZemaxError("UNKNOWN_BITMAP_HEADER", "无法识别的位图文件头。", size=len(data))


_SUFFIX_FOR_FORMAT = {"png": (".png",), "bmp": (".bmp",), "jpeg": (".jpg", ".jpeg")}


def bitmap_identity(name, data):
    """Combine the documented container rules with the real header of the file."""
    identity = source_file_identity(name)
    header = sniff_bitmap_header(data)
    return {**identity, **header,
            "suffix_matches_header": identity["suffix"] in _SUFFIX_FOR_FORMAT[header["format"]]}


def declared_scope(kind):
    """The full declared scope of a viewer/analysis, with verification state."""
    scope = {
        "light_source": {
            "inputs": ["DAT", "SDF", "TM25RAY binary source ray files"],
            "result_channel": "detector image (text grid and optional BMP/JPG/PNG output)",
            "coherence": "geometrical ray tracing; polarization assigned randomly when enabled",
            "wavelengths": "DAT follows the system wavelengths; SDF/TM25RAY always use file wavelengths",
            "notes": ["finite conjugate systems only", "flux in Watts or Lumens; Fraction selects rays"],
        },
        "bitmap_file_viewer": {
            "inputs": ["BMP", "JPG", "PNG"],
            "result_channel": "image window only; no data grid and no text export in the saved probe",
            "coherence": "not applicable (display only, no processing)",
            "wavelengths": "not applicable",
            "notes": ["files must live in the <images> folder"],
        },
        "beam_file_viewer": {
            "inputs": ["ZBF"],
            "result_channel": "image window; viewer settings are a subset of POP",
            "coherence": "coherent complex beam data",
            "wavelengths": "taken from the beam file",
            "notes": ["ZBF files live in the <pop> folder", "cursor keys page through surface numbers"],
        },
        "partially_coherent_image": {
            "inputs": ["IMA/BIM intensity", "ZBF complex amplitude (subset)"],
            "result_channel": "text grid plus one numeric data grid",
            "coherence": "data type selects incoherent, coherent, raw, transfer function, or partially coherent (image/PSF/gamma)",
            "wavelengths": "one wavelength number per calculation",
            "notes": ["Gamma/Alpha/Fraction describe the complex degree of coherence, not a coherence length",
                      "Oversampling/Zero Padding/OTF Sampling plus optional detector resampling"],
        },
        "extended_diffraction_image": {
            "inputs": ["IMA", "BIM"],
            "result_channel": "text grid plus one numeric data grid",
            "coherence": "fully coherent or fully incoherent illumination only",
            "wavelengths": "one wavelength number per calculation",
            "notes": ["the OTF may vary over the field of view (OTF Grid)", "Display Size is independent of File Size"],
        },
        "geometric_bitmap_image": {
            "inputs": ["BMP", "JPG", "PNG"],
            "result_channel": "RGB data grid",
            "coherence": "geometrical ray tracing (incoherent)",
            "wavelengths": "RGB or 1+2+3 system wavelengths",
            "notes": ["Field Y Size defines the source size in field space", "Show Source Bitmap traces no rays"],
        },
    }[kind]
    result = dict(scope)
    result["kind"] = kind
    result["settings"] = settings_surface(kind)
    result["result_channel"] = RESULT_CHANNELS[kind]["note"]
    result["verified"] = False
    return result


def _grid(lines):
    rows = []
    for line in lines:
        tokens = line.replace("\t", " ").split()
        if not tokens:
            continue
        if any(_NON_FINITE.match(token) for token in tokens):
            raise ZemaxError("ANALYSIS_TEXT_NON_FINITE", "报告网格含非有限值。",
                             line=line.strip()[:120], tokens=[t for t in tokens if _NON_FINITE.match(t)])
        if all(_NUMBER.fullmatch(token) for token in tokens):
            rows.append([float(token) for token in tokens])
    if not rows:
        raise ZemaxError("ANALYSIS_TEXT_NO_GRID", "报告中没有可解析的数值网格。", lines=len(lines))
    width = len(rows[0])
    for index, row in enumerate(rows):
        if len(row) != width:
            raise ZemaxError("ANALYSIS_TEXT_RAGGED_GRID", "网格行宽不一致。",
                             row=index, expected=width, actual=len(row))
    return rows


def _verify_shape(rows, pixels):
    """The text grid must match the pixel counts printed in the header."""
    actual = [len(rows[0]), len(rows)]
    if actual != [int(pixels[0]), int(pixels[1])]:
        raise ZemaxError("ANALYSIS_TEXT_SHAPE_MISMATCH", "网格尺寸与报告头条目像素数不一致。",
                         grid=actual, header=[int(pixels[0]), int(pixels[1])])


def _statistics(rows, semantics):
    flat = [value for row in rows for value in row]
    return {
        "row_count": len(rows),
        "column_count": len(rows[0]),
        "cell_count": len(flat),
        "minimum": min(flat),
        "maximum": max(flat),
        "value_semantics": semantics,
        "grid": rows,
    }


def _pixels(line):
    match = _PIXELS.search(line)
    if not match:
        raise ZemaxError("ANALYSIS_TEXT_NO_PIXELS", "未能识别像素数。", line=line.strip())
    return int(match.group(1)), int(match.group(2))


def _aberration(text):
    if "包含像差" in text or "with aberration" in text.lower():
        return True
    if "衍射极限" in text or "diffraction limited" in text.lower():
        return False
    return None


def parse_extended_diffraction_text(text):
    """Parse the saved Extended Diffraction Image Analysis report."""
    lines = text.splitlines()
    head = lines[:40]
    joined = "\n".join(head)
    location = _LOCATION.search(joined) or _TARGET.search(joined)
    wave = _UM.search(joined)
    if not location or not wave:
        raise ZemaxError("ANALYSIS_TEXT_NO_HEADER", "扩展衍射像报告头不完整。", head=joined[:400])
    source = next((line for line in head if "光源" in line), "")
    display = next((line for line in head if "显示" in line), "")
    source_width = _NUMBER.findall(source.split(":")[-1] if ":" in source else source)
    display_width = _NUMBER.findall(display.split(":")[-1] if ":" in display else display)
    source_pixels = list(_pixels(source))
    display_pixels = list(_pixels(display))
    rows = _grid(lines)
    _verify_shape(rows, display_pixels)
    record = {
        "kind": "extended_diffraction_image",
        "wavelength_um": float(wave.group(1)),
        "field_deg": float(location.group(1)),
        "source_width": float(source_width[0]) if source_width else None,
        "source_pixels": source_pixels,
        "display_width": float(display_width[0]) if display_width else None,
        "display_pixels": display_pixels,
        "aberration_included": _aberration(joined),
        "normalization": "relative_intensity",
        "size_units": "mm",
        "wavelength_units": "um",
        "axes": {"x": "image space about the field centre", "y": "image space about the field centre"},
    }
    if record["source_width"]:
        record["source_pixel_size"] = record["source_width"] / source_pixels[0]
    if record["display_width"]:
        record["display_pixel_size"] = record["display_width"] / display_pixels[0]
    record.update(_statistics(rows, "relative_intensity"))
    return record


def _imaging(lines):
    """Match the coherence line exactly; the three phrases share a suffix."""
    for line in lines:
        text = line.strip()
        for key, value in COHERENCE_TEXT.items():
            if text == key:
                return value
    joined = "\n".join(lines)
    for key, value in COHERENCE_TEXT.items():
        if key in joined:
            return value
    return None


def parse_partially_coherent_text(text):
    """Parse the saved Partially Coherent Image Analysis report."""
    lines = text.splitlines()
    head = lines[:40]
    joined = "\n".join(head)
    location = _TARGET.search(joined) or _LOCATION.search(joined)
    wave = _UM.search(joined)
    width = next((line for line in head if "宽度" in line), "")
    if not location or not wave or not width:
        raise ZemaxError("ANALYSIS_TEXT_NO_HEADER", "部分相干成像报告头不完整。", head=joined[:400])
    widths = _NUMBER.findall(width)
    imaging = _imaging(head)
    pixels = list(_pixels(width))
    rows = _grid(lines)
    _verify_shape(rows, pixels)
    record = {
        "kind": "partially_coherent_image",
        "wavelength_um": float(wave.group(1)),
        "field_deg": float(location.group(1)),
        "width": float(widths[0]) if widths else None,
        "pixels": pixels,
        "imaging": imaging,
        "aberration_included": _aberration(joined),
        "normalization": "relative_intensity",
        "size_units": "mm",
        "wavelength_units": "um",
        "axes": {"x": "image space about the field centre", "y": "image space about the field centre"},
    }
    if record["width"]:
        record["pixel_size"] = record["width"] / pixels[0]
    record.update(_statistics(rows, "relative_intensity"))
    return record


def parse_light_source_text(text):
    """Parse the saved Light Source Analysis report.

    Infinite-conjugate reports carry an applicability message. Finite-conjugate
    reports have the observed RGB/tristimulus table; an undefined input remains
    unavailable even when the report contains a complete zero table.
    """
    stripped = text.strip()
    if not stripped:
        raise ZemaxError("ANALYSIS_TEXT_EMPTY", "光源分析报告为空。")
    if "仅有限共轭" in stripped or "finite conjugate" in stripped.lower():
        return {
            "kind": "light_source",
            "available": False,
            "reason": "finite_conjugate_only",
            "message": stripped,
        }
    from .light_source_report import parse_finite_light_source
    return parse_finite_light_source(text)


PARSERS = {
    "extended_diffraction_image": parse_extended_diffraction_text,
    "partially_coherent_image": parse_partially_coherent_text,
    "light_source": parse_light_source_text,
}


def parse_report(kind, text):
    try:
        parser = PARSERS[kind]
    except KeyError:
        raise ZemaxError("NO_ANALYSIS_TEXT_PARSER", "该分析没有离线文本解析器。",
                         kind=kind, known=sorted(PARSERS)) from None
    return parser(text)
