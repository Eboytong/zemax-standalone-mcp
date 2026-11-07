"""Native review checks for variable adoption and all WavefrontMap option pairs."""
import asyncio,math
from pathlib import Path
import numpy as np
import pytest
from support.native import execute

@pytest.mark.zemax
def test_set_variables_native_adoption():
    async def work(e):
        for kind in ("Standard","Paraxial","CoordinateBreak","GridPhase"):
            await e.model()
            await e.call("update_surfaces",dict(changes=[dict(surface=1,surface_type=kind,replace_solves=True)]))
            r=await e.call("set_variables",dict(variables=[dict(surface=1,cell="radius")]),okay=False)
            cell=(await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["radius"]
            if kind=="Standard":
                assert "variables"in r and cell["solve"]["type"]=="Variable",(r,cell)
                await e.call("set_variables",dict(variables=[dict(surface=1,cell="radius",variable=False)]))
                assert (await e.call("get_surfaces",dict(start=1,count=1)))["surfaces"][0]["cells"]["radius"]["solve"]["type"]=="Fixed"
            else:
                assert not r["ok"]and r["error"]["code"]=="SOLVE_UPDATE_FAILED",(r,cell)
                assert r["error"]["details"]["actual"]==cell["solve"]["type"]
                assert r["error"]["details"]["partial_changes_possible"]
                e.check(kind+" ignored variable rejected",int(not r["ok"]),1)
    asyncio.run(execute("variables_adoption",work))

@pytest.mark.zemax
def test_wavefront_public_options():
    async def work(e):
        await e.call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        fields=(await e.call("get_system_settings"))["fields"];maximum=max(math.hypot(f["x"],f["y"])for f in fields)
        samplings=("S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024")
        for sampling in samplings:
            for field in ((2,3)if sampling=="S_64x64"else(2,)):
                raw={}
                for exit_pupil in (False,True):
                    request=dict(kind="wavefront",sampling=sampling,field=field,wavelength=2,remove_tilt=False,use_exit_pupil=exit_pupil)
                    r=await e.finish(await e.call("run_analysis",dict(request=request)));g=r["grids"][0]
                    positions=[(g["nx"]//2+g["nx"]//8,g["ny"]//2),(g["nx"]//2,g["ny"]//2+g["ny"]//8),(g["nx"]//2-g["nx"]//10,g["ny"]//2-g["ny"]//12)]
                    if exit_pupil:
                        assert g["pupil_frame"]=="apparent exit pupil shape"
                        assert "not numerically verified"in g["coordinate_validation"]
                        for key in ("min_x","min_y","dx","dy"):assert g[key]==g["native_axes"][key]
                        e.check(f"{sampling} field={field} exit shape chief OPD",g["values"][g["ny"]//2][g["nx"]//2],0)
                    else:
                        f=fields[field-1]
                        rays=[dict(hx=f["x"]/maximum,hy=f["y"]/maximum,px=g["min_x"]+ix*g["dx"],py=g["min_y"]+iy*g["dy"],wavelength=2)for ix,iy in positions]
                        tr=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(rays=rays,opd=True))))
                        for (ix,iy),ray in zip(positions,tr["rows"]):
                            assert ray["error_code"]==0 and ray["vignette_code"]==0,ray
                            e.check(f"{sampling} field={field} exit={exit_pupil} OPD {ix},{iy}",g["values"][iy][ix],ray["opd"])
                    raw[exit_pupil]=g
                    # Omitting both public options exercises the actual default request.
                    if exit_pupil:request.pop("remove_tilt");request.pop("use_exit_pupil")
                    else:request["remove_tilt"]=True
                    result=await e.finish(await e.call("run_analysis",dict(request=request)));tilted=result["grids"][0]
                    settings=result["task"]["settings"]["native"]
                    assert settings["RemoveTilt"]and settings["UseExitPupil"]==exit_pupil,settings
                    for key in ("min_x","min_y","dx","dy","nx","ny"):assert tilted[key]==g[key]
                    a=[];b=[]
                    for iy in range(0,g["ny"],max(1,g["ny"]//16)):
                        for ix in range(0,g["nx"],max(1,g["nx"]//16)):
                            before=g["values"][iy][ix];after=tilted["values"][iy][ix]
                            if before is not None and after is not None:
                                a.append([1,g["min_x"]+ix*g["dx"],g["min_y"]+iy*g["dy"]]);b.append(before-after)
                    assert len(a)>10
                    fit=np.linalg.lstsq(np.asarray(a),np.asarray(b),rcond=None)[0]
                    residual=float(np.max(np.abs(np.asarray(a)@fit-b)))
                    e.check(f"{sampling} field={field} exit={exit_pupil} removed affine tilt",residual,0)
                    e.checks[-1]["fitted_plane"]=list(map(float,fit))
                    if exit_pupil and sampling=="S_64x64":
                        request.update(remove_tilt=True,use_exit_pupil=True)
                        explicit=(await e.finish(await e.call("run_analysis",dict(request=request))))["grids"][0]
                        for ix,iy in positions:e.check("explicit true/true matches public defaults",explicit["values"][iy][ix],tilted["values"][iy][ix])
    asyncio.run(execute("wavefront_options",work))

