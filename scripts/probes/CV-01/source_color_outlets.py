import argparse
import json
import sys
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from zemax_mcp.analyses import scalar_settings
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import new_analysis


def describe_result(result, output, backend, task):
    result = unwrap(result)
    rt = result.GetType()
    data = {
        "result_type": str(rt.FullName),
        "valid": bool(result.IsValid),
        "properties": [
            {"name": p.Name, "type": str(p.PropertyType)}
            for p in rt.GetProperties()
        ],
        "methods": [str(m) for m in rt.GetMethods() if m.IsPublic and not m.IsSpecialName],
        "counts": {
            name: int(getattr(result, name))
            for name in (
                "NumberOfMessages", "NumberOfDataSeries", "NumberOfDataGrids",
                "NumberOfDataGridsRgb", "NumberOfDataScatterPoints",
                "NumberOfDataScatterPointsRgb",
            ) if hasattr(result, name)
        },
        "messages": [str(result.GetMessageAt(i).Text) for i in range(int(result.NumberOfMessages))],
        "series": [],
        "grids": [],
    }
    for i in range(data["counts"].get("NumberOfDataSeries", 0)):
        series = unwrap(result.GetDataSeries(i))
        data["series"].append({
            "description": str(series.Description),
            "labels": None if series.SeriesLabels is None else [str(v) for v in series.SeriesLabels],
            "x_null": series.XData is None,
            "y_null": series.YData is None,
        })
    for i in range(data["counts"].get("NumberOfDataGrids", 0)):
        grid = unwrap(result.GetDataGrid(i))
        data["grids"].append({
            "type": str(grid.GetType().FullName), "nx": int(grid.Nx), "ny": int(grid.Ny),
            "name": str(grid.Name), "description": str(grid.Description),
            "values_null": grid.Values is None,
        })
    data["text_export"] = bool(result.GetTextFile(str(output)))
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--analysis",choices=["SourceColorChart1931","SourceColorChart1976"],default="SourceColorChart1931")
    parser.add_argument("--output",type=Path,default=ROOT/".local/evidence/development/CV-01/source-color-sequential-1931-20261108")
    args=parser.parse_args()
    output=args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    record = {"items": []}
    try:
        record["connect"] = backend.dispatch("connect", {})
        assert record["connect"]["ok"]
        source=Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        record["input"]=str(source)
        record["open_lens"]=backend.dispatch("open_lens",{"path":str(source)})
        assert record["open_lens"]["ok"]
        record["context"]=backend.context()
        for name in (args.analysis,):
            item = {"kind": name}
            record["items"].append(item)
            tool = None
            handed = False
            try:
                tool = new_analysis(backend, name)
                if tool is None:
                    item["factory"] = "null"
                    continue
                item["settings"] = scalar_settings(unwrap(tool.GetSettings()))

                tool.ApplyAndWaitForCompletion()
                item["result"] = describe_result(tool.GetResults(), output / f"{name}.txt", backend, {"native": tool})
                item["task_state"] = "completed"
            except Exception as exc:
                item["error"] = {"type": type(exc).__name__, "message": str(exc)}
            finally:
                if tool is not None:
                    item["close"] = backend._close_task_native({"native": tool})
        record["disconnect"] = backend.dispatch("disconnect", {})
    finally:
        (output / "summary.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "closed": record.get("disconnect", {}).get("ok"), "items": [{"kind": x["kind"], "factory": x.get("factory"), "counts": x.get("result", {}).get("counts"), "state": x.get("task_state"), "error": x.get("error")} for x in record["items"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
