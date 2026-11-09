"""D006 offline replay over already-saved source / spectrum / chromaticity materials.

This module never starts OpticStudio and never touches the ZOS-API. It re-reads the
native artefacts that earlier native runs already exported into the main project's
read-only evidence tree and re-derives the acceptance numbers from them, so the
D006 review has a real, repeatable check even while native startup stays deferred.

Reused materials (all read-only inputs in the main project):

  * ``source-spectrum-20261108/spectrum.txt`` - native SourceSpectrumViewer report
  * ``directivity-20261108/directivity.txt``  - native DirectivityPlot report
    plus the installed ``sample.ies`` the report names, for the angular/flux reference
  * ``flux-wavelength-20261108/flux.txt`` and ``summary.json`` - the empty outlet record
  * ``source-polar-20261108/summary.json`` - the 19x19 grid the probe recorded
  * ``source-illumination-twocolor-20261108/summary.json`` - the two-colour source condition

Run with the workspace Python::

    C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe -B \\
        .local/coordination/d006-offline.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
EVIDENCE = Path("C:/Users/tonge/Desktop/Zemax_MCP/.local/evidence/development/NS-03")
IES_SAMPLE = Path("C:/Users/tonge/Documents/Zemax/Objects/Sources/IESNA/sample.ies")
OUTPUT = Path(__file__).resolve().parent / "d006-offline.out.json"

sys.path.insert(0, str(WORKSPACE / "src"))

from zemax_mcp.analyses import ANALYSES  # noqa: E402
from zemax_mcp.basic_analyses import parse_directivity_plot, parse_source_spectrum  # noqa: E402

# Angular reference tolerance used by the native directivity audit (5.1e-5 absolute on
# the normalized candela scale); the flux gate is the displayed 4-decimal precision.
ANGULAR_TOLERANCE = 5.1e-5
FLUX_TOLERANCE = 5e-3

D006_ITEMS = [
    "NS-03.SourceSpectrumViewer",
    "NS-03.FluxvsWavelength",
    "NS-03.DirectivityPlot",
    "CV-01.SourceColorChart1931",
    "CV-01.SourceColorChart1976",
    "NS-03.SourcePolarViewer",
    "NS-03.SourceIlluminationMap",
    "NS-03.PhotoluminscenceViewer",
    "NS-03.RadiantSourceModelViewerSettings",
    "NS-03.RoadwayLighting",
]

# Native analysis kinds the product currently dispatches. Only two of the ten D006
# items have a kind today; the rest were probed through the generic analysis object.
PRODUCT_KINDS = {
    "NS-03.SourceSpectrumViewer": "source_spectrum_viewer",
    "NS-03.DirectivityPlot": "directivity_plot",
    "NS-03.FluxvsWavelength": "flux_vs_wavelength",
    "CV-01.SourceColorChart1931": "source_color_chart_1931",
    "CV-01.SourceColorChart1976": "source_color_chart_1976",
    "NS-03.SourcePolarViewer": "source_polar_viewer",
    "NS-03.SourceIlluminationMap": "source_illumination_map",
    "NS-03.PhotoluminscenceViewer": "photoluminscence_viewer",
    "NS-03.RadiantSourceModelViewerSettings": "radiant_source_model_viewer",
    "NS-03.RoadwayLighting": "roadway_lighting",
}


def read_native_text(path: Path) -> str:
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8", errors="replace")


def parse_ies(path: Path) -> dict:
    """Parse an IESNA LM-63 photometric file (TILT=NONE, one ballast line)."""

    lines = [ln.strip() for ln in path.read_text(encoding="latin-1").splitlines()]
    start = next(i for i, ln in enumerate(lines) if ln.replace(" ", "").upper() == "TILT=NONE")
    body = [ln for ln in lines[start + 1 :] if ln]
    counts = [float(x) for x in re.split(r"[,\s]+", body[0]) if x]
    number_of_lamps = int(counts[0])
    n_vertical = int(counts[3])
    n_horizontal = int(counts[4])
    cursor = 1
    ballast = [float(x) for x in re.split(r"[,\s]+", body[cursor]) if x]
    number_of_lamps = int(ballast[0]) or number_of_lamps
    cursor += number_of_lamps
    vertical = [float(x) for x in re.split(r"[,\s]+", body[cursor]) if x]
    cursor += 1
    horizontal = [float(x) for x in re.split(r"[,\s]+", body[cursor]) if x]
    cursor += 1
    if len(vertical) != n_vertical or len(horizontal) != n_horizontal:
        raise ValueError(f"angular grid mismatch: {len(vertical)}x{len(horizontal)}")
    candela = []
    for _ in range(n_horizontal):
        row = [float(x) for x in re.split(r"[,\s]+", body[cursor]) if x]
        cursor += 1
        if len(row) != n_vertical:
            raise ValueError(f"candela row has {len(row)} values, expected {n_vertical}")
        candela.append(row)
    return {
        "vertical_angles": vertical,
        "horizontal_angles": horizontal,
        "candela": candela,
        "peak_candela": max(max(row) for row in candela),
        "distinct_slices": len({tuple(row) for row in candela}),
        "lamp_count": number_of_lamps,
    }


def check_directivity_angles() -> dict:
    text = read_native_text(EVIDENCE / "directivity-20261108" / "directivity.txt")
    parsed = parse_directivity_plot(text)
    ies = parse_ies(IES_SAMPLE)
    peak = ies["peak_candela"]
    slice_row = ies["candela"][0]
    vertical = ies["vertical_angles"]

    def reference(angle_deg: float) -> float:
        target = abs(angle_deg)
        for index, value in enumerate(vertical):
            if abs(value - target) <= 1e-9:
                return slice_row[index] / peak
        raise ValueError(f"angle {angle_deg} is not on the IES grid")

    diffs = {}
    for row in parsed["rows"]:
        expected = reference(row["angle_deg"])
        diffs[row["angle_deg"]] = abs(row["normalized_candela"] - expected)
    worst_angle = max(diffs, key=diffs.get)
    return {
        "ok": len(parsed["rows"]) == 37 and max(diffs.values()) <= ANGULAR_TOLERANCE,
        "rows": len(parsed["rows"]),
        "scan_angles_deg": [group["scan_angle_deg"] for group in parsed["groups"]]
        if "groups" in parsed
        else sorted({row["scan_angle_deg"] for row in parsed["rows"]}),
        "ies_file": parsed["ies_file"],
        "peak_intensity_candela": parsed["peak_intensity_candela"],
        "total_luminous_flux_lumens": parsed["total_luminous_flux_lumens"],
        "ies_peak_candela": peak,
        "ies_distinct_horizontal_slices": ies["distinct_slices"],
        "max_abs_difference": max(diffs.values()),
        "worst_angle_deg": worst_angle,
        "tolerance": ANGULAR_TOLERANCE,
    }


def check_directivity_flux() -> dict:
    ies = parse_ies(IES_SAMPLE)
    vertical = ies["vertical_angles"]
    row = ies["candela"][0]
    total = 0.0
    for index in range(len(vertical) - 1):
        theta0 = math.radians(vertical[index])
        theta1 = math.radians(vertical[index + 1])
        f0 = row[index] * math.sin(theta0)
        f1 = row[index + 1] * math.sin(theta1)
        total += 0.5 * (f0 + f1) * (theta1 - theta0)
    total *= 2.0 * math.pi
    reported = 112.81
    return {
        "ok": abs(total - reported) <= FLUX_TOLERANCE,
        "trapezoid_flux_lumens": total,
        "native_reported_flux_lumens": reported,
        "abs_difference": abs(total - reported),
        "tolerance": FLUX_TOLERANCE,
        "note": "continuous piecewise-linear integration would give 113.0973355 lm; the report matches the sampled trapezoid",
    }


def check_source_spectrum() -> dict:
    text = read_native_text(EVIDENCE / "source-spectrum-20261108" / "spectrum.txt")
    parsed = parse_source_spectrum(text)
    wavelengths = [row["wavelength_um"] for row in parsed["rows"]]
    weights = [row["relative_weight"] for row in parsed["rows"]]
    peak = max(weights)
    return {
        "ok": len(parsed["rows"]) == 20
        and abs(wavelengths[0] - 0.44) < 1e-12
        and abs(wavelengths[-1] - 0.64) < 1e-12
        and abs(peak - 1.0) < 1e-12
        and parsed["input_xyz"] == parsed["fitted_xyz"] == [1.0, 1.0, 1.0]
        and abs(parsed["cri"] - 70.1766) < 1e-9
        and abs(parsed["cct_kelvin"] - 5188.0) < 1e-9,
        "rows": len(parsed["rows"]),
        "wavelength_range_um": [wavelengths[0], wavelengths[-1]],
        "peak_relative_weight": peak,
        "input_xyz": parsed["input_xyz"],
        "fitted_xyz": parsed["fitted_xyz"],
        "cri": parsed["cri"],
        "cct_kelvin": parsed["cct_kelvin"],
        "input_definition": parsed["input_definition"],
        "source_object_binding": parsed["source_object_binding"],
    }


def check_flux_outlet() -> dict:
    text = read_native_text(EVIDENCE / "flux-wavelength-20261108" / "flux.txt")
    summary = json.loads((EVIDENCE / "flux-wavelength-20261108" / "summary.json").read_text("utf-8"))
    counts = summary["result"]["counts"]
    body = [ln for ln in text.splitlines() if ln.strip()]
    return {
        "ok": not body and all(int(value) == 0 for value in counts.values()),
        "exported_characters": len(text),
        "report_rows": len(body),
        "result_counts": counts,
        "text_export_flag": summary["result"]["text_export"],
        "wavelengths_from_context": summary["context"].get("mode"),
        "conclusion": "the outlet is reachable but empty: text export is flagged true while the file only holds the BOM",
    }


def check_source_polar_grid() -> dict:
    summary = json.loads((EVIDENCE / "source-polar-20261108" / "summary.json").read_text("utf-8"))
    grid = summary["result"]["grids"][0]
    return {
        "ok": grid["nx"] == 19
        and grid["ny"] == 19
        and grid["dx"] == 10.0
        and abs(grid["dy"] - 18.94736842105263) < 1e-12
        and grid["x_label"] == grid["y_label"] == grid["value_label"] == "None",
        "nx": grid["nx"],
        "ny": grid["ny"],
        "dx": grid["dx"],
        "dy": grid["dy"],
        "min_x": grid["min_x"],
        "min_y": grid["min_y"],
        "labels": [grid["x_label"], grid["y_label"], grid["value_label"]],
        "conclusion": "raw native matrix retained; axis semantics and units are still undefined",
    }


def check_source_polar_sample_correspondence() -> dict:
    """Numeric correspondence between the saved polar matrix and *this one sample's* IES table.

    SCOPE LIMIT: ``sample.ies`` is rotationally symmetric - all nineteen horizontal slices
    hold the same 18..0 candela row - so a cell-by-cell match against it can only show that
    the saved matrix reproduces this sample's numbers. It cannot establish how OpticStudio
    publishes an arbitrary IES table, nor its unit or normalisation contract.
    """

    summary = json.loads((EVIDENCE / "source-polar-20261108" / "summary.json").read_text("utf-8"))
    values = [[float(cell) for cell in row] for row in summary["result"]["grids"][0]["values"]]
    ies = parse_ies(IES_SAMPLE)
    table = [[float(cell) for cell in row] for row in ies["candela"]]
    horizontal = ies["horizontal_angles"]
    vertical = ies["vertical_angles"]
    grid = summary["result"]["grids"][0]
    return {
        "ok": values == table,
        "cells_equal_to_this_sample_ies": values == table,
        "shape": [len(values), len(values[0])],
        "sample_horizontal_slices_all_identical": ies["distinct_slices"] == 1,
        "reported_dx": grid["dx"],
        "source_vertical_step_deg": vertical[1] - vertical[0],
        "reported_dy": grid["dy"],
        "source_horizontal_step_deg": horizontal[1] - horizontal[0],
        "dy_equals_uniform_360_over_19": abs(
            grid["dy"] - (horizontal[-1] - horizontal[0]) / len(horizontal)
        )
        < 1e-9,
        "scope": "single rotationally symmetric sample",
        "conclusion": (
            "for this rotationally symmetric sample the saved 19x19 matrix reproduces the file's "
            "candela values cell by cell. Because every horizontal slice of the file is identical, "
            "this cannot show how an arbitrary IES table is published, nor its units or "
            "normalisation. The reported dy of 360/19 differs from the file's 20 degree node "
            "spacing; that difference is recorded as a fact only - it may be a native pixel-range "
            "or centre convention and is not judged here as a mapping error."
        ),
    }


def check_illumination_condition() -> dict:
    """Object condition of the checked model only, plus its empty result collection.

    This is not an exhaustive input-contract check: without a published selection contract
    for the topic, other input-condition errors cannot be excluded.
    """

    summary = json.loads(
        (EVIDENCE / "source-illumination-twocolor-20261108" / "summary.json").read_text("utf-8")
    )
    rows = summary["objects"]["data"]["rows"]
    sources = [row["type"] for row in rows if str(row["type"]).startswith("Source")]
    detectors = [row["type"] for row in rows if str(row["type"]).startswith("Detector")]
    counts = summary["result"]["counts"]
    return {
        "ok": sources.count("SourceEllipse") == 4 and "DetectorColor" in detectors,
        "checked_model_only": True,
        "source_types": sources,
        "detector_types": detectors,
        "result_counts": counts,
        "conclusion": (
            "the checked model carries four SourceEllipse sources and one DetectorColor, and its "
            "result collection is empty. This establishes the object condition of this model and "
            "the empty outlet for it only; with no topic input-selection contract it does not rule "
            "out every other possible input-condition error."
        ),
    }


def _roadway_metrics(text: str) -> dict:
    metrics = {}
    for key, pattern in (
        ("average_luminance", r"平均亮度[^:]*:\s*(\S+)\s+(\S+)\s+(\S+)"),
        ("overall_uniformity", r"整体亮度均匀性[^:]*:\s*(\S+)\s+(\S+)\s+(\S+)"),
        ("longitudinal_uniformity", r"纵向亮度均匀性[^:]*:\s*(\S+)\s+(\S+)\s+(\S+)"),
        ("threshold_increment", r"阈值增量[^:]*:\s*(\S+)\s+(\S+)\s+(\S+)"),
        ("surround_ratio", r"环绕率[^:]*:\s*(\S+)\s+(\S+)\s+(\S+)"),
    ):
        match = re.search(pattern, text)
        if match:
            metrics[key] = {
                "verdict": match.group(1),
                "target": match.group(2),
                "value": match.group(3),
            }
    title = re.search(r"题目:\s*(.+)", text)
    return {"title": title.group(1).strip() if title else None, "metrics": metrics}


def check_roadway_reports() -> dict:
    """Two saved roadway runs reported the same defaults but different models and metrics."""

    first_text = read_native_text(EVIDENCE / "roadway-lighting-20261108" / "photoluminescence.txt")
    second_text = read_native_text(
        EVIDENCE / "roadway-lighting-repeat-20261108" / "photoluminescence.txt"
    )
    first = _roadway_metrics(first_text)
    second = _roadway_metrics(second_text)
    marker = "CIE 140-2000"
    same_defaults = marker in first_text and marker in second_text
    differing = {
        key: [first["metrics"][key]["value"], second["metrics"][key]["value"]]
        for key in first["metrics"]
        if key in second["metrics"] and first["metrics"][key]["value"] != second["metrics"][key]["value"]
    }
    return {
        "ok": same_defaults and first["title"] != second["title"] and bool(differing),
        "first_model": first["title"],
        "second_model": second["title"],
        "same_default_road_spec": same_defaults,
        "first_metrics": first["metrics"],
        "second_metrics": second["metrics"],
        "metrics_that_changed": differing,
        "conclusion": (
            "both runs used the same default CIE 140-2000 road spec but different systems and produced "
            "different metrics; with no writable or readable topic settings and no roadway model, neither "
            "value is attributable to a controlled road-lighting input"
        ),
    }


def check_product_interface() -> dict:
    present, absent = [], []
    for item, kind in PRODUCT_KINDS.items():
        (present if kind in ANALYSES else absent).append({"item": item, "kind": kind})
    return {
        "ok": len(present) == 2 and len(absent) == 8,
        "present": present,
        "absent": absent,
        "conclusion": "only the spectrum viewer and the directivity plot have a typed request and dispatch today",
    }


CHECKS = {
    "directivity_angles": check_directivity_angles,
    "directivity_flux": check_directivity_flux,
    "source_spectrum": check_source_spectrum,
    "flux_outlet": check_flux_outlet,
    "source_polar_grid": check_source_polar_grid,
    "source_polar_sample_correspondence": check_source_polar_sample_correspondence,
    "illumination_condition": check_illumination_condition,
    "roadway_reports": check_roadway_reports,
    "product_interface": check_product_interface,
}


def main() -> int:
    results = {}
    for name, function in CHECKS.items():
        try:
            results[name] = function()
        except Exception as error:  # noqa: BLE001 - a broken check must be visible, not fatal
            results[name] = {"ok": False, "error": f"{type(error).__name__}: {error}"}
    failures = sorted(name for name, value in results.items() if not value["ok"])
    payload = {
        "task": "D006.SOURCE_SPECTRUM_COLOR_ILLUMINATION",
        "agent": "Agent 2 module worker",
        "executed_native": False,
        "materials_root": str(EVIDENCE),
        "checks": results,
        "failed_checks": failures,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({name: value["ok"] for name, value in results.items()}, indent=2))
    print(f"failed: {failures}")
    print(f"written: {OUTPUT}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
