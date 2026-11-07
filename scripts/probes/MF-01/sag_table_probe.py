import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Formal SagTable result outlets and read-only sag operand parameter probe."""
import json,sys
from pathlib import Path
ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder,case="parabola"):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(analyses=[],operands=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect');call('new_system')
        shape=dict(parabola=dict(radius=40,conic=-1,parameters={'1':.0001}),
            concave=dict(radius=-40,conic=-1,parameters={'1':-.0001}),
            sphere=dict(radius=40,conic=0,parameters={'1':0}),
            plane=dict(radius='Infinity',conic=0,parameters={'1':0}))[case]
        record['case']=case
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',
            semi_diameter=5,thickness=20,replace_solves=True)|shape]))
        record['baseline']=call('get_surfaces');record['merit_before']=call('get_merit_function')
        for name in ['SagTable','SurfaceSag','SurfaceSlopeCross']:
            tool=None;item=dict(native_id=name);record['analyses'].append(item)
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,name))
                settings=unwrap(tool.GetSettings());item['settings_type']=str(settings.GetType().FullName)
                if name!='SagTable':
                    settings.Surface.SetSurfaceNumber(1)
                    if name=='SurfaceSlopeCross':
                        settings.RemoveOption=b.native.enum(settings.GetType().GetProperty('RemoveOption').PropertyType,'BestFitSphere')
                tool.ApplyAndWaitForCompletion();result=tool.GetResults()
                item['arrays']={key:int(getattr(result,key)) for key in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataSeriesRgb','NumberOfDataGridsRgb','NumberOfMessages']}
                item['messages']=[str(result.GetMessageAt(i).Text) for i in range(result.NumberOfMessages)]
                text=folder/(name+'.txt');item['text_exported']=bool(result.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')[:9000]
                item['methods']=[str(m)for m in result.GetType().GetMethods() if m.IsPublic and not m.IsSpecialName]
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:item['closed']=b._close_task_native(dict(native=tool))
                save()
        record['sag_samples']=[dict(y=y,result=list(b.system.LDE.GetSag(1,0,y)))for y in [0,1,3,5]]
        names=set(b.native.enum_names(b.native.api.Editors.MFE.MeritOperandType))
        for name in ['SSAG','SSLP','BFSR','BFSD','BFSX','BFSY']:
            item=dict(name=name,available=name in names);record['operands'].append(item)
            if name not in names:continue
            enum=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name)
            count=int(b.system.MFE.NumberOfOperands);operand=b.system.MFE.AddOperand()
            try:
                operand.ChangeType(enum);item['headers']=[]
                for number in range(1,9):
                    cell=operand.GetOperandCell(b.native.enum(b.native.api.Editors.MFE.MeritColumn,'Param'+str(number)))
                    item['headers'].append(dict(number=number,header=str(cell.Header),type=str(cell.DataType),active=bool(cell.IsActive)))
            finally:b.system.MFE.RemoveOperandAt(count+1)
            save()
        record['bfs_queries']=[]
        for data in range(8):
            args=[1,data,0.,0.,0.,0.,0.,0.]
            value=float(b.system.MFE.GetOperandValue(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,'BFSD'),*args))
            record['bfs_queries'].append(dict(data=data,arguments=args,value=value))
        record['slope_queries']=[]
        for y in [0,1,3,5]:
            args=[1,1,0.,float(y),0.,0.,0.,3.]
            value=float(b.system.MFE.GetOperandValue(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,'SSLP'),*args))
            record['slope_queries'].append(dict(y=y,value=value))
        record['surfaces_after']=call('get_surfaces');record['merit_after']=call('get_merit_function')
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(analyses=record['analyses'],operands=record['operands']),ensure_ascii=False)[:1800])
if __name__=='__main__':run(*sys.argv[1:])
