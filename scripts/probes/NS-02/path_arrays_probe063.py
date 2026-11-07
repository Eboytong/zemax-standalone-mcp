import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Capture native repeated-object and uncategorized path dimensions."""
import json
from pathlib import Path
import shutil
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap,dotnet_array

ROOT=PROJECT_ROOT
folder=ROOT/'verification/development/NS-02/path-arrays063';folder.mkdir(parents=True,exist_ok=True)
config=Config.from_env();b=Backend(Config(config.install_dir,folder/'runs'));records=[]
try:
    calls=json.loads((ROOT/'.local/fixtures/paths063_uncategorized_dae7fb3286/calls.json').read_text(encoding='utf-8'))
    for call in calls:
        if call['tool']=='run_nsc_ray_trace':break
        args=call['arguments']or{}
        response=b.dispatch(call['tool'],args.get('request',args.get('settings',args)))
        assert response['ok'],response
    staged=Path(str(b.system.SystemFile)).parent/'loss.zrd'
    shutil.copyfile(ROOT/'.local/fixtures/paths063_uncategorized_dae7fb3286/loss.zrd',staged)
    b.system.UpdateFileLists()
    for threshold in [0,1]:
        a=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'PathAnalysis'))
        record=dict(threshold=threshold);records.append(record)
        try:
            s=unwrap(a.GetSettings());s.RayDatabaseFile=staged.name;s.RelativeMinimumFlux=threshold
            a.ApplyAndWaitForCompletion();r=unwrap(a.GetResults());d=unwrap(r.PathAnalysisData)
            entries=list(d.Paths)
            try:entries.append(d.GetPathUncategorized())
            except Exception as exc:record['uncategorized_error']=str(exc)
            record['entries']=[]
            for raw in entries:
                e=unwrap(raw)
                item=dict(path_number=int(e.PathNumber),object_count=int(e.NumberOfObjectsInPath),unique_objects=int(e.UniqueObjectsInPath),objects=[int(v)for v in e.PathObjectList],
                          matrix=dotnet_array(e.PathObjectAndFaceList),flux=float(e.TotalPathFlux))
                if item['path_number']:
                    d.PathNumber=item['path_number'];item['sequence']=str(d.PathSequence)
                record['entries'].append(item)
            record['num_paths']=int(d.NumPaths)
            record['alternate_lookups']=[]
            for number in [0,4294967295]:
                try:
                    entry=unwrap(d.GetPathNumber(number))
                    record['alternate_lookups'].append(dict(number=number,present=entry is not None,
                        path_number=int(entry.PathNumber)if entry is not None else None))
                except Exception as exc:record['alternate_lookups'].append(dict(number=number,error=str(exc)))
            record['text_export']=bool(r.GetTextFile(str(folder/('threshold'+str(threshold)+'.txt'))))
        except Exception as exc:record['error']=str(exc)
        finally:record['closed']=b._close_task_native({'native':a})
finally:
    response=b.dispatch('disconnect',{})
    (folder/'summary.json').write_text(json.dumps(dict(records=records,disconnect=response),ensure_ascii=False,indent=2),encoding='utf-8')
