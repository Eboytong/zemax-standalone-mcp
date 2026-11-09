import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from zemax_mcp.analyses import scalar_settings
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap


def main():
    output = ROOT / ".local/evidence/development/CV-01/iso-element-drawing-20261108"
    output.mkdir(parents=True, exist_ok=False)
    source = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    record = {"analysis": "ISOElementDrawing", "input": str(source)}
    tool = None
    try:
        record["connect"] = backend.dispatch("connect", {})
        record["open_lens"] = backend.dispatch("open_lens", {"path": str(source)})
        if not record["open_lens"]["ok"]:
            raise RuntimeError(record["open_lens"])
        record["context"] = backend.context()
        before = backend.dispatch("get_surfaces", {"start": 0, "count": 20})
        record["baseline_surfaces"] = before
        analyses = backend.system.Analyses
        analysis_id = backend.native.enum(backend.native.api.Analysis.AnalysisIDM, "ISOElementDrawing")
        factory = getattr(analyses, "New_Analysis_SettingsFirst", analyses.New_Analysis)
        tool = factory(analysis_id)
        settings = unwrap(tool.GetSettings())
        record["settings_type"] = str(settings.GetType().FullName)
        record["settings"] = scalar_settings(settings)
        record["settings_members"] = sorted(str(x.Name) for x in settings.GetType().GetMembers())
        tool.ApplyAndWaitForCompletion()
        result = unwrap(tool.GetResults())
        record["result_type"] = str(result.GetType().FullName)
        record["result_members"] = sorted(str(x.Name) for x in result.GetType().GetMembers())
        record["result"] = {
            "valid": bool(result.IsValid),
            "counts": {n: int(getattr(result, n)) for n in (
                "NumberOfMessages", "NumberOfDataSeries", "NumberOfDataGrids",
                "NumberOfDataGridsRgb", "NumberOfDataScatterPoints",
                "NumberOfDataScatterPointsRgb") if hasattr(result, n)},
            "messages": [str(result.GetMessageAt(i).Text) for i in range(int(result.NumberOfMessages))],
        }
        text_path = output / "analysis.txt"
        try:
            record["result"]["text_export"] = bool(result.GetTextFile(str(text_path)))
            if text_path.exists():
                record["result"]["text_bytes"] = text_path.stat().st_size
        except Exception as exc:
            record["result"]["text_error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["surfaces_after"] = backend.dispatch("get_surfaces", {"start": 0, "count": 20})
        record["model_unchanged"] = before == record["surfaces_after"]
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if tool is not None:
            record["close"] = backend._close_task_native({"native": tool})
        record["disconnect"] = backend.dispatch("disconnect", {})
        (output / "summary.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "result": record.get("result"),
                      "settings_type": record.get("settings_type"), "close": record.get("close"),
                      "disconnect": record.get("disconnect", {}).get("ok"), "error": record.get("error")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
