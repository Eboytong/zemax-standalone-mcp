"""Formal Gradium surface/GRIN settings discovery on an owned baseline."""
import json,sys,time
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder, delta_t=.01):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
 b=Backend(Config(Config.from_env().install_dir,folder/'native'));r={'item_id':'MA-01.GradiumProfile','calls':[],'runs':[]}
 def save(): (folder/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 def call(name,args=None):
  r['stage']=name;save();v=b.dispatch(name,args or {});r['calls'].append(dict(tool=name,arguments=args,response=v));save()
  if not v['ok']:raise RuntimeError(str(v))
  return v['data']
 try:
  call('connect');call('new_system');call('insert_surfaces',dict(at=1))
  call('update_system_settings',dict(aperture_value=2,wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)]))
  call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Gradium',material='G14SFN',thickness=1,semi_diameter=1,parameters={1:delta_t,2:1},replace_solves=True)]))
  r['surfaces']=call('get_surfaces');r['system_settings']=call('get_system_settings')
  for wave in [1,2]:
   q=dict(kind='grin_profile',surface=1,wavelength=wave,show_index_vs='Z',minimum_z=0,maximum_z=1,x_value=0,y_value=0)
   task=call('run_analysis',dict(request=q));deadline=time.monotonic()+30
   while task['state'] not in ['succeeded','failed','cancelled']:
    if time.monotonic()>deadline:
     call('cancel_task',dict(task_id=task['task_id']));raise TimeoutError('GRIN30s')
    time.sleep(.05);task=call('get_task_status',dict(task_id=task['task_id']))
   result=call('get_task_result',dict(task_id=task['task_id']))
   if wave==1:
    lines=(Path.home()/'Documents/Zemax/Glasscat/PROFILE.GRD').read_text().splitlines()
    coefficients=[float(value) for value in lines[1:13]];r['reference']=dict(resource='PROFILE.GRD',profile='G14SFN',family='GSF',wavelength_um=.58756,delta_t=delta_t,formula='sum(n_i*((z+DeltaZ)/MAX_Z)**i)',atol=1e-10,rtol=1e-9,checks=[])
    for x,y in zip(result['series'][0]['x'],result['series'][0]['y'],strict=True):
     expected=sum(c*((x+1)/5.8)**i for i,c in enumerate(coefficients));actual=y[0]
     r['reference']['checks'].append(dict(z=x,expected=expected,actual=actual,error=abs(actual-expected),passed=abs(actual-expected)<=1e-10+1e-9*abs(expected)))
    r['reference']['passed']=all(c['passed'] for c in r['reference']['checks'])
    save()
   r['runs'].append(dict(request=q,task=task,result=result));save()
 except Exception as exc:r['error']=dict(type=type(exc).__name__,message=str(exc));save()
 finally:
  r['disconnect']=b.dispatch('disconnect',{});r['stage']='closed';save()
 print(json.dumps(dict(error=r.get('error'),runs=len(r['runs']),disconnect=r['disconnect']),ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1],float(sys.argv[2])if len(sys.argv)>2 else .01)
