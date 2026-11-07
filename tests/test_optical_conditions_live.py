"""Additional native conditions. Numerical checks do not imply other models are verified."""
from support.native import Evidence, execute
import asyncio,json,math,sys,time,uuid
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT

TYPES=("Standard","EvenAspheric","OddAsphere","Toroidal","Biconic","Paraxial","CoordinateBreak","GridSag","GridPhase")
SOLVES={"fixed":"Fixed","variable":"Variable","surface_pickup":"SurfacePickup","f_number":"FNumber","marginal_ray_height":"MarginalRayHeight","chief_ray_height":"ChiefRayHeight","edge_thickness":"EdgeThickness","position":"Position","pickup_chief_ray":"PickupChiefRay"}



@pytest.mark.zemax
def test_gaussian_mismatch_native():
    async def work(e):
        await e.model()
        for beam,fiber in (((.1,.1),(.15,.15)),((.1,.06),(.08,.09))):
            expected=math.prod(2*a*b/(a*a+b*b)for a,b in zip(beam,fiber))
            for n,width in (("S_256x256",2),("S_512x512",2),("S_512x512",4)):
                result=await e.finish(await e.call("run_pop",dict(request=dict(end_surface=2,beam_parameters={0:beam[0],1:beam[1]},fiber_type="GaussianWaist",fiber_parameters={0:fiber[0],1:fiber[1]},x_sampling=n,y_sampling=n,x_width=width,y_width=width))))
                m=result["metrics"]
                e.check("Gaussian mode mismatch "+str((beam,fiber,n,width)),m["receiver_efficiency"],expected,atol=5e-4)
                e.check("total coupling definition",m["total_coupling_efficiency"],m["system_efficiency"]*m["receiver_efficiency"])
    asyncio.run(execute("gaussian_mismatch",work))

@pytest.mark.zemax
def test_nonzero_grid_phase_native():
    async def work(e):
        await e.model()
        path=e.folder/"phase.dat"
        lines=["33 33 0.5 0.5 0"]
        for iy in range(33):
            for ix in range(33):
                x=(ix-16)*.5;y=(16-iy)*.5
                lines.append(f"{.02*x*x+.03*y*y+.01*x*y} {.04*x+.01*y} {.06*y+.01*x} 0.01")
        path.write_text("\n".join(lines),encoding="ascii")
        await e.call("update_surfaces",dict(changes=[dict(surface=1,surface_type="GridPhase",import_file=str(path),replace_solves=True)]))
        cells=(await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]

        for sign in (1,-1,0):
            signed=e.folder/f"phase_{sign}.dat"
            signed.write_text("\n".join([lines[0]]+[" ".join(str(float(v)*sign)for v in line.split())for line in lines[1:]]),encoding="ascii")
            await e.call("update_surfaces",dict(changes=[dict(surface=1,import_file=str(signed),replace_solves=True)]))
            for kind in ("surface_phase","surface_phase_cross"):
                r=await e.finish(await e.call("run_analysis",dict(request=dict(kind=kind,surface=1,sampling="S_33x33"))))
                if r.get("grids"):
                    g=r["grids"][0];points=[(g["min_x"]+ix*g["dx"],g["min_y"]+iy*g["dy"],g["values"][iy][ix])for ix,iy in ((24,16),(16,24),(24,24))]
                else:
                    s=r["series"][0];points=[(s["x"][i],s["y"][i][0],s["y"][i][1])for i in (8,16,24)]
                for x,y,value in points:e.check(f"{kind} input sign {sign} ({x},{y})",value,sign*(.02*x*x+.03*y*y+.01*x*y)/(2*math.pi))
        saved=e.folder/"phase.zos"
        await e.call("save_lens_as",dict(path=str(saved)))
        await e.call("open_lens",dict(path=str(saved)))
        reloaded=await e.finish(await e.call("run_analysis",dict(request=dict(kind="surface_phase",surface=1,sampling="S_33x33"))))
        e.check("reloaded zero phase",reloaded["grids"][0]["values"][16][16],0)
    asyncio.run(execute("nonzero_phase",work))

@pytest.mark.zemax
def test_solve_matrix_inventory_native():
    async def work(e):
        matrix=[]
        try:
            for surface_type in TYPES:
                await e.model()
                await e.call("update_surfaces",dict(changes=[dict(surface=1,surface_type=surface_type,replace_solves=True),dict(surface=2,surface_type=surface_type,replace_solves=True)]))
                cells=(await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]
                for cell,meta in cells.items():
                    for mode,native in SOLVES.items():
                        record=dict(surface_type=surface_type,cell=cell,header=meta["header"],mode=mode,native_available=native in meta["available_solves"])
                        matrix.append(record)
                        if not meta["writable"]:record["status"]="not_applicable";continue
                        if native not in meta["available_solves"]:record["status"]="native_unsupported";continue
                        if mode not in ("fixed","variable","surface_pickup"):
                            record.update(status="pending_numeric_reference",reason="Requires an independently defined optical fixture for this surface/cell.");continue
                        if mode=="surface_pickup":
                            # Surface 2 follows surface 1; direction avoids forward-reference surprises.
                            target=2;spec=dict(mode=mode,source_surface=1)
                        else:target=1;spec=dict(mode=mode)
                        result=await e.call("update_surfaces",dict(changes=[dict(surface=target,replace_solves=True,solves={cell:spec})]),okay=False)
                        if isinstance(result,dict)and result.get("ok")is False:
                            record.update(status="native_rejected" if result.get("error",{}).get("message")in {"原生单元格未采用请求的求解模式。","原生变量/固定模式未采用请求值。"} else "failed",error=result);continue
                        after=(await e.call("get_surfaces",dict(start=target,count=1)))["surfaces"][0]["cells"][cell]
                        if after["solve"]["type"]!=native:
                            record.update(status="failed",actual=after["solve"]["type"]);continue
                        if mode=="surface_pickup":
                            expected=(await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"][cell]["value"]
                        else:expected=meta["value"]
                        if type(expected)in (float,int)and math.isfinite(expected):e.check(f"{surface_type} {cell} {mode}",after["value"],expected)
                        else:assert after["value"]==expected
                        saved=e.folder/"matrix.zos"
                        await e.call("save_lens_as",dict(path=str(saved),overwrite=True))
                        await e.call("open_lens",dict(path=str(saved)))
                        loaded=(await e.call("get_surfaces",dict(start=target,count=1)))["surfaces"][0]["cells"][cell]
                        assert loaded["solve"]["type"]==native
                        record.update(status="passed",expected=expected,actual=after["value"],saved_value=loaded["value"])
                        await e.call("update_surfaces",dict(changes=[dict(surface=target,replace_solves=True,solves={cell:dict(mode="fixed")})]))
                print("Matrix",surface_type,len(matrix),flush=True)
        finally:(e.folder/"matrix.json").write_text(json.dumps(matrix,ensure_ascii=False,indent=2),encoding="utf-8")
        assert not [r for r in matrix if r["status"]=="failed"],[r for r in matrix if r["status"]=="failed"]
    asyncio.run(execute("solve_matrix",work))


@pytest.mark.zemax
def test_fresnel_oblique_native():
    async def work(e):
        # AGF formula 2: alternating B/C Sellmeier coefficients, wavelength in um.
        catalog=Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF"
        active=False;coefficients=None
        for line in catalog.read_text(encoding="utf-8-sig",errors="replace").splitlines():
            if line.startswith("NM "):
                active=line.split()[1]=="N-BK7"
                if active:assert line.split()[2]=="2"
            if active and line.startswith("CD "):coefficients=list(map(float,line.split()[1:7]));break
        assert coefficients is not None
        l2=.55**2;n=math.sqrt(1+sum(coefficients[i]*l2/(l2-coefficients[i+1])for i in (0,2,4)))
        await e.model();await e.call("insert_surfaces",dict(at=2))
        await e.call("update_system_settings",dict(settings=dict(material_catalogs=["SCHOTT"],polarization=dict(unpolarized=False,method="YAxisMethod"))))
        await e.call("update_surfaces",dict(changes=[dict(surface=1,thickness=10),dict(surface=2,material="N-BK7",thickness=10,semi_diameter=100,replace_solves=True)]))
        for degrees in (0,30):
            angle=math.radians(degrees);ct=math.sqrt(1-(math.sin(angle)/n)**2);ci=math.cos(angle)
            rs=((ci-n*ct)/(ci+n*ct))**2;rp=((n*ci-ct)/(n*ci+ct))**2
            for label,pol,transmission in (("p",dict(jx=1,jy=0),1-rp),("s",dict(jx=0,jy=1),1-rs),("circular",dict(jx=1,jy=1,y_phase=90),1-(rs+rp)/2)):
                r=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(input_mode="Direct",start_surface=1,target_surface=2,polarization=pol,rays=[dict(x=0,y=0,z=0,l=math.sin(angle),m=0,n=ci)]))))
                ray=r["rows"][0];assert ray["error_code"]==0,ray
                e.check(f"{degrees}deg {label} direction",ray["direction"][0],math.sin(angle)/n)
                e.check(f"{degrees}deg {label} transmission",ray["intensity"],transmission)
    asyncio.run(execute("oblique_fresnel",work))


@pytest.mark.zemax
def test_annular_pupil_native():
    async def work(e):
        import numpy as np
        await e.model()
        await e.call("update_surfaces",dict(changes=[dict(surface=1,aperture=dict(type="CircularObscuration",maximum_radius=1.5)),dict(surface=2,radius=-200,conic=-1,material="MIRROR",thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        n=2048
        x=(np.arange(n)+.5)*2/n-1
        yy=x[:,None]**2
        pupil=(x*x+yy<=1)&(x*x+yy>=.3**2)
        shift=2*50*.00055*100/10
        shifted=((x-shift)**2+yy<=1)&((x-shift)**2+yy>=.3**2)
        expected=float((pupil&shifted).sum()/pupil.sum())
        r=await e.finish(await e.call("run_analysis",dict(request=dict(kind="huygens_mtf",field=1,wavelength=1,sampling="S_256x256",image_sampling="S_512x512",maximum_frequency=50))))
        from zemax_mcp.evaluation import interpolate
        for s in r["series"]:
            for j in range(len(s["y"][0])):
                e.check("annular pupil MTF 50 cycles/mm",interpolate(s["x"],[v[j]for v in s["y"]],50),expected,atol=.02)
    asyncio.run(execute("annular_pupil",work))


@pytest.mark.zemax
def test_cooke_nonzero_wavefront_native():
    async def work(e):
        lens=Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        await e.call("open_lens",dict(path=str(lens)))
        settings=await e.call("get_system_settings")
        max_field=max(math.hypot(f["x"],f["y"])for f in settings["fields"])
        for sampling in ("S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024"):
            for field in (2,3):
                f=settings["fields"][field-1]
                r=await e.finish(await e.call("run_analysis",dict(request=dict(kind="wavefront",field=field,wavelength=2,sampling=sampling,remove_tilt=False,use_exit_pupil=False))))
                g=r["grids"][0]
                positions=[(g["nx"]//2+g["nx"]//8,g["ny"]//2),(g["nx"]//2,g["ny"]//2+g["ny"]//8),(g["nx"]//2-g["nx"]//10,g["ny"]//2-g["ny"]//12)]
                rays=[dict(hx=f["x"]/max_field,hy=f["y"]/max_field,px=g["min_x"]+ix*g["dx"],py=g["min_y"]+iy*g["dy"],wavelength=2)for ix,iy in positions]
                trace=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(rays=rays,opd=True))))
                for (ix,iy),ray in zip(positions,trace["rows"]):
                    assert ray["error_code"]==0 and ray["vignette_code"]==0,ray
                    e.check(f"Cooke field {field} OPD pupil {ix},{iy}",g["values"][iy][ix],ray["opd"])
                assert any(abs(g["values"][iy][ix])>1e-5 for ix,iy in positions),"fixture must have nonzero aberration"
    asyncio.run(execute("cooke_nonzero",work))
