"""Locate the installed model-glass dispersion wavelength anchors."""
import json
import sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean

def run(folder=None):
 folder=Path(folder or "verification/development/ED-02/material-diagnostic018");folder.mkdir(parents=True,exist_ok=True)
 b=Backend(Config(Config.from_env().install_dir,folder/"native"));calls=[];out=dict(closed=False)
 def call(n,a=None):
  r=b.dispatch(n,a or {});calls.append(dict(tool=n,args=a,response=r));assert r["ok"],r;return r["data"]
 try:
  call("connect")
  from System import Array,Double
  call("new_system");call("update_system_settings",dict(wavelengths=[dict(wavelength_um=w)for w in [.5875618,.5876,.4861327,.4861,.6562725,.6563]]))
  out['wavelengths']=[.5875618,.5876,.4861327,.4861,.6562725,.6563]
  out['environment']=call('get_system_settings')
  out['models']=[]
  for nd,vd,dpgf in [(1.6,60,0),(1.6,60,.001),(1.5,50,0)]:
   request=dict(mode="material_model",index_nd=nd,abbe_vd=vd,dpgf=dpgf)
   call("update_surfaces",dict(changes=[dict(surface=1,solves={"material":request},replace_solves=True)]))
   a=Array[Double]([0.]*6);b.system.LDE.GetIndex(1,6,a)
   out['models'].append(dict(request=request,index=list(a),actual=call('get_surfaces',dict(start=1,count=1)),physical_abbe=(a[0]-1)/(a[2]-a[4]),rounded_abbe=(a[1]-1)/(a[3]-a[5])))
  call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',solves={'material':dict(mode='fixed')},replace_solves=True)]))
  a=Array[Double]([0.]*6);b.system.LDE.GetIndex(1,6,a)
  out['base_index']=list(a)
  out['catalog']=call('get_material_properties',dict(catalog='SCHOTT',material='N-BK7',include_internal_transmission=False,include_birefringence=False))
  out['offsets']=[]
  for nd,vd in [(0,0),(.001,0),(0,1),(.001,1)]:
   request=dict(mode='material_offset',nd_offset=nd,vd_offset=vd)
   call('update_surfaces',dict(changes=[dict(surface=1,solves={'material':request},replace_solves=True)]))
   a=Array[Double]([0.]*6);b.system.LDE.GetIndex(1,6,a)
   out['offsets'].append(dict(request=request,index=list(a),actual=call('get_surfaces',dict(start=1,count=1)),physical_abbe=(a[0]-1)/(a[2]-a[4]),rounded_abbe=(a[1]-1)/(a[3]-a[5])))
  props=out['catalog']['properties']
  out['offset_model_reference']=[]
  for dpgf in [0,props['dPgF']]:
   refs=[]
   for nd,vd in [(0,0),(.001,0),(0,1),(.001,1)]:
    request=dict(mode='material_model',index_nd=props['Nd']+nd,abbe_vd=props['Vd']+vd,dpgf=dpgf)
    call('update_surfaces',dict(changes=[dict(surface=1,solves={'material':request},replace_solves=True)]))
    a=Array[Double]([0.]*6);b.system.LDE.GetIndex(1,6,a)
    refs.append(dict(request=request,index=list(a)))
   for ref,offset in zip(refs,out['offsets']):
    ref['expected_offset_index']=[base+adjusted-initial for base,adjusted,initial in zip(out['base_index'],ref['index'],refs[0]['index'])]
    ref['errors']=[actual-expected for actual,expected in zip(offset['index'],ref['expected_offset_index'])]
   out['offset_model_reference'].append(dict(dpgf=dpgf,comparisons=refs))
  call("disconnect");out["closed"]=True
 finally:
  b.shutdown();(folder/"calls.json").write_text(json.dumps(clean(calls),ensure_ascii=False,indent=2),encoding="utf-8")
  (folder/"anchors.json").write_text(json.dumps(clean(out),ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps(dict(closed=out['closed'],models=[dict(request=m['request'],physical_abbe=m['physical_abbe'],rounded_abbe=m['rounded_abbe']) for m in out['models']],offsets=[dict(request=m['request'],physical_abbe=m['physical_abbe'],rounded_abbe=m['rounded_abbe']) for m in out['offsets']]),indent=2))
if __name__=="__main__":run(sys.argv[1] if len(sys.argv)>1 else None)
