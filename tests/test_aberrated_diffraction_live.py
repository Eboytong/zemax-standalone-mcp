"""Nonzero pupil phase MTF against an independently sampled complex-pupil integral."""
import asyncio
import json
import math

import pytest

from support.native import execute
from zemax_mcp.evaluation import interpolate


def polynomial(kind,x,y):
    if kind=="spherical":return (x*x+y*y)**2,4*x*(x*x+y*y),4*y*(x*x+y*y),8*x*y
    if kind=="coma":return x*(x*x+y*y),3*x*x+y*y,2*x*y,2*y
    if kind=="astigmatism":return x*x-y*y,2*x,-2*y,0
    return x*x+y*y,2*x,2*y,0


@pytest.mark.zemax
@pytest.mark.parametrize("kind",["spherical","coma","astigmatism","defocus"])
def test_nonzero_phase_diffraction_reference_native(kind):
    async def work(e):
        import numpy as np
        await e.model()
        coefficient=.2;radius=5.;focal_length=100.;wavelength=.00055
        path=e.folder/(kind+".dat");lines=["65 65 0.25 0.25 0"]
        for iy in range(65):
            for ix in range(65):
                p,px,py,pxy=polynomial(kind,(ix-32)*.25/radius,(32-iy)*.25/radius)
                lines.append(" ".join(map(str,(2*math.pi*coefficient*p,2*math.pi*coefficient*px/radius,
                    2*math.pi*coefficient*py/radius,2*math.pi*coefficient*pxy/radius**2))))
        path.write_text("\n".join(lines),encoding="ascii")
        await e.call("update_surfaces",dict(changes=[
            dict(surface=1,surface_type="GridPhase",import_file=str(path),replace_solves=True),
            dict(surface=2,radius=-200,conic=-1,material="MIRROR",thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        await e.call("save_lens_as",dict(path=str(e.folder/(kind+".zos"))))
        n=1024;axis=(np.arange(n)+.5)*2/n-1
        x=axis[None,:];y=axis[:,None];mask=x*x+y*y<=1
        phase=polynomial(kind,x,y)[0]*2*math.pi*coefficient
        denominator=float(mask.sum());references=[]
        result=await e.finish(await e.call("run_analysis",dict(request=dict(kind="huygens_mtf",field=1,wavelength=1,
            sampling="S_256x256",image_sampling="S_512x512",maximum_frequency=50))))
        for series in result["series"]:
            for column,label in enumerate(series["labels"]):
                assert label in {"Tangential","Sagittal","子午","弧矢"},label
                for frequency in (10,25,50):
                    separation=frequency*wavelength*focal_length/radius
                    sx,sy=(0,separation)if label in {"Tangential","子午"}else(separation,0)
                    shifted=(x-sx)**2+(y-sy)**2<=1
                    delta=phase-polynomial(kind,x-sx,y-sy)[0]*2*math.pi*coefficient
                    expected=float(abs(np.exp(1j*delta)[mask&shifted].sum())/denominator)
                    observed=interpolate(series["x"],[row[column]for row in series["y"]],frequency)
                    e.check(f"{kind} complex pupil MTF {label} {frequency} cycles/mm",observed,expected,atol=.02)
                    references.append(dict(label=label,frequency_cycles_mm=frequency,expected=expected,actual=observed))
        # Even phase models have no unresolved image-axis reversal. Coma PSF
        # orientation requires a separate signed-coordinate reference.
        if kind!="coma":
            psf=await e.finish(await e.call("run_analysis",dict(request=dict(kind="huygens_psf",field=1,wavelength=1,
                sampling="S_256x256",image_sampling="S_256x256",image_delta=2,normalize=True))))
            g=psf["grids"][0]
            image_x=(g["min_x"]+np.arange(g["nx"])*g["dx"])/1000
            image_y=(g["min_y"]+np.arange(g["ny"])*g["dy"])/1000
            quadrature=256;u=(np.arange(quadrature)+.5)*2/quadrature-1
            xx=u[None,:];yy=u[:,None]
            pupil=np.where(xx*xx+yy*yy<=1,np.exp(2j*np.pi*coefficient*polynomial(kind,xx,yy)[0]),0)
            kx=np.exp(-2j*np.pi*image_x[:,None]*(radius*u)[None,:]/(wavelength*focal_length))
            ky=np.exp(-2j*np.pi*image_y[:,None]*(radius*u)[None,:]/(wavelength*focal_length))
            reference=np.abs(ky@pupil@kx.T)**2;reference/=reference.max()
            actual=np.array([[0 if v is None else v for v in row]for row in g["values"]])
            cy,cx=g["ny"]//2,g["nx"]//2
            for iy,ix in ((cy,cx),(cy,cx+2),(cy,cx+5),(cy+2,cx),(cy+5,cx)):
                e.check(f"{kind} PSF scalar diffraction [{iy},{ix}]",float(actual[iy,ix]),float(reference[iy,ix]),atol=.025)
            disk=image_y[:,None]**2+image_x[None,:]**2<(.02)**2
            e.check(f"{kind} PSF integrated energy inside 20 um",float(actual[disk].sum()/actual.sum()),
                float(reference[disk].sum()/reference.sum()),atol=.025)
        (e.folder/"complex_pupil_reference.json").write_text(json.dumps(dict(
            phase=kind,coefficient_waves=coefficient,pupil_radius_mm=radius,wavelength_mm=wavelength,
            image_focal_length_mm=focal_length,reference_grid=n,
            formula="abs integral P(u)*conj(P(u-shift)) / integral abs(P(u))^2; shift=f*lambda*focal_length/radius",
            scope="scalar on-axis paraboloid, controlled nonzero GridPhase; finite sampling tolerance 0.02 MTF",
            checks=references),indent=2),encoding="utf-8")
    asyncio.run(execute("diffraction_phase_"+kind,work))
