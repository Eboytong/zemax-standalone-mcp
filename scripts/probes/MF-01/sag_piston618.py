import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Separate native BFS offset signs with an explicitly displaced sag vertex."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(conditions='z=.0126*r²+piston, semi5mm; no reference fitted to native offsets',cases=[],calls=[])
    def save():(folder/'piston.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('new_system')
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='ZernikeFringeSag',radius=40,conic=-1,semi_diameter=5,thickness=20,parameters={'13':1},replace_solves=True)]))
        for piston in [0.,.003,-.003]:
            call('update_surfaces',dict(changes=[dict(surface=1,parameters={'1':.0001,'14':5,'15':piston},replace_solves=True)]))
            before=call('get_surfaces');settings=call('get_system_settings');merit=call('get_merit_function')
            case=dict(piston=piston,sag=[dict(y=y,result=list(b.system.LDE.GetSag(1,0.,y)))for y in [0.,2.5,5.]],queries=[])
            record['cases'].append(case);save()
            for name,arguments in [('BFSD',[1,2,0,5,0,0,0,0])]+[('DSAG',[1,0,data,1,0,2,flag,0])for flag in [0,1,2]for data in [9,10]]:
                value=float(b.system.MFE.GetOperandValue(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name),*arguments))
                case['queries'].append(dict(operand=name,arguments=arguments,value=value));save()
            tool=None
            try:
                tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'SagTable'))
                tool.ApplyAndWaitForCompletion()
                path=folder/('sag-'+str(piston)+'.txt')
                case['text_exported']=bool(tool.GetResults().GetTextFile(str(path)))
                if path.is_file():case['text']=path.read_text(encoding='utf-16')
            finally:
                if tool is not None:case['closed']=b._close_task_native(dict(native=tool))
                save()
            case['preserved']=call('get_surfaces')==before and call('get_system_settings')==settings and call('get_merit_function')==merit
            assert case['preserved'];save()
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps([dict(piston=c['piston'],queries=c['queries'],closed=c.get('closed'),preserved=c.get('preserved'))for c in record['cases']]))

if __name__=='__main__':run(sys.argv[1])
