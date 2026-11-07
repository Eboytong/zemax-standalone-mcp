"""ED-02 independent baseline requests and persistent native evidence."""
import json,math
from pathlib import Path
from zemax_mcp.config import Config
from zemax_mcp.backend import Backend
from zemax_mcp.data import clean
import time

CASES=[
 ("radius",dict(mode="marginal_ray_angle",angle=-.1),6),
 ("radius",dict(mode="chief_ray_angle",angle=.1),6),
 ("radius",dict(mode="marginal_ray_normal"),6),
 ("radius",dict(mode="chief_ray_normal"),6),
 ("radius",dict(mode="aplanatic"),6),
 ("radius",dict(mode="element_power",power=.02),6),
 ("radius",dict(mode="concentric_surface",source_surface=1),6),
 ("radius",dict(mode="concentric_radius",source_surface=1),6),
 ("thickness",dict(mode="optical_path_difference",opd=0,pupil_zone=.7),6),
 ("thickness",dict(mode="compensator",source_surface=1,sum=20),6),
 ("thickness",dict(mode="center_of_curvature",source_surface=1),6),
 ("thickness",dict(mode="pupil_position"),6),
 ("material",dict(mode="material_model",index_nd=1.6,abbe_vd=60,dpgf=.001,vary_index=True,vary_abbe=False,vary_dpgf=True),1),
 ("material",dict(mode="material_offset",nd_offset=.001,vd_offset=1),1),
 ("material",dict(mode="material_substitute",catalog="SCHOTT"),1),
 ("semi_diameter",dict(mode="automatic"),6),
 ("semi_diameter",dict(mode="maximum"),6),
]
for cell in ("mechanical_semi_diameter","chip_zone"):
 CASES.extend([(cell,dict(mode="fixed"),6),(cell,dict(mode="automatic"),6),(cell,dict(mode="surface_pickup",source_surface=1),6)])
for cell in ("radius","thickness","semi_diameter","mechanical_semi_diameter","chip_zone","conic",*("parameter_"+str(i)for i in (*range(1,11),13,14))):
 CASES.append((cell,dict(mode="zpl_macro",macro="ED02_COUNT018" if cell in {"parameter_13","parameter_14"}else"ED02_CONSTANT018"),6))

def numeric(b,call,item):
 cell=item["cell"];spec=item["spec"];surface=item["surface"];mode=spec["mode"];checks=[]
 def check(label,value,expected,atol=1e-8,rtol=1e-7):
  passed=math.isfinite(value)and abs(value-expected)<=atol+rtol*abs(expected)
  checks.append(dict(label=label,actual=value,expected=expected,atol=atol,rtol=rtol,passed=passed))
 def trace(target,hy=0,py=0,kind="Paraxial",opd=False):
  t=call("run_batch_ray_trace",dict(target_surface=target,ray_type=kind,opd=opd,rays=[dict(hy=hy,py=py,wavelength=2)]))
  while t["state"]not in {"succeeded","failed","cancelled"}:
   time.sleep(.005);t=call("get_task_status",dict(task_id=t["task_id"]))
  r=call("get_task_result",dict(task_id=t["task_id"]));assert t["state"]=="succeeded",r
  row=r["rows"][0];assert row["error_code"]==0,row;return row
 def rows():return call("get_surfaces",dict(start=0,count=20))["surfaces"]
 rs=rows();c=rs[surface]["cells"];r=c[cell]["value"]
 if mode in {"marginal_ray_angle","chief_ray_angle"}:
  ray=trace(surface,hy=1 if mode=="chief_ray_angle"else 0,py=1 if mode=="marginal_ray_angle"else 0)
  check("paraxial outgoing slope",ray["direction"][1]/ray["direction"][2],spec["angle"])
 if mode in {"marginal_ray_normal","chief_ray_normal","aplanatic"}:
  ray=trace(surface-1,hy=1 if mode=="chief_ray_normal"else 0,py=0 if mode=="chief_ray_normal"else 1)
  u=ray["direction"][1]/ray["direction"][2];y=ray["position"][1]+rs[surface-1]["cells"]["thickness"]["value"]*u
  expected=-y/u
  if mode=="aplanatic":
   from System import Array,Double
   n=[]
   for i in [surface-1,surface]:
    a=Array[Double]([0.]*int(b.system.SystemData.Wavelengths.NumberOfWavelengths));b.system.LDE.GetIndex(i,len(a),a);n.append(float(a[1]))
   expected*=n[0]/sum(n)
  check("paraxial conjugate radius",r,expected)
 if mode=="element_power":
  from System import Array,Double
  ns=[]
  for i in [surface-2,surface-1,surface]:
   a=Array[Double]([0.]*int(b.system.SystemData.Wavelengths.NumberOfWavelengths));b.system.LDE.GetIndex(i,len(a),a);ns.append(float(a[1]))
  c1=1/rs[surface-1]["cells"]["radius"]["value"];c2=1/r;t=rs[surface-1]["cells"]["thickness"]["value"]
  p1=(ns[1]-ns[0])*c1;p2=(ns[2]-ns[1])*c2
  check("thick element power",p1+p2-t/ns[1]*p1*p2,spec["power"])
 if mode in {"concentric_surface","concentric_radius","center_of_curvature"}:
  ref=spec["source_surface"];distance=sum(rs[i]["cells"]["thickness"]["value"]for i in range(ref,surface))
  radius=rs[ref]["cells"]["radius"]["value"]
  check("axial center of curvature",r,(0 if mode=="concentric_surface"else radius)-distance)
 if mode=="compensator":check("compensator thickness sum",r+rs[spec["source_surface"]]["cells"]["thickness"]["value"],spec["sum"])
 if mode=="optical_path_difference":
  ray=trace(len(rs)-1,py=spec["pupil_zone"],kind="Real",opd=True)
  check("exit pupil OPD waves",ray["opd"],spec["opd"],atol=1e-5,rtol=1e-7)
 if mode=="pupil_position":
  a=trace(surface,hy=-1e-5,kind="Real");d=trace(surface,hy=1e-5,kind="Real")
  u1=a["direction"][1]/a["direction"][2];u2=d["direction"][1]/d["direction"][2]
  y1=a["position"][1]-a["position"][2]*u1;y2=d["position"][1]-d["position"][2]*u2
  check("differential real chief pupil",r,-(y2-y1)/(u2-u1),atol=1e-6,rtol=1e-6)
 if mode=="zpl_macro":check("constant macro; radius uses curvature",r,8 if cell=="radius"else 4 if spec["macro"]=="ED02_COUNT018"else .125)
 if mode=="maximum":
  autos=[]
  for configuration in (1,2):
   call("set_configuration",dict(configuration=configuration));autos.append(call("get_surfaces",dict(start=surface,count=1))["surfaces"][0]["cells"][cell]["value"])
  check("maximum same configurations",autos[0],autos[1])
 return checks

def run(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
 macro=Path.home()/"Documents/Zemax/Macros/ED02_CONSTANT018.ZPL"
 if macro.exists():raise RuntimeError("Owned fixture name already exists")
 macro.write_text("SOLVERETURN .125\n",encoding="ascii")
 count_macro=macro.with_name("ED02_COUNT018.ZPL")
 if count_macro.exists():raise RuntimeError("Owned count macro already exists")
 count_macro.write_text("SOLVERETURN 4\n",encoding="ascii")
 b=Backend(Config(Config.from_env().install_dir,folder/"native"));events=[];cases=[]
 def call(name,args=None):
  r=b.dispatch(name,args or {});events.append(dict(tool=name,args=args,response=r))
  if not r["ok"]:raise RuntimeError(str(r["error"]))
  return r["data"]
 try:
  call("connect")
  lens=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
  for cell,spec,surface in CASES:
   item=dict(id=spec["mode"]+"."+cell,cell=cell,spec=spec,surface=surface);cases.append(item)
   try:
    call("open_lens",dict(path=lens))
    if cell.startswith("parameter_"):call("update_surfaces",dict(changes=[dict(surface=surface,surface_type=("EvenAspheric" if int(cell[10:])<=8 else "GridSag" if int(cell[10:])in (9,10) else "ExtendedAsphere"),replace_solves=True)]))
    if cell in {"parameter_9","parameter_10"}:
     gridfile=folder/(cell+".dat")
     gridfile.write_text("33 33 1 1 0\n"+"\n".join(f"{.0001*(x-16)**2+.0002*(y-16)**2} {.0002*(x-16)} {.0004*(y-16)} 0"for y in range(33)for x in range(33)),encoding="ascii")
     call("update_surfaces",dict(changes=[dict(surface=surface,import_file=str(gridfile.resolve()),replace_solves=True)]))
    if spec["mode"]=="maximum":
     call("update_configurations",dict(actions=[dict(action="add",copy_current=True)]))
    item["before"]=call("get_surfaces",dict(start=surface,count=1))["surfaces"][0]
    item["request"]=dict(changes=[dict(surface=surface,solves={cell:spec},replace_solves=True)])
    result=call("update_surfaces",item["request"])
    item["adopted"]=result["surfaces"][0]["cells"][cell]
    path=folder/(item["id"]+".zos")
    call("save_lens_as",dict(path=str(path.resolve())))
    call("open_lens",dict(path=str(path.resolve())))
    item["reloaded"]=call("get_surfaces",dict(start=surface,count=1))["surfaces"][0]["cells"][cell]
    assert item["adopted"]["solve"]==item["reloaded"]["solve"],item
    item["state"]= "persistence_passed"
    item["numeric"]=numeric(b,call,item)
    if any(not c["passed"]for c in item["numeric"]):item["state"]="reference_exceeded"

   except Exception as exc:item.update(state="failed",error=str(exc))
   print(item["id"],item["state"],item.get("error","")[:400],flush=True)
  call("disconnect")
 finally:
  b.shutdown();macro.unlink(missing_ok=True);count_macro.unlink(missing_ok=True)
  (folder/"calls.json").write_text(json.dumps(clean(events),ensure_ascii=False,indent=2),encoding="utf-8")
  (folder/"cases.json").write_text(json.dumps(clean(cases),ensure_ascii=False,indent=2),encoding="utf-8")
 return cases
if __name__=="__main__":
 import sys
 run(sys.argv[1] if len(sys.argv)>1 else "verification/development/ED-02/native018")
