"""Finite-distance Gaussian coupling, displaced and tilted receiver references."""
import asyncio,math
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("distance,offset,tilt",[(30,0,0),(30,.03,0),(0,0,.02)])
def test_gaussian_propagation_and_receiver_native(distance,offset,tilt):
    async def work(e):
        await e.model()
        await e.call("update_surfaces",dict(changes=[dict(surface=1,thickness=distance,replace_solves=True)]))
        wavelength=.00055;w=.1;zr=math.pi*w*w/wavelength
        factor=1+(distance/(2*zr))**2
        expected=math.exp(-offset*offset/(w*w*factor))/factor
        if tilt:expected*=math.exp(-(math.pi*w*math.sin(math.radians(tilt))/wavelength)**2)
        r=await e.finish(await e.call("run_pop",dict(request=dict(beam_parameters={0:w,1:w,2:offset,3:0},
            fiber_type="GaussianWaist",fiber_parameters={0:w,1:w},fiber_tilt_y=tilt,
            x_sampling="S_256x256",y_sampling="S_256x256",x_width=2,y_width=2))))
        e.check("finite distance integrated W",r["metrics"]["integrated_power"],1,atol=5e-4)
        e.check("Gaussian overlap analytic efficiency",r["metrics"]["receiver_efficiency"],expected,atol=5e-4)
        e.check("efficiency product",r["metrics"]["total_coupling_efficiency"],r["metrics"]["receiver_efficiency"]*r["metrics"]["system_efficiency"])
        grid=r["grids"][0];mass=sum(v for row in grid["values"]for v in row if v is not None)
        xmean=sum((grid["min_x"]+ix*grid["dx"])*v for row in grid["values"]for ix,v in enumerate(row)if v is not None)/mass
        variance=sum((grid["min_x"]+ix*grid["dx"]-xmean)**2*v for row in grid["values"]for ix,v in enumerate(row)if v is not None)/mass
        e.check("propagated Gaussian radius mm",2*math.sqrt(variance),w*math.sqrt(1+(distance/zr)**2),atol=5e-4)
    asyncio.run(execute("gaussian_distance_offset_tilt",work))
