"""Read actual best-fit settings and exported report for all native criteria."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));r=dict(cases=[])
    def save():(folder/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r['stage']='enter '+name;save();v=b.dispatch(name,args or {});assert v['ok'],v;return v['data']
    try:
        r['connect']=call('connect');call('new_system')
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=40,conic=-1,parameters={'1':.0001},semi_diameter=5,replace_solves=True)]))
        r['before']=call('get_surfaces');r['settings_before']=call('get_system_settings')
        for criterion,reverse in [('MinimumVolume',False),('MinimumRMS',False),('MinimumRMSWithOffset',False),('MinimumVolume',True)]:
            tool=None;item=dict(criterion=criterion,reverse=reverse);r['cases'].append(item)
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'SurfaceSlopeCross'))
                s=unwrap(tool.GetSettings());s.Surface.SetSurfaceNumber(1)
                s.RemoveOption=b.native.enum(s.GetType().GetProperty('RemoveOption').PropertyType,'BestFitSphere')
                s.BestFitSphereOption=b.native.enum(s.GetType().GetProperty('BestFitSphereOption').PropertyType,criterion)
                if criterion=='MinimumVolume':s.ReverseDirection=reverse
                s.Angle=90
                item['actual']=dict(surface=s.Surface.GetSurfaceNumber(),criterion=str(s.BestFitSphereOption),criterion_value=int(s.BestFitSphereOption),reverse=bool(s.ReverseDirection),angle=float(s.Angle))
                r['stage']='Apply '+criterion+' '+str(reverse);save()
                tool.ApplyAndWaitForCompletion();result=tool.GetResults()
                text=folder/(criterion+str(reverse)+'.txt');item['text_exported']=bool(result.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')[:2200]
                item['header_properties']=[dict(name=p.Name,type=str(p.PropertyType))for p in result.HeaderData.GetType().GetProperties()]
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:item['closed']=b._close_task_native(dict(native=tool))
                save()
        r['after']=call('get_surfaces');r['settings_after']=call('get_system_settings')
    finally:r['disconnect']=b.dispatch('disconnect',{});r['stage']='closed';save()
    print(json.dumps(r['cases'],ensure_ascii=False)[:1800])
if __name__=='__main__':run(sys.argv[1])
