import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Compare real entrance refraction with Gradium RefN and GetIndex outputs."""
import json,math,sys,time
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='GRADIUM GetIndex/profile may be approximate while actual entrance refraction uses the exact RefN; use zero-thickness planar interface to remove GRIN integration',cases=[],calls=[])
    def save():(folder/'snell.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    def finish(task):
        while task['state']not in ['succeeded','failed','cancelled']:
            time.sleep(.03);task=call('get_task_status',dict(task_id=task['task_id']))
        result=call('get_task_result',dict(task_id=task['task_id']));assert task['state']=='succeeded',result
        return result
    try:
        call('connect');call('new_system');call('insert_surfaces',dict(at=1,count=2))
        call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)]))
        call('update_surfaces',dict(changes=[dict(surface=1,radius=0,thickness=1,material='',semi_diameter=1,replace_solves=True),
            dict(surface=2,surface_type='Gradium',radius=0,thickness=0,material='G14SFN',semi_diameter=1,parameters={1:.01,2:1},replace_solves=True)]))
        from System import Array,Double
        coefficients=[float(v)for v in (Path.home()/'Documents/Zemax/Glasscat/PROFILE.GRD').read_text().splitlines()[1:13]]
        for offset in [1.,1.25,1.5,1.75,2.]:
            call('update_surfaces',dict(changes=[dict(surface=2,parameters={2:offset},replace_solves=True)]))
            before=call('get_surfaces');settings=call('get_system_settings');merit=call('get_merit_function')
            indices=Array[Double]([0.,0.]);returned=int(b.system.LDE.GetIndex(2,2,indices))
            expected=sum(c*(offset/5.8)**i for i,c in enumerate(coefficients))
            rays=[dict(x=0,y=0,z=0,l=sine,m=0,n=math.sqrt(1-sine*sine),wavelength=wave)for wave in [1,2]for sine in [.05,.1,.2]]
            trace=finish(call('run_batch_ray_trace',dict(input_mode='Direct',start_surface=1,target_surface=2,rays=rays)))
            case=dict(offset=offset,reference_index=expected,get_index=list(indices),get_index_return=returned,trace=trace,checks=[])
            record['cases'].append(case);save()
            for request,row in zip(rays,trace['rows'],strict=True):
                if row['error_code']or row['vignette_code']:
                    case['checks'].append(dict(wavelength=request['wavelength'],input_sine=request['l'],state='ray_failed',ray=row));continue
                actual=request['l']/row['direction'][0]
                case['checks'].append(dict(wavelength=request['wavelength'],input_sine=request['l'],snell_index=actual,
                    get_index_error=actual-float(indices[request['wavelength']-1]),
                    reference_error=actual-expected if request['wavelength']==1 else None))
            case['preserved']=call('get_surfaces')==before and call('get_system_settings')==settings and call('get_merit_function')==merit
            assert case['preserved'];save()
    except BaseException as exc:record['error']=dict(type=type(exc).__name__,message=str(exc));save();raise
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(cases=len(record['cases']),ray_checks=sum(len(c['checks'])for c in record['cases']),disconnect_ok=record['disconnect']['ok'])))

if __name__=='__main__':run(sys.argv[1])
