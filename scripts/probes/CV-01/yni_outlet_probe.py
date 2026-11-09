import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from zemax_mcp.analyses import scalar_settings
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import new_analysis


def main():
    output = ROOT / ".local/evidence/development/CV-01/yni-outlet-20261108"
    output.mkdir(parents=True, exist_ok=False)
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    record = {"analysis": "YNIContributions", "input": None}
    try:
        record["connect"] = backend.dispatch("connect", {})
        assert record["connect"]["ok"]
        lens = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        record["open_lens"] = backend.dispatch("open_lens", {"path": str(lens)})
        if not record["open_lens"]["ok"]:
            raise RuntimeError(record["open_lens"])
        record["input"] = str(lens)
        tool = new_analysis(backend, "YNIContributions")
        record["settings"] = scalar_settings(unwrap(tool.GetSettings()))
        tool.ApplyAndWaitForCompletion()
        result = unwrap(tool.GetResults())
        record["result"] = {
            "type": str(result.GetType().FullName), "valid": bool(result.IsValid),
            "properties": [{"name": p.Name, "type": str(p.PropertyType)} for p in result.GetType().GetProperties()],
            "methods": [str(m) for m in result.GetType().GetMethods() if m.IsPublic and not m.IsSpecialName],
            "counts": {n: int(getattr(result, n)) for n in (
                "NumberOfMessages", "NumberOfDataSeries", "NumberOfDataGrids", "NumberOfDataGridsRgb",
                "NumberOfDataScatterPoints", "NumberOfDataScatterPointsRgb") if hasattr(result, n)},
            "messages": [str(result.GetMessageAt(i).Text) for i in range(int(result.NumberOfMessages))],
            "header": None if result.HeaderData is None or result.HeaderData.Lines is None else [str(x) for x in result.HeaderData.Lines],
            "text_export": bool(result.GetTextFile(str(output / "yni.txt"))),
        }
        record["close"] = backend._close_task_native({"native": tool})
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        record["disconnect"] = backend.dispatch("disconnect", {})
        (output / "summary.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "valid": record.get("result", {}).get("valid"), "counts": record.get("result", {}).get("counts"), "text": record.get("result", {}).get("text_export"), "close": record.get("close"), "disconnect": record.get("disconnect", {}).get("ok"), "error": record.get("error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
