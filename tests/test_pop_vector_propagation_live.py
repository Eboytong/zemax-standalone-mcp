"""Finite-distance spatial Jones field versus an independent Fresnel integral."""
import asyncio
import json
import math
import pytest
from support.native import execute
from support.numeric_reference import component_overlap,write_polarized_zbf as write_zbf


@pytest.mark.zemax
@pytest.mark.parametrize("tilt",[-.02,.02])
def test_finite_distance_vector_field_native(tilt):
    async def work(e):
        import numpy as np
        await e.model();distance=10.;wavelength=.00055;n=256;step=.005;width=n*step
        await e.call("update_system_settings",dict(settings=dict(polarization=dict(unpolarized=False,jx=1,jy=0))))
        await e.call("update_surfaces",dict(changes=[dict(surface=1,thickness=distance,replace_solves=True)]))
        axis=(np.arange(n)-n/2)*step;x,y=axis[None,:],axis[:,None]
        amplitude=np.exp(-(x/.12)**2-(y/.1)**2);phase=8*x+15*(x*x+y*y)
        base=amplitude*np.exp(1j*phase);angle=.4+2*x
        ex=base*np.cos(angle);ey=1j*base*np.sin(angle)
        receiver=np.exp(-((x-.025)/.12)**2-(y/.1)**2)
        rx=receiver*np.cos(.4);ry=1j*receiver*np.sin(.4)
        source=e.folder/"source.zbf";fiber=e.folder/"receiver.zbf"
        write_zbf(source,n,n,step,step,ex.ravel(),ey.ravel());write_zbf(fiber,n,n,step,step,rx.ravel(),ry.ravel())
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="File",beam_file=str(source),beam_parameters={},
            fiber_type="File",fiber_file=str(fiber),fiber_parameters={},fiber_tilt_y=tilt,
            use_polarization=True,ignore_fiber_polarization=False,
            x_sampling="S_256x256",y_sampling="S_256x256",x_width=width,y_width=width))))
        g=result["grids"][0];ox=g["min_x"]+np.arange(g["nx"])*g["dx"];oy=g["min_y"]+np.arange(g["ny"])*g["dy"]
        # Stored POP phase is wavefront advance, positive towards +Z (manual20606).
        # It is the conjugate of the exp(+ikz) field used in the Fourier derivation.
        # Thus native_out = conj(Fresnel(conj(native_in))); a positive phase
        # gradient has negative physical ray slope, independently testable below.
        q=np.exp(-1j*math.pi*(x*x+y*y)/(wavelength*distance))
        kx=np.exp(2j*math.pi*ox[:,None]*axis[None,:]/(wavelength*distance))
        ky=np.exp(2j*math.pi*oy[:,None]*axis[None,:]/(wavelength*distance))
        curvature=np.exp(-1j*math.pi*(ox[None,:]**2+oy[:,None]**2)/(wavelength*distance))
        propagated=[curvature*(ky@(field*q)@kx.T)*step**2/(-1j*wavelength*distance)for field in(ex,ey)]
        # Receiver is explicitly described at the end plane, including displacement.
        mode=np.exp(-((ox[None,:]-.025)/.12)**2-(oy[:,None]/.1)**2)
        mode=mode*np.exp(-2j*math.pi*math.sin(math.radians(tilt))*ox[None,:]/wavelength)
        receiver_fields=[mode*np.cos(.4),1j*mode*np.sin(.4)]
        expected=component_overlap(*(v.ravel()for v in propagated+receiver_fields))
        intensity=sum(abs(v)**2 for v in propagated);intensity/=intensity.sum()*g["dx"]*g["dy"]
        actual=np.asarray(g["values"],dtype=float)
        error=float(np.max(abs(actual/intensity.max()-intensity/intensity.max())))
        record=dict(distance_mm=distance,receiver_offset_mm=.025,receiver_tilt_y_deg=tilt,
            expected_coupling=expected,actual_metrics=result["metrics"],max_normalized_irradiance_error=error,
            tolerances=dict(coupling_absolute=.005,normalized_irradiance=.005),
            formula="native_out=conj(Fresnel(conj(native_in))); native positive phase is +Z wavefront advance; component-power-weighted overlaps",
            scope="slow diffracting field; native receiver tilt is linear phase, not physical oblique-endface projection",
            manual_lines=[20425,20475,20495,20606,20618,21138,21140,21356])
        (e.folder/"vector-propagation-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        e.check("propagated spatial Jones irradiance",error,0,atol=.005,rtol=0)
        centroid=float((actual*ox[None,:]).sum()/actual.sum())
        e.check("signed phase-gradient centroid mm",centroid,-distance*wavelength*8/(2*math.pi),atol=1e-6,rtol=0)
        e.check("propagated spatial Jones receiver overlap",result["metrics"]["receiver_efficiency"],expected,atol=.005,rtol=0)
        await e.call("save_lens_as",dict(path=str(e.folder/"vector_propagation.zos")))
    asyncio.run(execute("vector_propagation_"+str(tilt),work))
