import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Test formal CFG transfer from typed surface settings, with text adoption checks."""
import json,sys
from pathlib import Path
ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(cases=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_surfaces',dict(changes=[dict(surface=1,radius=40,semi_diameter=5,replace_solves=True),
            dict(surface=2,surface_type='EvenAspheric',radius=20,conic=-1,parameters={'1':.0003},semi_diameter=3,replace_solves=True)]))
        for criterion in ['MinimumVolume','MinimumRMS','MinimumRMSWithOffset']:
            donor=target=None;item=dict(criterion=criterion,surface=2);record['cases'].append(item)
            try:
                donor=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'SurfaceSlopeCross'))
                settings=unwrap(donor.GetSettings());settings.Surface.SetSurfaceNumber(2)
                settings.RemoveOption=b.native.enum(settings.GetType().GetProperty('RemoveOption').PropertyType,'BestFitSphere')
                settings.BestFitSphereOption=b.native.enum(settings.GetType().GetProperty('BestFitSphereOption').PropertyType,criterion)
                item['donor_readback']=dict(surface=settings.Surface.GetSurfaceNumber(),criterion=str(settings.BestFitSphereOption))
                cfg=folder/(criterion+'.CFG');item['saved']=bool(settings.SaveTo(str(cfg)))
                target=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'SagTable'))
                item['loaded']=bool(target.GetSettings().LoadFrom(str(cfg)))
                target.ApplyAndWaitForCompletion();r=target.GetResults();text=folder/(criterion+'.txt')
                item['text_exported']=bool(r.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')[:1800]
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                for key,obj in [('donor_closed',donor),('target_closed',target)]:
                    if obj is not None:item[key]=b._close_task_native(dict(native=obj))
                save()
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(record['cases'],ensure_ascii=False)[:1600])
if __name__=='__main__':run(sys.argv[1])
