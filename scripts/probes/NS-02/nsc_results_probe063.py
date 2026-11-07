import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Compare official generic/named analysis factories and result exports."""
import json
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.nsc_analyses import SINGLE
from zemax_mcp.path_models import NscSingleRayTrace
from zemax_mcp.imaging import checked
from zemax_mcp.nsc_analyses import read_segment

ROOT=PROJECT_ROOT
folder=ROOT/'verification/development/NS-02/probe063'
folder.mkdir(parents=True,exist_ok=True)
config=Config.from_env()
b=Backend(Config(config.install_dir,folder/'runs'))
records=[]
try:
    calls=json.loads((ROOT/'.local/fixtures/paths027_single_ab9ab38925/calls.json').read_text(encoding='utf-8'))
    for call in calls:
        if call['tool']=='run_analysis':break
        args=call['arguments']or{}
        response=b.dispatch(call['tool'],args.get('request',args.get('settings',args)))
        assert response['ok'],response
    for factory,settings_mode,execution in [('New_Analysis_SettingsFirst','requested','sync'),('New_Analysis_SettingsFirst','requested','async'),('New_NSCSingleRayTrace','defaults','sync')]:
        a=(getattr(b.system.Analyses,factory)(b.native.enum(b.native.api.Analysis.AnalysisIDM,'NSCSingleRayTrace'))
           if factory=='New_Analysis_SettingsFirst'else b.system.Analyses.New_NSCSingleRayTrace())
        label=factory+'_'+settings_mode+'_'+execution
        record=dict(factory=factory,settings_mode=settings_mode,execution=execution)
        records.append(record)
        try:
            s=unwrap(a.GetSettings())
            if settings_mode=='requested':
                q=NscSingleRayTrace(kind='nsc_single_ray_trace')
                s.Wavelength.SetWavelengthNumber(q.wavelength)
                for key,name in SINGLE.items():checked(b.native,s,name,getattr(q,key))
            s.SaveRaysFile=label+'.zrd'
            if execution=='sync':a.ApplyAndWaitForCompletion()
            else:
                import time
                a.Apply()
                record['initial_running']=bool(a.IsRunning())
                a.WaitForCompletion()
            r=unwrap(a.GetResults())
            record.update(valid=bool(r.IsValid),type=str(r.GetType().FullName),
                          single_data_present=r.NSCSingleRayTraceData is not None,
                          messages=[str(r.GetMessageAt(i).Text)for i in range(r.NumberOfMessages)])
            data=unwrap(r.NSCSingleRayTraceData)
            if data is not None:
                record['data_valid']=bool(data.IsValid)
                record['segment_count']=int(data.NumberOfSegments)
                record['indices']=[dict(index=i,result=[str(v) for v in read_segment(data,i,b.native)])for i in range(int(data.NumberOfSegments)+1)]
            record['text_export']=bool(r.GetTextFile(str(folder/(label+'.txt'))))
            record['properties']={}
            for p in r.GetType().GetProperties():
                try:
                    value=p.GetValue(r)
                    record['properties'][str(p.Name)]=None if value is None else str(value)
                except Exception as exc:record['properties'][str(p.Name)]={'error':str(exc)}
        except Exception as exc:record['error']=str(exc)
        finally:
            owner={'native':a}
            record['close']=b._close_task_native(owner)
    for mode in ['absolute','filename']:
        source=ROOT/'.local/fixtures/paths027_critical_ee6c031b07/controlled.CRS'
        import shutil
        staged=Path(str(b.system.SystemFile)).parent/'controlled.CRS'
        shutil.copyfile(source,staged)
        b.system.UpdateFileLists()
        a=b.system.Analyses.New_CriticalRayTracer()
        record=dict(kind='critical',mode=mode)
        records.append(record)
        try:
            s=unwrap(a.GetSettings());s.Filename=str(staged)if mode=='absolute'else staged.name
            a.ApplyAndWaitForCompletion()
            r=unwrap(a.GetResults())
            record.update(valid=bool(r.IsValid),data_present=r.CriticalRayData is not None,
                          text_export=bool(r.GetTextFile(str(folder/('critical_'+mode+'.txt')))),
                          messages=[str(r.GetMessageAt(i).Text)for i in range(r.NumberOfMessages)])
        except Exception as exc:record['error']=str(exc)
        finally:record['close']=b._close_task_native({'native':a})
finally:
    response=b.dispatch('disconnect',{})
    (folder/'results.json').write_text(json.dumps(dict(records=records,disconnect=response),ensure_ascii=False,indent=2),encoding='utf-8')
