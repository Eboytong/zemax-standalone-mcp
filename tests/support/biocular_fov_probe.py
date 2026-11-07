"""Formal FOV result outlets with stage logging and bounded asynchronous Apply."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));r={};tool=None
    def save():(folder/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r['stage']='enter '+name;save();v=b.dispatch(name,args or {});assert v['ok'],v;r['stage']='return '+name;save();return v['data']
    try:
        r['connect']=call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_surfaces',dict(changes=[dict(surface=1,thickness=50,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,thickness=50,semi_diameter=100,aperture=dict(type='CircularAperture',maximum_radius=10),replace_solves=True),dict(surface=3,semi_diameter=100,replace_solves=True)]))
        call('update_configurations',dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=50),dict(configuration=2,value=100)])]))
        tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'BiocularFieldOfViewAnalysis'))
        s=unwrap(tool.GetSettings());r['settings_type']=str(s.GetType().FullName)
        r['settings_methods']=[str(m)for m in s.GetType().GetMethods()if m.IsPublic and not m.IsSpecialName]
        r['stage']='Apply';save();tool.Apply();deadline=time.monotonic()+20
        while tool.IsRunning():
            if time.monotonic()>deadline:
                r['timeout']=True;tool.Terminate();break
            time.sleep(.05)
        r['stage']='results';save();result=tool.GetResults()
        r['counts']={k:int(getattr(result,k))for k in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataSeriesRgb','NumberOfDataGridsRgb','NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb','NumberOfRayData','NumberOfMessages']}
        r['scatter_outlets']=[]
        for i in range(result.NumberOfDataScatterPoints):
            data=result.GetDataScatterPoint(i)
            r['scatter_outlets'].append(dict(index=i,type=str(data.GetType().FullName),properties=[dict(name=p.Name,type=str(p.PropertyType))for p in data.GetType().GetProperties()],methods=[str(m)for m in data.GetType().GetMethods()if m.IsPublic and not m.IsSpecialName]))
        r['result_methods']=[str(m)for m in result.GetType().GetMethods()if m.IsPublic and not m.IsSpecialName]
        r['messages']=[str(result.GetMessageAt(i).Text)for i in range(result.NumberOfMessages)]
        r['text_exported']=bool(result.GetTextFile(str(folder/'fov.txt')))
        r['result_properties']=[dict(name=p.Name,type=str(p.PropertyType))for p in result.GetType().GetProperties()]
    finally:
        if tool is not None:r['analysis_closed']=b._close_task_native(dict(native=tool))
        r['disconnect']=b.dispatch('disconnect',{});r['stage']='closed';save()
    print(json.dumps(r,ensure_ascii=False)[:1800])
if __name__=='__main__':run(sys.argv[1])
