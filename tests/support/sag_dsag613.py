"""Query documented DSAG radius and physical vertex-offset outputs."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='DSAG Data9/10 provides the native sphere radius and physical vertex offset for RMS criteria',parameter_identity='614 formal row columns2..9: Surf,unused,Data,Samp,Off-axis,Remove,BFS,unused',cases=[],calls=[])
    def save():(folder/'queries.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('new_system')
        code=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,'DSAG')
        for sign in [1,-1]:
            call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=sign*40,conic=-1,parameters={'1':sign*.0001},semi_diameter=5,thickness=20,replace_solves=True)]))
            before=call('get_surfaces');settings=call('get_system_settings');merit=call('get_merit_function')
            for flag in [0,1,2,3]:
                for sampling in [1,3]:
                    case=dict(sign=sign,flag=flag,sampling=sampling,queries=[]);record['cases'].append(case);save()
                    for data in [9,10]:
                        args=[1,0,data,sampling,0,2,flag,0.]
                        value=float(b.system.MFE.GetOperandValue(code,*args))
                        case['queries'].append(dict(operand='DSAG',arguments=args,value=value));save()
            assert call('get_surfaces')==before and call('get_system_settings')==settings and call('get_merit_function')==merit
        record['preserved']=True
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(record['cases'],ensure_ascii=False))

if __name__=='__main__':run(sys.argv[1])
