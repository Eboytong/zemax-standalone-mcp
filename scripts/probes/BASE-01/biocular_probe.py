import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Formal Gaussian MFE query parameters, independent of AS_Default dialogs."""
import json
import sys
from pathlib import Path

ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(folder,mode="all"):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(operands=[],analyses=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        record['stage']='enter '+name;save()
        r=b.dispatch(name,args or {});record['stage']='return '+name;save();assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect');call('new_system')
        call('update_system_settings',dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)]))
        call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=5,replace_solves=True)]))
        call('update_configurations',dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=100),dict(configuration=2,value=120)])]))
        from zemax_mcp.data import unwrap
        for name in ([]if mode=='clipping_only'else['BiocularDipvergenceConvergence','BiocularFieldOfViewAnalysis']):
            tool=None;item=dict(native_id=name);record['analyses'].append(item)
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,name))
                settings=unwrap(tool.GetSettings());item['settings_type']=str(settings.GetType().FullName)
                item['properties']=[dict(name=p.Name,type=str(p.PropertyType),writable=bool(p.CanWrite))for p in settings.GetType().GetProperties()]
                record['stage']='Apply '+name;save()
                tool.ApplyAndWaitForCompletion();r=tool.GetResults()
                item['counts']={k:int(getattr(r,k))for k in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfMessages']}
                text=folder/(name+'.txt');item['text_exported']=bool(r.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')[:12000]
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:item['closed']=b._close_task_native(dict(native=tool))
                save()
        names=set(b.native.enum_names(b.native.api.Editors.MFE.MeritOperandType))
        record['merit_before']=call('get_merit_function')
        for name in ['BIOC','BIOD']:
            item=dict(name=name,available=name in names);record['operands'].append(item)
            if name not in names:continue
            enum=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name)
            count=int(b.system.MFE.NumberOfOperands);operand=b.system.MFE.AddOperand()
            try:
                operand.ChangeType(enum);headers=[]
                for number in range(1,9):
                    column=b.native.enum(b.native.api.Editors.MFE.MeritColumn,'Param'+str(number))
                    cell=operand.GetOperandCell(column)
                    headers.append(dict(number=number,header=str(cell.Header),type=str(cell.DataType),active=bool(cell.IsActive)))
                item['headers']=headers
            finally:b.system.MFE.RemoveOperandAt(count+1)
            item['queries']=[]
            for x,y in [(0,0),(10,0),(0,10),(-10,5)]:
                parameters=[1,2,1.,0.,float(x),float(y),0.,0.]
                try:item['queries'].append(dict(arguments=parameters,value=float(b.system.MFE.GetOperandValue(enum,*parameters))))
                except Exception as exc:item['queries'].append(dict(arguments=parameters,error=dict(type=type(exc).__name__,message=str(exc))))
            save()
        call('update_surfaces',dict(changes=[dict(surface=2,aperture=dict(type='CircularAperture',maximum_radius=.01))]))
        record['clipped_queries']=[]
        for name in ['BIOC','BIOD']:
            item=dict(operand=name);record['clipped_queries'].append(item)
            record['stage']='clipped query '+name;save()
            try:item['value']=float(b.system.MFE.GetOperandValue(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name),1,2,1.,0.,10.,0.,0.,0.))
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
        record['mfe_properties']=[dict(name=p.Name,type=str(p.PropertyType))for p in b.system.MFE.GetType().GetProperties()]
        record['merit_after']=call('get_merit_function')
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(operands=record['operands'],analyses=record['analyses'],closed=record['disconnect']['ok']),ensure_ascii=False)[:2500])


if __name__=='__main__':run(*sys.argv[1:])
