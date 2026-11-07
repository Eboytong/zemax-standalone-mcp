import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Public runtime settings/results for remaining first-order ray diagrams."""
import json,sys
from pathlib import Path
ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap,dotnet_array

def run(folder,case="cooke"):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(analyses=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect')
        record['case']=case
        if case=='cooke':call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        elif case=='mirror':
            call('new_system')
            call('update_system_settings',dict(aperture_value=10,fields=[dict(x=0,y=0),dict(x=0,y=2)],wavelengths=[dict(wavelength_um=.55)]))
            call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,material='MIRROR',thickness=-100,semi_diameter=10,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=20,replace_solves=True)]))
        elif case in ('image_glass','image_power','image_power_glass'):
            call('new_system')
            call('update_system_settings',dict(aperture_value=10,fields=[dict(x=0,y=0),dict(x=0,y=10)],wavelengths=[dict(wavelength_um=.55)]))
            call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)|(dict(material='N-BK7')if case=='image_glass'else dict(surface_type='Paraxial',parameters={'1':10},material='N-BK7'if case=='image_power_glass'else''))]))
        elif case in ('fields_mixed','fields_negative','finite_object'):
            call('new_system')
            fields=[dict(x=40,y=0),dict(x=0,y=20)]if case=='fields_mixed'else[dict(x=0,y=0),dict(x=0,y=-20 if case=='fields_negative'else 20)]
            call('update_system_settings',dict(aperture_value=10,fields=fields,wavelengths=[dict(wavelength_um=.55)],field_type='ObjectHeight'if case=='finite_object'else'Angle'))
            changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]
            if case=='finite_object':changes.insert(0,dict(surface=0,thickness=100,replace_solves=True))
            call('update_surfaces',dict(changes=changes))
        else:raise ValueError(case)
        record['baseline']=call('get_surfaces');record['settings_before']=call('get_system_settings')
        for name in ['YYbarDiagram','IncidentAnglevsImageHeight']:
            tool=None;item=dict(native_id=name);record['analyses'].append(item)
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,name))
                settings=unwrap(tool.GetSettings());item['settings_type']=str(settings.GetType().FullName)
                item['properties']=[dict(name=p.Name,type=str(p.PropertyType),writable=bool(p.CanWrite))for p in settings.GetType().GetProperties()]
                tool.ApplyAndWaitForCompletion();result=tool.GetResults()
                item['arrays']={key:int(getattr(result,key)) for key in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataSeriesRgb','NumberOfDataGridsRgb','NumberOfMessages']}
                item['messages']=[str(result.GetMessageAt(i).Text)for i in range(result.NumberOfMessages)]
                item['series']=[]
                for i in range(result.NumberOfDataSeries):
                    data=result.GetDataSeries(i)
                    item['series'].append(dict(description=str(data.Description),labels=[str(x)for x in data.SeriesLabels],x=dotnet_array(data.XData.Data),y=dotnet_array(data.YData.Data)))
                text=folder/(name+'.txt');item['text_exported']=bool(result.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')[:8500]
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:item['closed']=b._close_task_native(dict(native=tool))
                save()
        record['operands']=[];record['merit_before']=call('get_merit_function')
        image=int(b.system.LDE.NumberOfSurfaces)-1
        primary=next(w['number']for w in record['settings_before']['wavelengths']if w['primary'])
        names=set(b.native.enum_names(b.native.api.Editors.MFE.MeritOperandType))
        for name in ['PARY','PARX','REAY','RAGB','RAGC','INDX']:
            item=dict(name=name,available=name in names,queries=[]);record['operands'].append(item)
            if name not in names:continue
            enum=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name)
            count=int(b.system.MFE.NumberOfOperands);operand=b.system.MFE.AddOperand()
            try:
                operand.ChangeType(enum);item['headers']=[]
                for number in range(1,9):
                    cell=operand.GetOperandCell(b.native.enum(b.native.api.Editors.MFE.MeritColumn,'Param'+str(number)))
                    item['headers'].append(dict(number=number,header=str(cell.Header),type=str(cell.DataType),active=bool(cell.IsActive)))
            finally:b.system.MFE.RemoveOperandAt(count+1)
            for surface in (sorted(set([1,2,image])) if name.startswith('PAR') or name=='INDX' else [image]):
              for hy,py in [(1,0),(0,1),(0,-1),(.5,0)]:
                args=[surface,primary,0.,hy,0.,py,0.,0.]
                try:item['queries'].append(dict(arguments=args,value=float(b.system.MFE.GetOperandValue(enum,*args))))
                except Exception as exc:item['queries'].append(dict(arguments=args,error=str(exc)))
            save()
        record['merit_after']=call('get_merit_function')
        record['surfaces_after']=call('get_surfaces');record['settings_after']=call('get_system_settings')
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(record['analyses'],ensure_ascii=False)[:2500])
if __name__=='__main__':run(*sys.argv[1:])
