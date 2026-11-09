"""CV-01.FftSurfaceMtf retained-data independent numerical control experiments.

Pure offline (no OpticStudio). Reproduces the cross-outlet autocorrelation baseline
from the 605 coherent-pupil record, then runs single-factor controls (amplitude
normalization, pupil-support threshold, center/DC slice, frequency-node/projection).
For 509 it locates the independent traced off-axis error from the retained ray data
and quantifies the frequency-node mismatch. Threshold absolute 0.005 is maintained.

Writes a dated offline diagnostic under .local/evidence/development/CV-01/.
"""
import json
import math
from pathlib import Path

import numpy as np

R = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
OUT = R / ".local/evidence/development/CV-01/retained-controls-20261109/controls.json"
TOL = 0.005
COHERENT = R / ".local/runs/runs/surface_mtf605_coherent_pupil_7d0d1a6c1d/coherent-pupil.json"
F509 = R / ".local/fixtures/surface_mtf509_pupil_3517781fe1"


def pupil_autocorrelation(pupil):
    """Identical to tests/support/diffraction_reference.pupil_autocorrelation."""
    pupil = np.asarray(pupil, dtype=complex)
    power = float(np.sum(abs(pupil) ** 2))
    shape = tuple(2 * n for n in pupil.shape)
    spectrum = np.fft.fft2(pupil, s=shape)
    return abs(np.fft.fftshift(np.fft.ifft2(abs(spectrum) ** 2))) / power


def crop(acf, cx, cy, ny, nx, dy=0, dx=0):
    cy0, cx0 = np.array(acf.shape) // 2
    y = cy0 - cy + dy
    x = cx0 - cx + dx
    return acf[y:y + ny, x:x + nx]


def errors(pred, mtf):
    d = np.abs(pred - mtf)
    return dict(maximum_error=float(d.max()), rms_error=float(np.sqrt(np.mean(d ** 2))),
                passed=bool(d.max() <= TOL))


def summarize(d):
    return dict(maximum_error=d["maximum_error"], rms_error=d["rms_error"], passed=d["passed"])


report = {"threshold_absolute": TOL,
          "note": "offline control experiments on retained data; no native run",
          "sections": {}}

records = json.loads(COHERENT.read_text(encoding="utf-8"))["records"]

# ---------------------------------------------------------------- baseline 605
baseline = {}
cache = {}
for rec in records:
    f = rec["field"]
    real = np.asarray(rec["modes"]["Real_Coherent"]["grids"][0]["values"], dtype=float)
    imag = np.asarray(rec["modes"]["Imaginary_Coherent"]["grids"][0]["values"], dtype=float)
    mtfg = rec["modes"]["MTF_Incoherent"]["grids"][0]
    mtf = np.asarray(mtfg["values"], dtype=float)
    pupil = real + 1j * imag
    acf = pupil_autocorrelation(pupil)
    cx = mtfg["zero_frequency_index"]["x"]
    cy = mtfg["zero_frequency_index"]["y"]
    pred = crop(acf, cx, cy, mtfg["ny"], mtfg["nx"])
    b = errors(pred, mtf)
    b["stored_maximum_error"] = rec["autocorrelation"]["maximum_error"]
    b["stored_rms_error"] = rec["autocorrelation"]["rms_error"]
    b["reproduced"] = abs(b["maximum_error"] - rec["autocorrelation"]["maximum_error"]) <= 1e-9
    baseline[str(f)] = b
    cache[f] = dict(real=real, imag=imag, pupil=pupil, acf=acf, mtf=mtf, mtfg=mtfg, cx=cx, cy=cy)
report["sections"]["baseline_605"] = baseline

# ------------------------------------------------- E1 amplitude normalization
def e1(f):
    c = cache[f]
    out = {}
    # E1a global scalar normalisation (expect invariant)
    p = c["pupil"] / np.max(np.abs(c["pupil"]))
    out["E1a_global_scalar"] = summarize(errors(crop(pupil_autocorrelation(p), c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"]), c["mtf"]))
    # E1b per-mode normalisation
    r = c["real"] / (np.max(np.abs(c["real"])) or 1.0)
    i = c["imag"] / (np.max(np.abs(c["imag"])) or 1.0)
    out["E1b_per_mode"] = summarize(errors(crop(pupil_autocorrelation(r + 1j * i), c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"]), c["mtf"]))
    # E1c phase-only (unit amplitude inside support, keep phase)
    amp = np.abs(c["pupil"])
    phase = np.where(amp > 0, c["pupil"] / np.where(amp > 0, amp, 1), 0)
    out["E1c_phase_only"] = summarize(errors(crop(pupil_autocorrelation(phase), c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"]), c["mtf"]))
    # amplitude stats
    out["amplitude"] = {"min": float(amp.min()), "max": float(amp.max()),
                        "support_gt_1e-10": int((amp > 1e-10).sum()),
                        "support_total": int(amp.size)}
    return out


# --------------------------------------------------------- E2 support threshold
def e2(f, thresholds=(0.0, 1e-10, 1e-6, 1e-3, 1e-2)):
    c = cache[f]
    amp = np.abs(c["pupil"])
    amax = float(amp.max()) or 1.0
    rows = []
    for t in thresholds:
        tt = t * amax if t >= 1e-3 else t
        p = np.where(amp > tt, c["pupil"], 0)
        e = errors(crop(pupil_autocorrelation(p), c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"]), c["mtf"])
        rows.append(dict(threshold=tt, support=int((amp > tt).sum()), **summarize(e)))
    # explicit relative 1e-3*max handled above via tt for t>=1e-3 (1e-3->1e-3*max); add explicit rel
    p = np.where(amp > 1e-3 * amax, c["pupil"], 0)
    rows.append(dict(threshold=1e-3 * amax, label="relative_1e-3_max", support=int((amp > 1e-3 * amax).sum()),
                     **summarize(errors(crop(pupil_autocorrelation(p), c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"]), c["mtf"]))))
    return rows


# ------------------------------------------------------------ E3 center / DC
def e3(f):
    c = cache[f]
    rows = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            pred = crop(c["acf"], c["cx"], c["cy"], c["mtfg"]["ny"], c["mtfg"]["nx"], dy=dy, dx=dx)
            rows.append(dict(dy=dy, dx=dx, **summarize(errors(pred, c["mtf"]))))
    return dict(zero_frequency_index={"x": c["cx"], "y": c["cy"]}, grid_shape=list(c["mtf"].shape), rows=rows)


# ------------------------------------------------ E4 frequency node / projection
def e4(f):
    c = cache[f]
    g = c["mtfg"]
    na = g.get("native_axes") or {}
    return dict(grid_dx=g["dx"], native_axes_dx=na.get("dx"), grid_min_x=g["min_x"],
                native_axes_min_x=na.get("min_x"),
                dx_ratio=(na.get("dx") / g["dx"] if na.get("dx") else None),
                lag_convention=g.get("frequency_sampling"),
                note="2x zero-padded autocorrelation lag spacing equals pupil grid spacing; "
                     "integer lag is exact when grid dx == MTF dx")


report["sections"]["E1_amplitude"] = {str(f): e1(f) for f in (1, 3)}
report["sections"]["E2_support_threshold"] = {str(f): e2(f) for f in (1, 3)}
report["sections"]["E3_center_dc"] = {str(f): e3(f) for f in (1, 3)}
report["sections"]["E4_frequency_node"] = {str(f): e4(f) for f in (1, 3)}

# --------------------------------------------------- 509 independent traced data
s509 = {}
for f, rayname in ((1, "field1-rays.json"), (3, "field3-rays.json")):
    rays = json.loads((F509 / rayname).read_text(encoding="utf-8"))
    iy = np.array([r["iy"] for r in rays]); ix = np.array([r["ix"] for r in rays])
    opd = np.array([r["ray"]["opd"] for r in rays]); inten = np.array([r["ray"]["intensity"] for r in rays])
    ec = np.array([r["ray"]["error_code"] for r in rays]); vc = np.array([r["ray"]["vignette_code"] for r in rays])
    px = np.array([r["ray"]["input"]["px"] for r in rays]); py = np.array([r["ray"]["input"]["py"] for r in rays])
    s509[str(f)] = dict(
        rays=len(rays), iy_range=[int(iy.min()), int(iy.max())], ix_range=[int(ix.min()), int(ix.max())],
        unique_cells=int(len(set(zip(iy.tolist(), ix.tolist())))),
        intensity_unique=sorted(set(np.round(inten, 12).tolist()))[:5],
        intensity_is_uniform=bool(np.allclose(inten, inten[0])),
        opd_range=[float(opd.min()), float(opd.max())],
        error_codes=sorted(set(ec.tolist())), vignette_codes=sorted(set(vc.tolist())),
        px_range=[float(px.min()), float(px.max())], py_range=[float(py.min()), float(py.max())],
    )

# 509 comparison axis facts + frequency-spacing mismatch, from stored comparisons
d509 = json.loads((F509 / "autocorrelation.json").read_text(encoding="utf-8"))
comp = {}
for rec in d509:
    g = rec["result"]["grids"][0]
    grid_dx = g["dx"]
    modes = {}
    for cname, cd in rec["comparisons"].items():
        pts = cd["points"]
        modes[cname] = dict(
            frequency_spacing=cd["frequency_spacing"],
            spacing_ratio_vs_grid=cd["frequency_spacing"] / grid_dx,
            maximum_error=cd["maximum_error"],
            passed=bool(cd["maximum_error"] <= TOL),
            worst_point=max(pts, key=lambda p: abs(p["error"])),
            error_by_frequency=[{"fx": p["fx"], "fy": p["fy"], "error": p["error"]}
                                for p in pts if p["fx"] != 0 or p["fy"] != 0],
        )
    comp[str(rec["field"])] = dict(grid_dx=grid_dx, native_axes_dx=(g.get("native_axes") or {}).get("dx"),
                                   zero_frequency_index=g["zero_frequency_index"], modes=modes,
                                   pupil_power=rec["pupil_power"], valid_samples=rec["valid_samples"])

report["sections"]["509_rays"] = s509
report["sections"]["509_comparisons"] = comp
report["sections"]["509_amplitude_degenerate"] = {
    str(f): s509[str(f)]["intensity_is_uniform"] for f in (1, 3)}

# --------------------------------------- 509 actual recomputation from traced rays
def _bilinear(A, x, y):
    x0 = int(np.floor(x)); y0 = int(np.floor(y))
    tx = x - x0; ty = y - y0
    return (A[y0, x0] * (1 - tx) * (1 - ty) + A[y0, x0 + 1] * tx * (1 - ty)
            + A[y0 + 1, x0] * (1 - tx) * ty + A[y0 + 1, x0 + 1] * tx * ty)

def recompute_509(f, rayname):
    rays = json.loads((F509 / rayname).read_text(encoding="utf-8"))
    N = 256
    pupil = np.zeros((N, N), dtype=complex)
    for r in rays:
        pupil[r["iy"], r["ix"]] = math.sqrt(r["ray"]["intensity"]) * np.exp(2j * math.pi * r["ray"]["opd"])
    A = pupil_autocorrelation(pupil)
    cy0, cx0 = np.array(A.shape) // 2
    rec = d509  # list; pick matching field
    record = next(r for r in rec if r["field"] == f)
    modes = {}
    for cname in ("paraxial", "real", "native_cutoff"):
        cd = record["comparisons"][cname]
        sp = cd["frequency_spacing"]
        pts = []
        for pt in cd["points"]:
            fx, fy = pt["fx"], pt["fy"]
            val = float(np.real(_bilinear(A, cx0 + fx / sp, cy0 + fy / sp)))
            pts.append(dict(fx=fx, fy=fy, native=pt["native"], reference_stored=pt["reference"],
                            reference_recomputed=val,
                            error_stored=abs(pt["native"] - pt["reference"]),
                            error_recomputed=abs(pt["native"] - val),
                            stored_matches_recomputed=bool(abs(pt["reference"] - val) <= 1e-9)))
        modes[cname] = dict(frequency_spacing=sp,
                            max_error_stored=max(q["error_stored"] for q in pts),
                            max_error_recomputed=max(q["error_recomputed"] for q in pts),
                            all_points_match_stored=all(q["stored_matches_recomputed"] for q in pts),
                            points=pts)
    return dict(pupil_power_recomputed=float(np.sum(abs(pupil) ** 2)),
                pupil_power_stored=record["pupil_power"],
                support_cells=int((abs(pupil) > 0).sum()), dc=float(np.real(A[cy0, cx0])),
                modes=modes)

report["sections"]["509_recompute"] = {str(f): recompute_509(f, rn)
                                        for f, rn in ((1, "field1-rays.json"), (3, "field3-rays.json"))}
report["sections"]["E4_metadata_audit_note"] = (
    "E4 compares grid.dx vs grid.native_axes.dx metadata only; it is a metadata audit, not a new interpolation experiment")
report["caveats"] = {
    "E1": "global scalar normalisation invariance only shows global scaling has no effect; it does NOT exclude native spatial amplitude weighting (E1c phase-only worsens, so amplitude weighting does matter)",
    "E2": "threshold sweep is applied on the native grid only; it does NOT test post-projection support-domain differences",
    "E3": "only +/-1 pixel grid offsets were tested; sub-pixel/center factors beyond 1 px are NOT excluded",
    "E4": "metadata audit only (grid dx vs native_axes dx); not an interpolation experiment",
    "509": "large fy error supports an anisotropic-projection hypothesis only; it does NOT establish the root cause or that the residual is intrinsic; amplitude is degenerate (intensity=1) and all rays are valid, which limits what those null results can exclude",
}

# --------------------------------------------------------------------- save
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size, "bytes")
print("\n-- baseline 605 --")
for f, b in baseline.items():
    print(f"  field {f}: max={b['maximum_error']:.6e} rms={b['rms_error']:.3e} "
          f"stored={b['stored_maximum_error']:.6e} reproduced={b['reproduced']}")
print("\n-- E1 amplitude (field 3) --")
for k, v in report["sections"]["E1_amplitude"]["3"].items():
    if isinstance(v, dict) and "maximum_error" in v:
        print(f"  {k}: max={v['maximum_error']:.6e} passed={v['passed']}")
    else:
        print(f"  {k}: {v}")
print("\n-- E2 support threshold (field 3) --")
for row in report["sections"]["E2_support_threshold"]["3"]:
    print(f"  t={row['threshold']:.3e} support={row['support']} max={row['maximum_error']:.6e} passed={row['passed']}")
print("\n-- E3 center/DC (field 3) --")
for row in report["sections"]["E3_center_dc"]["3"]["rows"]:
    print(f"  dy={row['dy']} dx={row['dx']} max={row['maximum_error']:.6e} passed={row['passed']}")
print("\n-- E4 frequency node --")
for f, v in report["sections"]["E4_frequency_node"].items():
    print(f"  field {f}: grid_dx={v['grid_dx']:.6f} native_axes_dx={v['native_axes_dx']:.6f} ratio={v['dx_ratio']}")
print("\n-- 509 rays --")
for f, v in s509.items():
    print(f"  field {f}: rays={v['rays']} unique_cells={v['unique_cells']} intensity_uniform={v['intensity_is_uniform']} "
          f"errcodes={v['error_codes']} vign={v['vignette_codes']} opd={v['opd_range']}")
print("\n-- 509 comparisons --")
for f, v in comp.items():
    print(f"  field {f}: grid_dx={v['grid_dx']:.6f}")
    for m, md in v["modes"].items():
        print(f"     {m}: spacing={md['frequency_spacing']:.6f} ratio={md['spacing_ratio_vs_grid']:.4f} "
              f"maxerr={md['maximum_error']:.6f} passed={md['passed']}")
