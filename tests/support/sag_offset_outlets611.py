"""Inspect sag-specific result metadata for physical BFS offset and summaries."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.imaging import checked,check,select

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='Sag rather than slope report may preserve manufacturing vertex offset or fitted-sphere metadata',cases=[],calls=[])
    def save():(folder/'outlets.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        response=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=response));save();assert response['ok'],response;return response['data']
    try:
        call('connect');call('new_system')
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=40,conic=-1,parameters={'1':.0001},semi_diameter=5,thickness=20,replace_solves=True)]))
        record['before']=call('get_surfaces');record['settings']=call('get_system_settings');record['merit']=call('get_merit_function')
        for topic in ['SurfaceSag','SurfaceSagCross']:
            for criterion,reverse in [('MinimumRMS',False),('MinimumRMSWithOffset',False),('MinimumVolume',True)]:
                tool=None;case=dict(topic=topic,criterion=criterion,reverse=reverse);record['cases'].append(case)
                try:
                    tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,topic))
                    settings=unwrap(tool.GetSettings());select(settings.Surface,'Surface',1)
                    values=dict(RemoveOption='BestFitSphere',BestFitSphereOption=criterion,ConsiderOffAxisAperture=False)
                    if criterion=='MinimumVolume':values['ReverseDirection']=reverse
                    if topic.endswith('Cross'):values.update(Angle=90.,Sampling='S_65')
                    else:values.update(Sampling='S_65x65')
                    for key,value in values.items():checked(b.native,settings,key,value)
                    for key,value in values.items():check(b.native,settings,key,value)
                    case['actual_settings']={key:str(getattr(settings,key))for key in values};case['surface']=settings.Surface.GetSurfaceNumber()
                    save();tool.ApplyAndWaitForCompletion();result=unwrap(tool.GetResults())
                    case['result_type']=str(result.GetType().FullName)
                    case['properties']=[dict(name=p.Name,type=str(p.PropertyType))for p in result.GetType().GetProperties()]
                    case['methods']=[str(m)for m in result.GetType().GetMethods()if m.DeclaringType==result.GetType()and not m.IsSpecialName]
                    case['counts']={p.Name:int(getattr(result,p.Name))for p in result.GetType().GetProperties()if p.Name.startswith('NumberOf')}
                    header=unwrap(result.HeaderData)
                    case['header']=[str(line)for line in header.Lines]if header.Lines is not None else[]
                    text=folder/(topic+'-'+criterion+str(reverse)+'.txt');case['text_exported']=bool(result.GetTextFile(str(text)))
                    if text.is_file():case['text']=text.read_text(encoding='utf-16')
                    case['grids']=[];case['series']=[]
                    for i in range(int(result.NumberOfDataGrids)):
                        grid=unwrap(result.GetDataGrid(i));case['grids'].append(dict(nx=int(grid.Nx),ny=int(grid.Ny),description=str(grid.Description),center=float(grid.Values[int(grid.Ny)//2,int(grid.Nx)//2]),properties=[dict(name=p.Name,type=str(p.PropertyType))for p in grid.GetType().GetProperties()]))
                    for i in range(int(result.NumberOfDataSeries)):
                        series=unwrap(result.GetDataSeries(i));case['series'].append(dict(description=str(series.Description),properties=[dict(name=p.Name,type=str(p.PropertyType))for p in series.GetType().GetProperties()]))
                except BaseException as exc:
                    case['error']=dict(type=type(exc).__name__,message=str(exc));save();raise
                finally:
                    if tool is not None:case['closed']=b._close_task_native(dict(native=tool))
                    save()
        record['after']=call('get_surfaces');record['settings_after']=call('get_system_settings');record['merit_after']=call('get_merit_function')
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps([dict(topic=c['topic'],criterion=c['criterion'],counts=c.get('counts'),header=c.get('header'),grids=[dict(center=g['center'])for g in c.get('grids',[])],closed=c.get('closed'))for c in record['cases']],ensure_ascii=False))

if __name__=='__main__':run(sys.argv[1])
