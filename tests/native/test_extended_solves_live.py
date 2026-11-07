"""ED-02 serial native numerical and real-stdio acceptance."""
import asyncio,math,json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.solve_cases018 import CASES
from tests.support.material_reference import abbe, model_indices

LENS=Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"

async def setsolve(e,surface,cell,spec):
 return await e.call("update_surfaces",dict(changes=[dict(surface=surface,solves={cell:spec},replace_solves=True)]))

async def roundtrip(e,surface,cell,label):
 before=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]["cells"][cell]
 path=str(e.folder/(label+".zos"));await e.call("save_lens_as",dict(path=path));await e.call("open_lens",dict(path=path))
 after=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]["cells"][cell]
 assert before["solve"]==after["solve"]
 return after

@pytest.mark.zemax
def test_extended_solves_stdio():
 async def work(e):
  for cell,spec,surface in CASES[:17]:
   await e.call("open_lens",dict(path=str(LENS)))
   if spec["mode"]=="maximum":await e.call("update_configurations",{"request":dict(actions=[dict(action="add",copy_current=True)])})
   await setsolve(e,surface,cell,spec)
   await roundtrip(e,surface,cell,spec["mode"])
  await e.call("open_lens",dict(path=str(LENS)))
  await setsolve(e,6,"radius",dict(mode="marginal_ray_angle",angle=-.1))
  result=await e.finish(await e.call("run_batch_ray_trace",{"request":dict(target_surface=6,ray_type="Paraxial",rays=[dict(py=1,wavelength=2)])}))
  d=result["rows"][0]["direction"];e.check("paraxial angle from direction cosines",d[1]/d[2],-.1)
  await e.finish(await e.call("run_layout_export",{"request":dict(path=str(e.folder/"solved-layout.png"),width=640,height=480)}))
 asyncio.run(execute("extended_solves_stdio018",work))

@pytest.mark.zemax
@pytest.mark.parametrize("mode",["model","offset","substitute"])
def test_material_solves_numeric_stdio(mode):
 async def work(e):
  await e.model()
  wavelengths=[.5875618,.5876,.4861327,.4861,.6562725,.6563]
  await e.call("update_system_settings",dict(settings=dict(wavelengths=[dict(wavelength_um=w)for w in wavelengths],primary_wavelength=2)))
  await e.call("update_surfaces",dict(changes=[dict(surface=0,thickness=1),dict(surface=1,radius="Infinity",thickness=1,material="N-BK7",replace_solves=True)]))
  async def indices():
   result=await e.finish(await e.call("run_batch_ray_trace",{"request":dict(input_mode="Direct",start_surface=0,target_surface=1,rays=[dict(x=0,y=0,z=0,l=sine,m=0,n=math.sqrt(1-sine*sine),wavelength=w)for sine in [.1,.2]for w in range(1,7)])}))
   assert all(r["error_code"]==0 for r in result["rows"])
   values=[.1/r["direction"][0]for r in result["rows"][:6]]
   for wavelength,index,row in zip(wavelengths,values,result["rows"][6:]):
    e.check("Snell index at two incident angles, wavelength="+str(wavelength),.2/row["direction"][0],index,atol=1e-10,rtol=1e-10)
   return values
  if mode=="model":
   await setsolve(e,1,"material",dict(mode="material_model",index_nd=1.6,abbe_vd=60,dpgf=.001,vary_index=True,vary_dpgf=True))
   model=await indices()
   await roundtrip(e,1,"material","model-index")
   nd,nf,nc=model[1::2]
   e.check("model rounded d index from Snell",nd,1.6,atol=1e-6)
   e.check("model rounded Abbe from Snell",(nd-1)/(nf-nc),60,atol=1e-5)
  elif mode=="offset":
   base=await indices();d0,f0,c0=base[1::2]
   catalog=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7',include_internal_transmission=False,include_birefringence=False)))
   initial_model=await model_indices(e,wavelengths,catalog['properties'])
   adjusted_model=await model_indices(e,wavelengths,catalog['properties'],.001,1)
   reference=[n+adjusted-initial for n,adjusted,initial in zip(base,adjusted_model,initial_model)]
   await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',solves={'material':dict(mode='fixed')},replace_solves=True)]))
   await setsolve(e,1,"material",dict(mode="material_offset",nd_offset=.001,vd_offset=1))
   values=await indices()
   await roundtrip(e,1,"material","offset-index")
   nd,nf,nc=values[1::2]
   e.check("offset rounded d index",nd-d0,.001,atol=1e-6)
   e.check("offset rounded Abbe versus model-difference definition",(nd-1)/(nf-nc)-(d0-1)/(f0-c0),abbe(reference[1::2])-abbe(base[1::2]),atol=1e-5)
  else:
   before=await indices()
   await setsolve(e,1,"material",dict(mode="material_substitute",catalog="SCHOTT"))
   after=await indices()
   for a,b in zip(after,before):e.check("substitute retains selected material before optimization",a,b)
   await roundtrip(e,1,"material","substitute")
 asyncio.run(execute("material_"+mode+"_numeric048",work))


@pytest.mark.zemax
def test_automatic_dimensions_numeric_stdio():
 async def work(e):
  await e.model()
  await e.call("update_surfaces",dict(changes=[dict(surface=1,semi_diameter=4,chip_zone=.25,solves={"mechanical_semi_diameter":dict(mode="automatic")},replace_solves=True)]))
  c=(await roundtrip(e,1,"mechanical_semi_diameter","mechanical-auto"))["value"]
  e.check("automatic mechanical = clear + chip",c,4.25)
  await setsolve(e,1,"chip_zone",dict(mode="automatic"))
  c=(await roundtrip(e,1,"chip_zone","chip-auto"))["value"];e.check("native automatic chip preserves existing extension",c,.25)
  await e.call("open_lens",dict(path=str(LENS)))
  await e.call("update_configurations",{"request":dict(actions=[dict(action="add",copy_current=True)],operands=[dict(type="THIC",parameters={"1":4},cells=[dict(configuration=1,value=5),dict(configuration=2,value=20)])])})
  autos=[]
  for config in [1,2]:
   await e.call("set_configuration",dict(configuration=config));await setsolve(e,6,"semi_diameter",dict(mode="automatic"))
   autos.append((await e.call("get_surfaces",dict(start=6,count=1)))["surfaces"][0]["cells"]["semi_diameter"]["value"])
  assert abs(autos[0]-autos[1])>1e-3,autos
  await setsolve(e,6,"semi_diameter",dict(mode="maximum"))
  for config in [1,2]:
   await e.call("set_configuration",dict(configuration=config))
   c=(await e.call("get_surfaces",dict(start=6,count=1)))["surfaces"][0]["cells"]["semi_diameter"]["value"]
   e.check("maximum across distinct configurations",c,max(autos))
  await roundtrip(e,6,"semi_diameter","maximum")
 asyncio.run(execute("automatic_dimensions018",work))


@pytest.mark.zemax
def test_extended_solve_native_matrix():
 from tests.support.solve_cases018 import run
 from tests.support.paths import run_dir
 cases=run(run_dir("extended_solve_matrix018"))
 rejected={"surface_pickup.mechanical_semi_diameter","surface_pickup.chip_zone","zpl_macro.mechanical_semi_diameter","zpl_macro.chip_zone"}
 for c in cases:
  if c["id"]in rejected:
   assert c["state"]=="failed",c
   assert "SOLVE_UPDATE_FAILED"in c["error"]or"SETTING_REJECTED"in c["error"],c
  else:
   assert c["state"]=="persistence_passed",c
   assert all(n["passed"]for n in c.get("numeric",[])),c
