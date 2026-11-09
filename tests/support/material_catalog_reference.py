"""Read AGF catalogs and match material report rows against them.

`parse_catalog` reads the `NM` rows of an AGF catalog text into an upper-case
index plus an identity record (catalog path, `CC` header line, entry count).
Names keep their catalog spelling (`LF5HTi`) because the native report prints
upper case. Numeric dispersion references reuse
`tests.support.finite_reference` (glass_coefficients, sellmeier).
"""
from decimal import Decimal
from pathlib import Path

ND_TOLERANCE = Decimal("0.000005")
VD_TOLERANCE = Decimal("0.005")


def parse_catalog(text, path=None):
    """Parse AGF catalog text into (identity, entries).

    AGF `NM` rows are `NM <name> <formula> <code> <Nd> <Vd> ...`; four installed
    SCHOTT entries write the formula as `2.00000E+00`, so the formula is read
    through `int(float(...))`.
    """
    header, entries = "", {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("CC ") and not header:
            header = stripped[3:].strip()
            continue
        parts = stripped.split()
        if parts[0] != "NM" or len(parts) < 6:
            continue
        try:
            formula = int(float(parts[2]))
            refractive_index_nd = Decimal(parts[4])
            abbe_vd = Decimal(parts[5])
        except (ValueError, ArithmeticError):
            continue
        entries[parts[1].upper()] = dict(catalog_name=parts[1], formula=formula,
            refractive_index_nd=refractive_index_nd, abbe_vd=abbe_vd)
    return dict(path=str(path) if path else None, header=header, material_count=len(entries)), entries


def read_catalog(path):
    """Read an AGF catalog file; see `parse_catalog` for the parsed structure."""
    path = Path(path)
    return parse_catalog(path.read_text(encoding="utf-8-sig", errors="replace"), path)


def catalog_selection(loaded_catalogs):
    """Record the only formal selection the four reports share: system catalogs."""
    return dict(material_catalogs=list(loaded_catalogs),
        source="system settings material_catalogs (no per-analysis catalog selector)")


def match_rows(rows, entries, nd_tolerance=ND_TOLERANCE, vd_tolerance=VD_TOLERANCE):
    """Match native report rows to catalog entries by case-insensitive name.

    `rows` are the adapter's `glass_map` rows (material, refractive_index_nd,
    abbe_vd). Both names are preserved; errors are exact Decimals so displayed
    rounding boundaries stay exact.
    """
    matched, mismatched, missing = [], [], []
    for row in rows:
        entry = entries.get(str(row["material"]).upper())
        if entry is None:
            missing.append(dict(report_name=row["material"]))
            continue
        nd_error = abs(Decimal(str(row["refractive_index_nd"])) - entry["refractive_index_nd"])
        vd_error = abs(Decimal(str(row["abbe_vd"])) - entry["abbe_vd"])
        record = dict(report_name=row["material"], catalog_name=entry["catalog_name"],
            nd_error=nd_error, vd_error=vd_error)
        if nd_error > nd_tolerance or vd_error > vd_tolerance:
            mismatched.append(record)
        else:
            matched.append(record)
    return dict(matched=matched, mismatched=mismatched, missing=missing,
        nd_tolerance=str(nd_tolerance), vd_tolerance=str(vd_tolerance))
