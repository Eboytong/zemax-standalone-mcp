import math,json
from pathlib import Path
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from support.paths import run_dir

@pytest.mark.zemax
def test_solve_numeric_references():
    folder=run_dir("solves")
    b=Backend(Config(Config.from_env().install_dir,folder));events=[];checks=[]
    lens=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
    def call(name,args=None):
        r=b.dispatch(name,args or {});events.append(dict(tool=name,arguments=args,response=r));assert r["ok"],r
        return r["data"]
    def close_task(t):
        import time
        for _ in range(1000):
            if t["state"] in {"succeeded","failed","cancelled"}:break
            time.sleep(.01);t=call("get_task_status",dict(task_id=t["task_id"]))
        r=call("get_task_result",dict(task_id=t["task_id"]));assert t["state"]=="succeeded",r
        return r
    def solve(surface,cell,spec):call("update_surfaces",dict(changes=[dict(surface=surface,replace_solves=True,solves={cell:spec})]))
    def trace(target,ray_type="Real",hy=0,py=0):
        return close_task(call("run_batch_ray_trace",dict(target_surface=target,ray_type=ray_type,rays=[dict(hy=hy,py=py,wavelength=2)])))["rows"][0]
    try:
        call("connect")
        for zone in (0,.7,-.7):
            call("open_lens",dict(path=lens));solve(6,"thickness",dict(mode="marginal_ray_height",height=.1,pupil_zone=zone))
            ray=trace(7,"Paraxial" if zone==0 else "Real",py=1 if zone==0 else zone)
            assert ray["error_code"]==0 and ray["position"][1]==pytest.approx(.1,rel=1e-7,abs=1e-8),ray
            checks.append(dict(mode="marginal_ray_height",zone=zone,measured=ray["position"][1],expected=.1))
        call("open_lens",dict(path=lens));solve(6,"thickness",dict(mode="chief_ray_height",height=1))
        ray=trace(7,"Paraxial",hy=1)
        assert ray["position"][1]==pytest.approx(1,rel=1e-7,abs=1e-8),ray
        checks.append(dict(mode="chief_ray_height",measured=ray["position"][1],expected=1))
        call("open_lens",dict(path=lens));solve(1,"thickness",dict(mode="edge_thickness",thickness=2,radial_height=1))
        g1=call("get_surface_geometry",dict(surface=1,points=[dict(x=1,y=0)]))["rows"][0]["sag"]
        g2=call("get_surface_geometry",dict(surface=2,points=[dict(x=1,y=0)]))["rows"][0]["sag"]
        thickness=call("get_surfaces",dict(start=1,count=1))["surfaces"][0]["cells"]["thickness"]["value"]
        assert thickness+g2-g1==pytest.approx(2,rel=1e-7,abs=1e-8)
        checks.append(dict(mode="edge_thickness",measured=thickness+g2-g1,expected=2))
        for surface,source,length in ((6,1,60),(6,6,40),(3,7,60)):
            call("open_lens",dict(path=lens));solve(surface,"thickness",dict(mode="position",source_surface=source,length=length))
            rows=call("get_surfaces",dict(start=1,count=7))["surfaces"]
            lo,hi=(source,surface+1) if source<=surface else (surface,source)
            measured=sum(r["cells"]["thickness"]["value"] for r in rows if lo<=r["surface"]<hi)
            assert measured==pytest.approx(length,rel=1e-7,abs=1e-8)
            checks.append(dict(mode="position",surface=surface,source=source,measured=measured,expected=length))
        for parameter in range(1,7):
            call("open_lens",dict(path=lens));call("update_surfaces",dict(changes=[dict(surface=2,surface_type="CoordinateBreak",replace_solves=True)]))
            cell=call("get_surfaces",dict(start=2,count=1))["surfaces"][0]["cells"].get(f"parameter_{parameter}")
            if not cell or "PickupChiefRay"not in cell["available_solves"]:
                checks.append(dict(mode="pickup_chief_ray",parameter=parameter,supported=False));continue
            solve(2,f"parameter_{parameter}",dict(mode="pickup_chief_ray",field=2,wavelength=2))
            ray=trace(2,hy=.7)
            index=parameter-1
            if parameter in (1,2):assert ray["position"][index]==pytest.approx(0,abs=1e-8),ray
            elif parameter in (3,4):assert ray["direction"][1 if parameter==3 else 0]==pytest.approx(0,abs=1e-8),ray
            else:pytest.fail("未定义的主光线拾取参数行为需补充参考。")
            saved=str(folder/f"pickup_{parameter}.zos");call("save_lens_as",dict(path=saved));call("open_lens",dict(path=saved))
            loaded=call("get_surfaces",dict(start=2,count=1))["surfaces"][0]["cells"][f"parameter_{parameter}"]
            assert loaded["solve"]["type"]=="PickupChiefRay",loaded
            checks.append(dict(mode="pickup_chief_ray",parameter=parameter,supported=True,ray=ray))
        call("disconnect")
    finally:
        b.shutdown()
        (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
        (folder/"checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Solve evidence:",folder,flush=True)
