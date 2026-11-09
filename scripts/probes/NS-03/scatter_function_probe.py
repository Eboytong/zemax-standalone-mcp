import json
import sys
import argparse
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from zemax_mcp.analyses import scalar_settings
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import dotnet_array, unwrap
from zemax_mcp.imaging import new_analysis


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--analysis',default='ScatterFunctionViewer',choices=['ScatterFunctionViewer','ScatterPolarPlotSettings'])
    parser.add_argument('--output-name',default=None)
    parser.add_argument('--activate-abg',action='store_true')
    args=parser.parse_args()
    output = ROOT / ".local/evidence/development/NS-03" / (args.output_name or args.analysis.lower()+'-20261108')
    output.mkdir(parents=True, exist_ok=False)
    source = Path.home() / "Documents/Zemax/Samples/Non-sequential/Scattering/ABg scattering surface.zos"
    backend = Backend(Config(Config.from_env().install_dir, output / "native"))
    record = {"analysis": args.analysis, "input": str(source)}
    tool = None
    try:
        record["connect"] = backend.dispatch("connect", {})
        assert record["connect"]["ok"]
        record["open_lens"] = backend.dispatch("open_lens", {"path": str(source)})
        if not record["open_lens"]["ok"]:
            raise RuntimeError(record["open_lens"])
        record["context"] = backend.context()
        record["system_settings"] = backend.dispatch("get_system_settings",{})
        record["objects"] = backend.dispatch("get_nsc_objects", {"start": 1, "count": 20})
        if args.activate_abg:
            record["abg_update"] = backend.dispatch("update_nsc_objects",{"changes":[{"object":2,"faces":[{"face":0,"scatter_model":"ABg","settings":{"ScatterFraction":1.0}}]}]})
            record["objects_after_update"] = backend.dispatch("get_nsc_objects",{"start":2,"count":1})
        tool = new_analysis(backend, args.analysis)
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
            "text_export": bool(result.GetTextFile(str(output / (args.analysis+'.txt')))),
        }
        record["result"]["grids"]=[]
        for i in range(int(result.NumberOfDataGrids)):
            grid=unwrap(result.GetDataGrid(i));values=dotnet_array(grid.Values)
            record["result"]["grids"].append({
                "type":str(grid.GetType().FullName),
                "properties":[{"name":p.Name,"type":str(p.PropertyType)} for p in grid.GetType().GetProperties()],
                "description":str(grid.Description),"nx":int(grid.Nx),"ny":int(grid.Ny),
                "x_label":str(grid.XLabel),"y_label":str(grid.YLabel),"value_label":str(grid.ValueLabel),
                "dx":float(grid.Dx),"dy":float(grid.Dy),"min_x":float(grid.MinX),"min_y":float(grid.MinY),
                "values":values,
            })
        if args.analysis=='ScatterPolarPlotSettings':
            baseline=record['result']['grids'][0]['values']
            record['baseline_grid_summary']={"min":min(min(r)for r in baseline),"max":max(max(r)for r in baseline),"sample":baseline[len(baseline)//2][len(baseline[0])//2]}
            record['control_update']=backend.dispatch('update_nsc_objects',{'changes':[{'object':2,'faces':[{'face':0,'scatter_model':'Lambertian','settings':{'ScatterFraction':1.0}}]}]})
            if record['control_update']['ok']:
                control=new_analysis(backend,args.analysis)
                try:
                    record['control_settings']=scalar_settings(unwrap(control.GetSettings()))
                    control.ApplyAndWaitForCompletion()
                    control_result=unwrap(control.GetResults());g=unwrap(control_result.GetDataGrid(0));vals=dotnet_array(g.Values)
                    record['lambertian_control']={"valid":bool(control_result.IsValid),"nx":int(g.Nx),"ny":int(g.Ny),"description":str(g.Description),"x_label":str(g.XLabel),"y_label":str(g.YLabel),"value_label":str(g.ValueLabel),"dx":float(g.Dx),"dy":float(g.Dy),"min_x":float(g.MinX),"min_y":float(g.MinY),"min":min(min(r)for r in vals),"max":max(max(r)for r in vals),"sample":vals[len(vals)//2][len(vals[0])//2]}
                finally:
                    record['control_close']=backend._close_task_native({'native':control})
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
