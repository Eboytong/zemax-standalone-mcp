"""Probe native sequential BSDF settings using an owned scratch project."""
import json
import shutil
import os
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT / 'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(output: Path) -> dict:
    source = Path(r"C:\Program Files\Ansys Inc\v242\Zemax OpticStudio\ZemaxData\ScatterData\BrownVinyl.bsdf")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ['ZEMAX_STATE_DIR'] = str(output / 'state')
    project = output / "bsdf-probe.zos"
    resource_dir = output / "ScatterData"
    resource_dir.mkdir()
    if not source.is_file():
        raise FileNotFoundError(source)
    shutil.copy2(source, resource_dir / source.name)

    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    report = {"source": str(source), "project_resource": str(resource_dir / source.name),
              "source_root": str(ROOT), "trials": [],
              "hypothesis": "BRDF-only input might require a reflecting sequential surface"}
    try:
        report["connect"] = backend.dispatch("connect", {})
        if not report["connect"]["ok"]:
            return report
        report["new_system"] = backend.dispatch("new_system", {"mode": "Sequential"})
        if not report["new_system"]["ok"]:
            return report
        backend.system.SaveAs(str(project))
        row = backend.system.LDE.GetSurfaceAt(1)
        data = row.ScatteringData
        kind = backend.native.enum(backend.native.api.Editors.LDE.SurfaceScatteringTypes, "BSDF")
        holder = data.CreateScatteringTypeSettings(kind)
        setting = holder._S_BSDF
        report["native_type"] = str(setting.GetType().FullName)
        report["properties"] = [
            {"name": str(p.Name), "type": str(p.PropertyType.FullName),
             "readable": bool(p.CanRead), "writable": bool(p.CanWrite)}
            for p in setting.GetType().GetProperties()
        ]
        report["methods"] = sorted({str(m.Name) for m in setting.GetType().GetMethods()})
        report["available_file_names"] = [str(x) for x in setting.GetAvailableFileNames()]
        for material in ['', 'MIRROR']:
            row.Material = material
            for value in [source.name, str(resource_dir / source.name)]:
                item = {"requested_material": material, "actual_material": str(row.Material),
                        "requested_file_name": value}
                try:
                    holder = data.CreateScatteringTypeSettings(kind)
                    setting = holder._S_BSDF
                    item['available_file_names'] = [str(x) for x in setting.GetAvailableFileNames()]
                    item['precommit_result'] = bool(data.ChangeScatteringTypeSettings(holder))
                    item['committed_file_names'] = [str(x) for x in data.CurrentTypeSettings._S_BSDF.GetAvailableFileNames()]
                    setting.FileName = value
                    item["setter_readback"] = str(setting.FileName)
                    item["change_result"] = bool(data.ChangeScatteringTypeSettings(holder))
                    current = data.CurrentTypeSettings._S_BSDF
                    item["active_type"] = str(data.CurrentType)
                    item["active_file_name"] = str(current.FileName)
                    item["active_scatter_fraction"] = float(current.ScatterFraction)
                except Exception as exc:
                    item["error"] = {"type": type(exc).__name__, "message": str(exc)}
                report['trials'].append(item)
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report['session_id'] = backend.session_id
        backend.shutdown()
        receipt = output / 'state' / 'close_receipt.json'
        report['shutdown_receipt'] = json.loads(receipt.read_text(encoding='utf-8')) if receipt.is_file() else None
        report["native_closed"] = backend.native.application is None
        (output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    from datetime import datetime
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".local/runs/runs") / ("bsdf_selector_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    result = run(folder)
    print(json.dumps({"output": str(folder.resolve()), "native_closed": result.get("native_closed"),
                      "properties": result.get("properties"), "available_file_names": result.get("available_file_names"),
                      "trials": result.get("trials"), "error": result.get("error")}, ensure_ascii=False, indent=2))
