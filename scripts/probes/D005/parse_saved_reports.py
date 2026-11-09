"""Offline control probe: parse the saved D005 native reports.

No OpticStudio application is created.  The probe only reads the UTF-16 text
reports that were exported earlier and runs them through the offline parsers in
``zemax_mcp.image_viewers``, recording dimensions, headers and consistency
checks so the parsers are proven against real native output.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from zemax_mcp.image_viewers import parse_report  # noqa: E402

DEFAULT_EVIDENCE = ROOT / ".local/evidence/development/CV-02/probe442-b005"
REPORTS = {
    "light_source": "LightSourceAnalysis.txt",
    "partially_coherent_image": "PartiallyCoherentImageAnalysis.txt",
    "extended_diffraction_image": "ExtendedDiffractionImageAnalysis.txt",
}
DEFAULT_OUTPUT = ROOT / ".local" / "coordination" / "d005-saved-report-parse.json"


def decode(path):
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def checks(record):
    out = {"dimensions_match_header": None}
    pixels = record.get("display_pixels") or record.get("pixels")
    if pixels:
        out["dimensions_match_header"] = [record["row_count"], record["column_count"]] == [pixels[1], pixels[0]]
    grid = record.get("grid") or []
    if grid:
        flat = [value for row in grid for value in row]
        out["cell_count"] = len(flat)
        out["minimum"] = min(flat)
        out["maximum"] = max(flat)
        out["non_negative"] = min(flat) >= 0.0
    return out


def probe(evidence=None, output=None):
    evidence = Path(evidence or DEFAULT_EVIDENCE)
    output = Path(output or DEFAULT_OUTPUT)
    items = []
    for kind, name in REPORTS.items():
        path = evidence / name
        entry = {"kind": kind, "report": str(path), "exists": path.is_file()}
        if not path.is_file():
            entry["error"] = "report_not_found"
            items.append(entry)
            continue
        text, encoding = decode(path)
        entry["encoding"] = encoding
        entry["characters"] = len(text)
        try:
            record = parse_report(kind, text)
        except Exception as exc:  # noqa: BLE001 - probe must record, not raise
            entry["error"] = f"{type(exc).__name__}: {exc}"
            items.append(entry)
            continue
        record = parse_report(kind, text)
        entry["parsed"] = {key: value for key, value in record.items() if key != "grid"}
        entry["checks"] = checks(record)
        items.append(entry)
    record = {"schema": "d005-saved-report-parse/1", "evidence": str(evidence),
              "application_created": False, "items": items}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    result = probe(target)
    for item in result["items"]:
        state = item.get("error") or item["parsed"].get("imaging") or item["parsed"].get("reason")
        print(item["kind"], "->", state)
    print("wrote", DEFAULT_OUTPUT)
