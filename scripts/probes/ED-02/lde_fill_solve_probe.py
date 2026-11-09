"""Inspect native extended solve enum/interface and cell availability."""
import json
from datetime import datetime
from pathlib import Path

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(output: Path) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    report = {}
    try:
        report["connect"] = backend.dispatch("connect", {})
        if not report["connect"]["ok"]:
            return report
        report["new_system"] = backend.dispatch("new_system", {"mode": "Sequential"})
        if not report["new_system"]["ok"]:
            return report
        native = backend.native
        solve_enum = native.api.Editors.SolveType
        report["solve_enum_names"] = native.enum_names(solve_enum)
        candidates = ("CA_fill", "DIA_fill", "DuplicateSag", "InvertSag", "MarginPercent")
        report["candidate_enum_values"] = {
            name: int(getattr(solve_enum, name)) for name in candidates
        }
        from System.Reflection import Assembly

        assembly = Assembly.LoadFrom(str(Config.from_env().install_dir / "ZOSAPI_Interfaces.dll"))
        interface = assembly.GetType("ZOSAPI.Editors.ISolveData")
        report["isolve_data_properties"] = [
            {"name": str(p.Name), "type": str(p.PropertyType.FullName),
             "can_read": bool(p.CanRead), "can_write": bool(p.CanWrite)}
            for p in interface.GetProperties()
        ]
        row = backend.system.LDE.GetSurfaceAt(1)
        cells = {}
        for name, cell in backend._cells(row):
            cells[name] = {
                "native_cell_type": str(cell.GetType().FullName),
                "is_solve_type_supported": {
                    candidate: bool(cell.IsSolveTypeSupported(native.enum(solve_enum, candidate)))
                    for candidate in candidates
                },
                "available_solves": [str(x) for x in cell.GetAvailableSolveTypes()],
            }
        report["standard_surface_cells"] = cells
        for candidate in candidates:
            try:
                created = row.SemiDiameterCell.CreateSolveType(native.enum(solve_enum, candidate))
                report.setdefault("create_solve_type", {})[candidate] = None if created is None else {
                    "type": str(created.GetType().FullName),
                    "is_valid": bool(created.IsValid),
                    "properties": [str(p.Name) for p in created.GetType().GetProperties()],
                }
            except Exception as exc:
                report.setdefault("create_solve_type", {})[candidate] = {
                    "error_type": type(exc).__name__, "error": str(exc),
                }
    except Exception as exc:
        report["probe_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["disconnect"] = backend.dispatch("disconnect", {})
        report["native_closed"] = backend.native.application is None
        (output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    folder = Path(".local/runs/runs") / ("lde_fill_solve_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    result = run(folder)
    print(json.dumps({"output": str(folder.resolve()), "candidate_enum_values": result.get("candidate_enum_values"),
                      "interface_properties": result.get("isolve_data_properties"),
                      "standard_cells": result.get("standard_surface_cells"),
                      "create_solve_type": result.get("create_solve_type"),
                      "native_closed": result.get("native_closed"), "probe_error": result.get("probe_error")},
                     ensure_ascii=False, indent=2))
