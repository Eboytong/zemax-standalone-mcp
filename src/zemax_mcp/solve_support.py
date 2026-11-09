"""Compact validation scope; native enumeration and fixture validation stay separate."""
import json
from pathlib import Path
from importlib.resources import files
from zipimport import zipimporter

def solve_validation_summary():
    path=Path(__file__).resolve().parents[2]/"docs/reference/solve-support.json"
    if not path.is_file():
        path=Path(__file__).resolve().parent/"resources/solve-support.json"
    base=dict(reference="docs/reference/solve-support.json",native_enumeration_is_numeric_validation=False,
              zpl_macro_name_limit=dict(max_utf16_units=31,extension_included=False,
                  basis='local 2024 R2 native boundary probe; ASCII and Chinese names'),
              runtime_checks="native support, return status and actual adopted mode are checked per request",
              persistence_limits=[dict(surface_type="Hologram2",cell="parameter_13",mode="Variable",
                  required_value=1,rejected_value=0,reference="docs/topics/modeling/README.md")])
    if not path.is_file() and isinstance(__loader__, zipimporter):
        path = files("zemax_mcp").joinpath("resources/solve-support.json")
    if not path.is_file():return dict(base,status="evidence_unavailable")
    try:
        source=json.loads(path.read_text(encoding="utf-8"))
        return dict(base,status="recorded",environment=source["environment"],scope=source["scope"],
                    focused_cases=source["focused_cases"],matrix=source["matrix"],
                    detailed_records=str(path))
    except (OSError,ValueError,KeyError)as exc:
        return dict(base,status="evidence_unavailable",reason=str(exc))



def extended_solve_summary():
    """Installed ED-02 evidence, separate from the historical nine-solve matrix."""
    path=files("zemax_mcp").joinpath("resources/solve-extensions018.json")
    if not path.is_file():
        return dict(status="evidence_unavailable",reference="docs/solve-extensions.md")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError) as exc:
        return dict(status="evidence_unavailable",reason=str(exc))
