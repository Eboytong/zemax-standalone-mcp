"""Offline, read-only checks for D002 material reports (planning stage).

Reads installed AGF catalogs and previously saved native report text (read-only).
Writes nothing. Chinese tokens are written as unicode escapes so this file stays
ASCII-safe regardless of the shell that created it.
"""
import hashlib
import json
import math
import sys
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GC = Path.home() / "Documents" / "Zemax" / "Glasscat"
INSTALL_GC = Path(r"C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Glasscat")
MAIN = Path(r"C:\Users\tonge\Desktop\Zemax_MCP\.local\evidence\development\MA-01")

GLASS_NAME = "\u73bb\u7483\u540d\u79f0"   # glass name
WAVELENGTH = "\u6ce2\u957f"                # wavelength

REPORTS = {
    "glass_map": "glass-map-20261107",
    "dispersion_diagram": "dispersion-diagram-20261107",
    "dispersion_vs_wavelength": "dispersion-vs-wavelength-20261107",
}


def native_path(kind):
    return next((MAIN / REPORTS[kind] / "native").rglob("*_native.txt"))


def read_native(path):
    """Native analysis text is UTF-16LE with BOM."""
    return path.read_text(encoding="utf-16", errors="replace")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def agf_entries(path):
    out = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[0] == "NM":
            try:
                # Four SCHOTT entries write the formula as 2.00000E+00.
                out[parts[1]] = dict(formula=int(float(parts[2])), nd=Decimal(parts[4]), vd=Decimal(parts[5]))
            except (ValueError, ArithmeticError):
                continue
    return out


def agf_cd(path, name):
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.split()[:2] == ["NM", name]:
            for follow in lines[i + 1:i + 8]:
                if follow.startswith("CD "):
                    return [float(v) for v in follow.split()[1:7]]
    return []


def parse_report_rows(text):
    rows, started = [], False
    for line in text.splitlines():
        cells = line.split()
        if not started:
            started = len(cells) == 3 and cells[0] == GLASS_NAME
            continue
        if len(cells) == 3:
            try:
                rows.append((cells[0], Decimal(cells[1]), Decimal(cells[2])))
            except ArithmeticError:
                continue
        elif rows and line.strip():
            break
    return rows


def parse_curve(text):
    x, y, started = [], [], False
    for line in text.splitlines():
        if not started:
            started = line.startswith(WAVELENGTH + "\t")
            continue
        cells = line.split()
        if len(cells) == 2:
            try:
                x.append(float(cells[0]))
                y.append(float(cells[1]))
            except ValueError:
                continue
    return x, y


def sellmeier1(um, c):
    s = um * um
    return math.sqrt(1 + sum(c[i] * s / (s - c[i + 1]) for i in (0, 2, 4)))


def analytic_derivative(um, c):
    n = sellmeier1(um, c)
    return -um / n * sum(c[i] * c[i + 1] / (um * um - c[i + 1]) ** 2 for i in (0, 2, 4))


schott_path = GC / "SCHOTT.AGF"
schott = agf_entries(schott_path)
rad = agf_entries(GC / "Rad_Hard.AGF")
header = next(l.strip() for l in schott_path.read_text(encoding="utf-8-sig", errors="replace").splitlines() if l.strip())

rows = parse_report_rows(read_native(native_path("glass_map")))
by_upper = {k.upper(): k for k in schott}

matched, mismatches, missing = [], [], []
for name, nd, vd in rows:
    key = by_upper.get(name.upper())
    if key is None:
        missing.append(name)
        continue
    entry = schott[key]
    matched.append(name)
    nd_err, vd_err = abs(nd - entry["nd"]), abs(vd - entry["vd"])
    if nd_err > Decimal("0.000005") or vd_err > Decimal("0.005"):
        mismatches.append(dict(material=name, agf=key, nd_error=str(nd_err), vd_error=str(vd_err)))

seven = ["LF5HTI", "LLF1HTI", "N-BK7HTI", "N-SF57HTULTRA", "N-SF6HTULTRA", "N-SK5HTI", "SF57HTULTRA"]
seven_detail = []
for name in seven:
    key = by_upper.get(name)
    row = next((r for r in rows if r[0] == name), None)
    entry = schott.get(key) if key else None
    seven_detail.append(dict(report_name=name, agf_spelling=key,
                             report_nd=float(row[1]) if row else None,
                             report_vd=float(row[2]) if row else None,
                             agf_nd=float(entry["nd"]) if entry else None,
                             agf_vd=float(entry["vd"]) if entry else None,
                             exact_case_hit=name in schott))

schott_cd, rad_cd = agf_cd(schott_path, "BK7G18"), agf_cd(GC / "Rad_Hard.AGF", "BK7G18")
x_n, y_n = parse_curve(read_native(native_path("dispersion_diagram")))
x_d, y_d = parse_curve(read_native(native_path("dispersion_vs_wavelength")))

index_errors = [abs(n - sellmeier1(um, schott_cd)) for um, n in zip(x_n, y_n)]
analytic_errors = [abs(d - analytic_derivative(um, schott_cd)) for um, d in zip(x_d, y_d)]
over = [dict(wavelength_um=um, error=e) for um, e in zip(x_d, analytic_errors) if e > 5.1e-8]
fd_errors = [abs(y_d[i] - (y_n[i + 1] - y_n[i - 1]) / (x_n[i + 1] - x_n[i - 1])) for i in range(1, len(x_n) - 1)]

print(json.dumps(dict(
    catalog=dict(path=str(schott_path), header=header, sha256=sha256(schott_path), nm_entries=len(schott),
                 install_copy=str(INSTALL_GC / "SCHOTT.AGF"),
                 install_copy_identical=sha256(INSTALL_GC / "SCHOTT.AGF") == sha256(schott_path)),
    glass_map=dict(report_rows=len(rows), matched_case_insensitive=len(matched),
                   unmatched=missing, mismatches=mismatches,
                   report_count_346_expected=len(rows) == 346,
                   seven=seven_detail),
    bk7g18=dict(schott=dict(nd=str(schott["BK7G18"]["nd"]), vd=str(schott["BK7G18"]["vd"]), formula=schott["BK7G18"]["formula"], cd=schott_cd),
                rad_hard=dict(nd=str(rad["BK7G18"]["nd"]), vd=str(rad["BK7G18"]["vd"]), formula=rad["BK7G18"]["formula"], cd=rad_cd),
                index_at_0p5876_um=dict(schott=sellmeier1(0.5876, schott_cd))),
    dispersion=dict(points_n=len(x_n), points_d=len(x_d),
                    wavelength_range_um=[x_n[0], x_n[-1]] if x_n else None,
                    max_index_error=max(index_errors) if index_errors else None,
                    max_analytic_error=max(analytic_errors) if analytic_errors else None,
                    analytic_over_5p1e_8=over,
                    max_centered_difference_error=max(fd_errors) if fd_errors else None,
                    centered_difference_points=len(fd_errors)),
), indent=2, ensure_ascii=False))
