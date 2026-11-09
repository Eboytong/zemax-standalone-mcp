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
    output = ROOT / ".local/evidence/development/NS-03/directivity-20261108"
    output.mkdir(parents=True, exist_ok=False)
    source = Path.home() / "Documents/Zemax/Samples/Non-sequential/Colorimetry/Example 1  Two-color mixing gives white.zos"
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    record = {"analysis": "DirectivityPlot", "input": str(source)}
    tool = None
    try:
        record["connect"] = backend.dispatch("connect", {})
        assert record["connect"]["ok"]
        record["open_lens"] = backend.dispatch("open_lens", {"path": str(source)})
        if not record["open_lens"]["ok"]:
            raise RuntimeError(record["open_lens"])
        record["context"] = backend.context()
        tool = new_analysis(backend, "DirectivityPlot")
        record["settings"] = scalar_settings(unwrap(tool.GetSettings()))
        tool.ApplyAndWaitForCompletion()
        result = unwrap(tool.GetResults())
        record["result"] = {
            "type": str(result.GetType().FullName), "valid": bool(result.IsValid),
            "counts": {n: int(getattr(result, n)) for n in (
                "NumberOfMessages", "NumberOfDataSeries", "NumberOfDataGrids", "NumberOfDataGridsRgb",
                "NumberOfDataScatterPoints", "NumberOfDataScatterPointsRgb") if hasattr(result, n)},
            "messages": [str(result.GetMessageAt(i).Text) for i in range(int(result.NumberOfMessages))],
            "header": None if result.HeaderData is None or result.HeaderData.Lines is None else [str(x) for x in result.HeaderData.Lines],
            "text_export": bool(result.GetTextFile(str(output / "directivity.txt"))),
        }
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if tool is not None:
            record["close"] = backend._close_task_native({"native": tool})
        record["disconnect"] = backend.dispatch("disconnect", {})
        (output / "summary.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "mode": record.get("context", {}).get("mode"), "valid": record.get("result", {}).get("valid"), "counts": record.get("result", {}).get("counts"), "text": record.get("result", {}).get("text_export"), "close": record.get("close"), "disconnect": record.get("disconnect", {}).get("ok"), "error": record.get("error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
