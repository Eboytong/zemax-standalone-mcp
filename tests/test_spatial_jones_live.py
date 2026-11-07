"""Spatially varying polarization and phase with independent component integrals."""
import asyncio
import json
import math
import pytest
from support.native import execute
from support.numeric_reference import component_overlap,write_polarized_zbf as write_zbf


@pytest.mark.zemax
@pytest.mark.parametrize("mismatch",[False,True])
def test_spatial_jones_complex_overlap_native(mismatch):
    async def work(e):
        await e.model()
        await e.call("update_system_settings",dict(settings=dict(polarization=dict(unpolarized=False,jx=1,jy=0))))
        nx,ny=128,64;dx,dy=.01,.02;ex=[];ey=[];rx=[];ry=[]
        for iy in range(ny):
            for ix in range(nx):
                x=(ix-nx/2)*dx;y=(iy-ny/2)*dy
                a=math.exp(-(x/.12)**2-(y/.1)**2)
                phase=5*x+4*x*y+12*(x*x+y*y)
                field=a*complex(math.cos(phase),math.sin(phase))
                angle=.4+2*x
                sx=field*math.cos(angle);sy=1j*field*math.sin(angle)
                ex.append(sx);ey.append(sy)
                if mismatch:
                    rx.append(field*math.cos(angle+5*y));ry.append(-1j*field*math.sin(angle+5*y))
                else:rx.append(sx);ry.append(sy)
        source=e.folder/"spatial_source.zbf";receiver=e.folder/"spatial_receiver.zbf"
        write_zbf(source,nx,ny,dx,dy,ex,ey);write_zbf(receiver,nx,ny,dx,dy,rx,ry)
        expected=component_overlap(ex,ey,rx,ry)
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="File",beam_file=str(source),beam_parameters={},
            fiber_type="File",fiber_file=str(receiver),fiber_parameters={},use_polarization=True,ignore_fiber_polarization=False,
            x_sampling="S_128x128",y_sampling="S_64x64",x_width=nx*dx,y_width=ny*dy))))
        (e.folder/"spatial-jones-reference.json").write_text(json.dumps(dict(expected=expected,actual=result["metrics"],
            model="Gaussian envelope, quadratic curvature and spatial Jones angle=0.4+2x; component-weighted native definition",
            tolerance=.0005,scope="coincident normal planes; not oblique projection"),indent=2),encoding="utf-8")
        e.check("spatial Jones receiver overlap",result["metrics"]["receiver_efficiency"],expected,atol=.0005)
        e.check("spatial Jones output power",result["metrics"]["integrated_power"],1,atol=.0005)
        await e.call("save_lens_as",dict(path=str(e.folder/"spatial_jones.zos")))
    asyncio.run(execute("spatial_jones_"+str(mismatch),work))
