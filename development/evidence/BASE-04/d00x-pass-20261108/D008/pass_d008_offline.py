"""Offline recomputation for D008 (no OpticStudio, no native run).

O2: independent TPD parse vs the saved native catalog rows.
O3: recompute the 641 slope-summary comparison errors and tolerance verdicts.
O4: recompute the 622 manufacturing-offset sign/radius arithmetic.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from zemax_mcp.test_plates import parse_tpd  # noqa: E402

MAIN = Path(r"C:\Users\tonge\Desktop\Zemax_MCP")
EVID = MAIN / "development" / "evidence"
OUT = ROOT / ".local" / "coordination" / "pass-d008-offline-checks.json"
ROW_TOL = 0.0000500001

report = {}

# ---------------------------------------------------------------- O2 plate catalog
saved = json.loads((MAIN / ".local/runs/runs/plates429_native_f9120956a3/native-result.json")
                   .read_text(encoding="utf-8"))
catalog = saved.get("native_catalog_file")
tpd = Path(r"C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Testplate") / str(catalog)
headers, rows = parse_tpd(tpd.read_text(encoding="utf-8", errors="replace"))
native_rows = saved["rows"]
radius_errors = [abs(a["radius_mm"] - b["radius_mm"]) for a, b in zip(rows, native_rows)]
diameter_errors = [abs(a["diameter_mm"] - b["diameter_mm"]) for a, b in zip(rows, native_rows)]
identity_mismatch = [i for i, (a, b) in enumerate(zip(rows, native_rows))
                     if a["availability_code"] != b["availability_code"] or a["plate_id"] != b["plate_id"]]
report["plate_catalog"] = dict(
    catalog_file=catalog,
    tpd_path=str(tpd),
    tpd_exists=tpd.is_file(),
    parsed_rows=len(rows),
    native_rows=len(native_rows),
    headers=headers,
    max_radius_difference=max(radius_errors) if radius_errors else None,
    max_diameter_difference=max(diameter_errors) if diameter_errors else None,
    row_tolerance=ROW_TOL,
    rows_outside_tolerance=sum(1 for e in radius_errors + diameter_errors if e > ROW_TOL),
    identity_or_code_mismatches=len(identity_mismatch),
    passed=(len(rows) == len(native_rows)
            and all(e <= ROW_TOL for e in radius_errors + diameter_errors)
            and not identity_mismatch),
)

# ------------------------------------------------------- O3 slope summary (641)
p641 = json.loads((EVID / "MF-01" / "progress641-slope-summary.json").read_text(encoding="utf-8"))
comparisons = []
for row in p641["comparisons"]:
    expected = row["expected"]
    error = abs(row["actual"] - expected)
    limit = row["atol"] + row["rtol"] * abs(expected)
    comparisons.append(dict(label=row["label"], absolute_error=error, limit=limit,
                            passed=error <= limit, stored_passed=row["passed"],
                            stored_error=row.get("absolute_error")))
verdict_agreement = all(c["passed"] == c["stored_passed"] for c in comparisons)
error_agreement = all(abs(c["absolute_error"] - (c["stored_error"] or 0)) <= 1e-18 for c in comparisons)
report["slope_summary_641"] = dict(
    comparisons=comparisons,
    count=len(comparisons),
    max_absolute_error=max(c["absolute_error"] for c in comparisons),
    all_pass=all(c["passed"] for c in comparisons),
    stored_verdict_agreement=verdict_agreement,
    stored_error_agreement=error_agreement,
    tolerance="1e-6 absolute + 1e-5 relative",
)

# ------------------------------------------------------ O4 offset arithmetic (622)
p622 = json.loads((EVID / "MF-01" / "progress622-dsag-fit.json").read_text(encoding="utf-8"))
sign_rows = []
for row in p622["comparisons"]:
    native = row.get("native_offset")
    independent = row.get("independent_additive_sphere_offset")
    opposite = (native is not None and independent is not None
                and native != 0 and independent != 0
                and math.copysign(1, native) != math.copysign(1, independent))
    sign_rows.append(dict(
        sign=row.get("sign"), criterion=row.get("criterion"), sampling=row.get("sampling"),
        radius=row.get("radius"), native_offset=native, independent_offset=independent,
        opposite_signs=opposite,
        magnitude_difference=(abs(abs(native) - abs(independent))
                              if native is not None and independent is not None else None),
        radius_error=row.get("radius_error"),
    ))
offset_pairs = [r for r in sign_rows if r["opposite_signs"]]
report["offset_622"] = dict(
    rows=sign_rows,
    opposite_sign_rows=len(offset_pairs),
    max_magnitude_difference=max((r["magnitude_difference"] for r in offset_pairs), default=None),
    max_radius_error=max((r["radius_error"] for r in sign_rows if r["radius_error"] is not None), default=None),
    stated_max_opposite_sign_offset_error=p622.get("maximum_opposite_sign_offset_error"),
    stated_max_radius_error=p622.get("maximum_radius_error"),
    tolerance=p622.get("tolerance"),
    piston_cases=p622.get("piston_cases"),
    production_scope=p622.get("production"),
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=True, indent=1), encoding="utf-8")

print("wrote", OUT, OUT.stat().st_size, "bytes")
p = report["plate_catalog"]
print("plate:", p["catalog_file"], "parsed", p["parsed_rows"], "native", p["native_rows"],
      "maxR", p["max_radius_difference"], "maxD", p["max_diameter_difference"],
      "outside", p["rows_outside_tolerance"], "mismatch", p["identity_or_code_mismatches"],
      "passed", p["passed"])
s = report["slope_summary_641"]
print("slope641:", s["count"], "maxerr", s["max_absolute_error"], "all_pass", s["all_pass"],
      "verdict_agreement", s["stored_verdict_agreement"], "error_agreement", s["stored_error_agreement"])
o = report["offset_622"]
print("offset622: opposite-sign rows", o["opposite_sign_rows"],
      "max magnitude diff", o["max_magnitude_difference"],
      "max radius error", o["max_radius_error"])
