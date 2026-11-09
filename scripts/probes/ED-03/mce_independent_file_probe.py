"""Inspect installed MCE interface and runtime file methods without editing a model."""
import json
from datetime import datetime
from pathlib import Path

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(output: Path) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    report: dict = {}
    try:
        report["connect"] = backend.dispatch("connect", {})
        if not report["connect"]["ok"]:
            return report
        report["new_system"] = backend.dispatch("new_system", {"mode": "Sequential"})
        if not report["new_system"]["ok"]:
            return report

        mce = backend.system.MCE
        runtime_type = mce.GetType()
        report["runtime_type"] = str(runtime_type.FullName)
        report["runtime_methods"] = sorted(
            str(method) for method in runtime_type.GetMethods()
            if method.IsPublic and not method.IsSpecialName
        )
        report["runtime_properties"] = [
            {"name": str(prop.Name), "type": str(prop.PropertyType.FullName),
             "can_read": bool(prop.CanRead), "can_write": bool(prop.CanWrite)}
            for prop in runtime_type.GetProperties()
        ]

        from System.Reflection import Assembly
        assembly = Assembly.LoadFrom(str(Config.from_env().install_dir / "ZOSAPI_Interfaces.dll"))
        interface = assembly.GetType("ZOSAPI.Editors.MCE.IMultiConfigEditor")
        editor = assembly.GetType("ZOSAPI.Editors.IEditor")
        report["interface_methods"] = sorted(
            str(method) for method in interface.GetMethods()
            if not method.IsSpecialName
        )
        report["inherited_editor_methods"] = sorted(
            str(method) for method in editor.GetMethods()
            if not method.IsSpecialName
        )
        report["file_methods"] = {
            "runtime": [m for m in report["runtime_methods"] if any(k in m.lower() for k in ("load", "save", "file"))],
            "interface": [m for m in report["interface_methods"] if any(k in m.lower() for k in ("load", "save", "file"))],
            "inherited_editor": [m for m in report["inherited_editor_methods"] if any(k in m.lower() for k in ("load", "save", "file"))],
        }
        report["system_file_methods"] = sorted(
            str(method) for method in backend.system.GetType().GetMethods()
            if method.IsPublic and not method.IsSpecialName
            and any(k in str(method).lower() for k in ("loadfile", "saveas"))
        )
    except Exception as exc:
        report["probe_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["disconnect"] = backend.dispatch("disconnect", {})
        report["native_closed"] = backend.native.application is None
        (output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    folder = Path(".local/runs/runs") / ("mce_file_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    result = run(folder)
    print(json.dumps({"output": str(folder.resolve()), "runtime_type": result.get("runtime_type"),
                      "file_methods": result.get("file_methods"),
                      "system_file_methods": result.get("system_file_methods"),
                      "native_closed": result.get("native_closed"),
                      "probe_error": result.get("probe_error")}, ensure_ascii=False, indent=2))
