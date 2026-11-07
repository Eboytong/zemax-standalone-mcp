"""Controlled POWR/POWF operand semantics against one spherical interface."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(folder):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False);b=Backend(Config(Config.from_env().install_dir,folder/'native'));out={}
 def call(n,a=None):r=b.dispatch(n,a or {});assert r['ok'],r;out.setdefault('calls',[]).append(dict(tool=n,args=a,response=r));return r['data']
 try:
  call('connect');call('new_system');call('insert_surfaces',dict(at=1));call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.5875618)],aperture_value=8));call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=50,material='N-BK7',semi_diameter=8,replace_solves=True)]))
  out['surfaces']=call('get_surfaces');out['properties']=call('get_system_settings');from System import Array,Double
  n=Array[Double]([0.]);out['get_index_return']=b.system.LDE.GetIndex(1,1,n);out['index']=float(n[0])
  M=b.native.api.Editors.MFE.MeritOperandType
  results=[]
  for operand,args in [('POWR',[1,1]),('POWF',[1,1,0.,0.,0.,0.,0.,0.])]+[('POWF',[1,1,0.,0.,float(d),0.,0.,0.])for d in range(1,9)]+[('POWF',[1,1,0.,0.,9.,0.,0.,0.]),('POWF',[1,1,0.,0.,10.,0.,0.,0.])]:
   code=b.native.enum(MeritOperandType if False else M,operand)
   try:v=float(b.system.MFE.GetOperandValue(code,*args));results.append(dict(operand=operand,args=args,value=v))
   except Exception as exc:results.append(dict(operand=operand,args=args,error=str(exc)))
  out['queries']=results;out['analytic_surface_diopters']=1000*(1.5168-1)/50;out['actual_index_formula_diopters']=1000*(float(n[0])-1)/50
 finally:out['disconnect']=b.dispatch('disconnect',{});(folder/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
 print(json.dumps(dict(index=out.get('index'),analytic=out.get('analytic_surface_diopters'),queries=out.get('queries'),disconnect=out.get('disconnect',{}).get('ok')),ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1])
