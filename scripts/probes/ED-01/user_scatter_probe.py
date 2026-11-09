"""Inspect native User-scatter factory and current settings interfaces."""
import json
from datetime import datetime
from pathlib import Path

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def describe(obj):
    typ = obj.GetType()
    return {
        "type": str(typ.FullName),
        "properties": [{"name": str(p.Name), "type": str(p.PropertyType.FullName),
                        "readable": bool(p.CanRead), "writable": bool(p.CanWrite)}
                       for p in typ.GetProperties()],
        "methods": sorted({str(m.Name) for m in typ.GetMethods()}),
    }


def run(output: Path) -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    report = {"available_scatter_dlls": []}
    try:
        report["connect"] = backend.dispatch("connect", {})
        if not report["connect"]["ok"]:
            return report
        report["new_system"] = backend.dispatch("new_system", {"mode": "Sequential"})
        if not report["new_system"]["ok"]:
            return report
        row = backend.system.LDE.GetSurfaceAt(1)
        data = row.ScatteringData
        native = backend.native
        lambertian_type = native.enum(native.api.Editors.LDE.SurfaceScatteringTypes, "Lambertian")
        lambertian = data.CreateScatteringTypeSettings(lambertian_type)
        lambertian._S_Lambertian.ScatterFraction = 0.1
        report["lambertian_adopted"] = bool(data.ChangeScatteringTypeSettings(lambertian))
        report["active_type"] = str(data.CurrentType)
        report["scattering_data"] = describe(data)
        current = data.CurrentTypeSettings
        report["current_settings"] = describe(current)
        try:
            user = current._S_User
            report["current_user_settings"] = describe(user)
            try:
                report["available_scatter_dlls"] = [str(x) for x in user.GetAvailableDLLNames()]
            except Exception as exc:
                report["dll_query_error"] = {"type": type(exc).__name__, "message": str(exc)}
        except Exception as exc:
            report["current_user_error"] = {"type": type(exc).__name__, "message": str(exc)}
        try:
            user_kind = native.enum(native.api.Editors.LDE.SurfaceScatteringTypes, "User")
            data.CreateScatteringTypeSettings(user_kind)
            report["factory"] = "succeeded"
        except Exception as exc:
            report["factory"] = {"type": type(exc).__name__, "message": str(exc)}
        report["public_resource_query"] = backend.dispatch(
            "get_system_resources", {"kind": "scattering_files", "scattering_type": "User", "surface": 1})
    except Exception as exc:
        report["probe_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["disconnect"] = backend.dispatch("disconnect", {})
        report["native_closed"] = backend.native.application is None
        (output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    folder = Path(".local/runs/runs") / ("user_scatter_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    result = run(folder)
    print(json.dumps({"output": str(folder.resolve()), "active_type": result.get("active_type"),
                      "current_user_error": result.get("current_user_error"),
                      "available_scatter_dlls": result.get("available_scatter_dlls"),
                      "factory": result.get("factory"), "public_resource_query": result.get("public_resource_query"),
                      "native_closed": result.get("native_closed"), "probe_error": result.get("probe_error")},
                     ensure_ascii=False, indent=2))
