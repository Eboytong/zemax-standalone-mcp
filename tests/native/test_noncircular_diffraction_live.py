"""Noncircular pupil PSF and encircled energy from independent pupil integrals."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from zemax_mcp.evaluation import interpolate


@pytest.mark.zemax
@pytest.mark.parametrize("shape", ["rectangle", "annulus"])
def test_noncircular_psf_energy_native(shape):
    async def work(e):
        import numpy as np
        await e.model()
        aperture=(dict(type="RectangularAperture",x_half_width=4,y_half_width=3)
                  if shape=="rectangle" else dict(type="CircularObscuration",maximum_radius=1.5))
        await e.call("update_surfaces",dict(changes=[dict(surface=1,aperture=aperture),
            dict(surface=2,radius=-200,conic=-1,material="MIRROR",thickness=-100,
                 semi_diameter=5,is_stop=True,replace_solves=True)]))
        psf=await e.finish(await e.call("run_analysis",dict(request=dict(kind="huygens_psf",field=1,wavelength=1,
            sampling="S_256x256",image_sampling="S_256x256",image_delta=.5,normalize=True))))
        g=psf["grids"][0];actual=np.asarray(g["values"],dtype=float)
        xs=(g["min_x"]+np.arange(g["nx"])*g["dx"])/1000
        ys=(g["min_y"]+np.arange(g["ny"])*g["dy"])/1000
        references=[];energies=[]
        for n in (256,512):
            axis=(np.arange(n)+.5)*10/n-5
            xx,yy=axis[None,:],axis[:,None]
            mask=((abs(xx)<=4)&(abs(yy)<=3) if shape=="rectangle" else
                  ((xx*xx+yy*yy<=25)&(xx*xx+yy*yy>=2.25)))
            kx=np.exp(-2j*np.pi*xs[:,None]*axis[None,:]/(.00055*100))
            ky=np.exp(-2j*np.pi*ys[:,None]*axis[None,:]/(.00055*100))
            intensity=np.abs(ky@mask.astype(float)@kx.T)**2*(10/n)**4
            references.append(intensity/intensity.max())
            # Parseval denominator includes the full image plane, not the preview window.
            total=(.00055*100)**2*float(mask.sum())*(10/n)**2
            energies.append({r:float(intensity[(xs[None,:]**2+ys[:,None]**2)<=(r/1000)**2].sum()
                              *g["dx"]*g["dy"]/1e6/total) for r in (10,20)})
        cy,cx=g["ny"]//2,g["nx"]//2
        for iy,ix in ((cy,cx),(cy,cx+4),(cy,cx+8),(cy+4,cx),(cy+8,cx)):
            e.check("pupil integral PSF refinement",float(references[0][iy,ix]),float(references[1][iy,ix]),atol=.005,rtol=0)
            e.check("noncircular signed PSF sample",float(actual[iy,ix]),float(references[1][iy,ix]),atol=.025,rtol=0)
        ee=await e.finish(await e.call("run_analysis",dict(request=dict(kind="diffraction_encircled_energy",field=1,wavelength=1,
            sampling="S_256x256",reference="ChiefRay",maximum_radius=30))))
        records=[]
        for series in ee["series"]:
            for radius in (10,20):
                expected=energies[1][radius]
                e.check("EE integral refinement",energies[0][radius],expected,atol=.005,rtol=0)
                value=interpolate(series["x"],[v[0] for v in series["y"]],radius)
                records.append(dict(radius_um=radius,expected=expected,actual=value))
                e.check("encircled energy versus pupil integral",value,expected,atol=.025,rtol=0)
        await e.call("save_lens_as",dict(path=str(e.folder/(shape+".zos"))))
        (e.folder/"noncircular-reference.json").write_text(json.dumps(dict(shape=shape,aperture=aperture,
            pupil_quadrature=[256,512],image_step_um=g["dx"],psf_atol=.025,energy_atol=.025,
            formula="abs(double integral pupil*exp(-i*2pi*(X*x+Y*y)/(lambda*f)))^2; total=(lambda*f)^2*integral(abs(pupil)^2)",
            energy=records,scope="axis-aligned uniform rectangular/annular scalar pupils, on-axis paraboloid"),indent=2),encoding="utf-8")
    asyncio.run(execute("noncircular_diffraction_"+shape,work))
