import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Inspect the formal RayData/RGB outlets omitted by prior FullFieldSpot diagnostics."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import checked,check,select
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.spot_topics import configure


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='FullFieldSpot may expose formal RayData or RGB series even when text/SpotData/scatter counts are empty',cases=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record.setdefault('calls',[]).append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['before']=call('get_surfaces');record['settings']=call('get_system_settings');record['merit']=call('get_merit_function')
        for reference,symbols,exaggerate in [('Centroid',False,1),('ChiefRay',False,3),('Middle',True,1)]:
            q=RunAnalysis(request=dict(kind='full_field_spot',reference=reference,use_symbols=symbols,exaggerate=exaggerate)).request
            item=dict(request=q.model_dump());record['cases'].append(item);tool=None
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'FullFieldSpot'))
                s=unwrap(tool.GetSettings());surface=int(b.system.LDE.NumberOfSurfaces)-1
                for name,value in [('Field',q.field),('Wavelength',q.wavelength),('Surface',surface)]:select(getattr(s,name),name,value)
                values=configure(q,int(b.system.MCE.CurrentConfiguration),lambda k,v:checked(b.native,s,k,v))
                for k,v in values.items():check(b.native,s,k,v)
                from zemax_mcp.analyses import scalar_settings
                item['actual_settings']=scalar_settings(s);save()
                tool.ApplyAndWaitForCompletion();r=unwrap(tool.GetResults())
                item['result_type']=str(r.GetType().FullName)
                item['counts']={p.Name:int(getattr(r,p.Name))for p in r.GetType().GetProperties()if p.Name.startswith('NumberOf')}
                item['header']=[str(v)for v in r.HeaderData.Lines]
                item['spot_data']=r.SpotData is not None
                item['public_methods']=[str(m)for m in r.GetType().GetMethods()if m.IsPublic and not m.IsSpecialName]
                item['ray_data']=[]
                for i in range(int(r.NumberOfRayData)):
                    d=unwrap(r.GetRayData(i));sample=[]
                    for j in range(min(int(d.NumRays),10)):
                        ray=unwrap(d.GetRay(j));entry={}
                        for p in ray.GetType().GetProperties():
                            if not p.GetIndexParameters().Length:
                                try:entry[p.Name]=str(getattr(ray,p.Name))
                                except Exception as exc:entry[p.Name]=dict(error=str(exc))
                        sample.append(entry)
                    item['ray_data'].append(dict(index=i,description=str(d.Description),num_rays=int(d.NumRays),sample=sample))
                item['native_text_exported']=bool(r.GetTextFile(str(folder/(reference+'.txt'))))
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc));raise
            finally:
                if tool is not None:item['closed']=b._close_task_native(dict(native=tool))
                save()
        record['after']=call('get_surfaces');record['settings_after']=call('get_system_settings');record['merit_after']=call('get_merit_function')
    finally:
        record['disconnect']=b.dispatch('disconnect',{});save()


if __name__=='__main__':run(sys.argv[1])
