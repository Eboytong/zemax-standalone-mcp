"""Nonzero OPD: real-ray reference, polynomial reconstruction and signed fans."""
import asyncio
import json
import math
import pytest
from support.native import execute


def phase_polynomial(kind,x,y):
    if kind=="spherical":return (x*x+y*y)**2,4*x*(x*x+y*y),4*y*(x*x+y*y),8*x*y
    if kind=="coma":return x*(x*x+y*y),3*x*x+y*y,2*x*y,2*y
    if kind=="astigmatism":return x*x-y*y,2*x,-2*y,0
    return x*x+y*y,2*x,2*y,0


def fringe16(x,y):
    r=x*x+y*y
    return [1.,x,y,2*r-1,x*x-y*y,2*x*y,(3*r-2)*x,(3*r-2)*y,6*r*r-6*r+1,
        x**3-3*x*y*y,3*x*x*y-y**3,(4*r-3)*(x*x-y*y),(4*r-3)*2*x*y,
        (10*r*r-12*r+3)*x,(10*r*r-12*r+3)*y,20*r**3-30*r*r+12*r-1]


@pytest.mark.zemax
@pytest.mark.parametrize("kind",["spherical","coma","astigmatism","defocus"])
def test_nonzero_wavefront_zernike_fan_cross_native(kind):
    async def work(e):
        await e.model();coefficient=.2;radius=5.;lines=["65 65 0.25 0.25 0"]
        for iy in range(65):
            for ix in range(65):
                p,px,py,pxy=phase_polynomial(kind,(ix-32)*.25/radius,(32-iy)*.25/radius)
                lines.append(" ".join(map(str,(2*math.pi*coefficient*p,2*math.pi*coefficient*px/radius,2*math.pi*coefficient*py/radius,2*math.pi*coefficient*pxy/radius**2))))
        path=e.folder/"phase.dat";path.write_text("\n".join(lines),encoding="ascii")
        await e.call("update_surfaces",dict(changes=[dict(surface=1,surface_type="GridPhase",import_file=str(path),replace_solves=True),
            dict(surface=2,radius=-200,conic=-1,material="MIRROR",thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        await e.call("save_lens_as",dict(path=str(e.folder/(kind+".zos"))))
        wave=await e.finish(await e.call("run_analysis",dict(request=dict(kind="wavefront",field=1,wavelength=1,sampling="S_128x128",remove_tilt=False,use_exit_pupil=False))))
        g=wave["grids"][0];cx,cy=g["nx"]//2,g["ny"]//2
        positions=[(cx+dx,cy+dy)for dx,dy in((0,0),(16,0),(-16,0),(0,16),(0,-16),(24,24),(-24,24))]
        rays=[dict(px=g["min_x"]+ix*g["dx"],py=g["min_y"]+iy*g["dy"],wavelength=1)for ix,iy in positions]
        trace=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(rays=rays,opd=True))))
        for (ix,iy),row in zip(positions,trace["rows"]):
            assert row["error_code"]==row["vignette_code"]==0
            e.check("wavefront versus independent ray OPD waves",g["values"][iy][ix],row["opd"])
        coefficients=await e.finish(await e.call("run_analysis",dict(request=dict(kind="zernike_fringe",field=1,wavelength=1,sampling="S_256x256",maximum_terms=16))))
        values=[r["value"]for r in coefficients["rows"]];residual=[]
        for ix,iy in positions:
            x=g["min_x"]+ix*g["dx"];y=g["min_y"]+iy*g["dy"]
            reconstruction=sum(a*b for a,b in zip(values,fringe16(x,y)))
            residual.append(dict(px=x,py=y,wavefront=g["values"][iy][ix],zernike_reconstruction=reconstruction))
            e.check("Fringe polynomial reconstruction waves",reconstruction,g["values"][iy][ix],atol=.002,rtol=0)
        fan=await e.finish(await e.call("run_analysis",dict(request=dict(kind="ray_fan",field=1,wavelength=1,number_of_rays=21))))
        fan_rows=[]
        chief=(await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(rays=[dict(wavelength=1)])))))["rows"][0]
        for series in fan["series"]:
            tangential=any(s in series["description"]for s in("子午","Tangential"))
            sagittal=any(s in series["description"]for s in("弧矢","Sagittal"))
            assert tangential or sagittal,series["description"]
            axis=1 if tangential else 0
            indices=[len(series["x"])//4,len(series["x"])//2,3*len(series["x"])//4]
            rays=[dict(wavelength=1,**{"py"if tangential else"px":series["x"][i]})for i in indices]
            traced=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(rays=rays))))
            for i,row in zip(indices,traced["rows"]):
                expected=(row["position"][axis]-chief["position"][axis])*1000
                observed=series["y"][i][0]
                fan_rows.append(dict(description=series["description"],pupil=series["x"][i],expected_um=expected,actual_um=observed))
                e.check("signed ray fan versus ray intercept um",observed,expected)
        if kind=="coma":
            import numpy as np
            psf=await e.finish(await e.call("run_analysis",dict(request=dict(kind="huygens_psf",field=1,wavelength=1,
                sampling="S_256x256",image_sampling="S_256x256",image_delta=2,normalize=True))))
            pg=psf["grids"][0];axis=(np.arange(256)+.5)*2/256-1
            xx,yy=axis[None,:],axis[:,None]
            # The controlled phase advances optical phase; ray OPD is its negative.
            # Signed real-ray fan above fixes local image X, independently of PSF.
            pupil=np.where(xx*xx+yy*yy<=1,np.exp(2j*np.pi*.2*xx*(xx*xx+yy*yy)),0)
            image_x=(pg["min_x"]+np.arange(pg["nx"])*pg["dx"])/1000
            image_y=(pg["min_y"]+np.arange(pg["ny"])*pg["dy"])/1000
            kx=np.exp(-2j*np.pi*image_x[:,None]*(radius*axis)[None,:]/(.00055*100))
            ky=np.exp(-2j*np.pi*image_y[:,None]*(radius*axis)[None,:]/(.00055*100))
            reference=np.abs(ky@pupil@kx.T)**2;reference/=reference.max()
            actual=np.asarray(pg["values"],dtype=float);middle=pg["ny"]//2
            error=float(np.max(np.abs(actual[middle]-reference[middle])))
            (e.folder/"coma-psf-reference.json").write_text(json.dumps(dict(max_signed_centerline_error=error,atol=.025,
                formula="abs(Fourier(exp(+i*2pi*0.2*x*(x*x+y*y))*circular_pupil))^2; physical image X from signed ray fan",
                reference_peak_x_um=float(image_x[int(np.argmax(reference[middle]))]*1000),
                actual_peak_x_um=float(image_x[int(np.argmax(actual[middle]))]*1000),
                scope="signed local image axes, scalar on-axis paraboloid, chief-ray reference"),indent=2),encoding="utf-8")
            e.check("signed coma PSF centerline scalar diffraction",error,0,atol=.025,rtol=0)
        (e.folder/"imaging-cross-reference.json").write_text(json.dumps(dict(phase=kind,coefficient_waves=.2,
            reconstruction=residual,fan=fan_rows,scope="entrance pupil, no tilt removal; Fringe first16 analytic polynomials and chief-referenced ray fan",
            remaining="chromatic/noncircular diffraction cross relations and nonzero-field full cross-validation"),ensure_ascii=False,indent=2),encoding="utf-8")
    asyncio.run(execute("imaging_cross_"+kind,work,role="fixture"))
