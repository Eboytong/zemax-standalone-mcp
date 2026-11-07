"""Two sampled plane waves: signed launch phase, fringe period and visibility."""
import asyncio
import json
import math

import pytest

from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_sampled_plane_wave_interference_native():
    async def work(e):
        import numpy as np
        nx=32;pixel=.02;half=nx*pixel/2;z=10.;wavelength=.00055;period=.08
        sine=wavelength/(2*period);cosine=math.sqrt(1-sine*sine);k=2*math.pi/wavelength
        await setup(e,2*nx+1)
        changes=[];positions=[]
        for ix in range(nx):
            x=-half+(ix+.5)*pixel;positions.append(x)
            for beam,(l,power)in enumerate(((-sine,.25),(sine,.75))):
                start=x-z*l/cosine
                changes.append(dict(object=2*ix+beam+1,object_type="SourceRay",x=start,
                    data=dict(NumberOfAnalysisRays=1,Power=power/nx,XCosine=l,YCosine=0,ZCosine=cosine,WaveNumber=1),
                    sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=0,
                        InitialPhaseDeg=math.degrees(k*l*start)%360)))
        index=2*nx+1
        changes.append(dict(object=index,object_type="DetectorRectangle",z=z,material="ABSORB",
            data=dict(NumberXPixels=nx,NumberYPixels=1,XHalfWidth=half,YHalfWidth=.1,Polarization=0,Mirroring=0),
            type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False)))
        await update(e,changes)
        await trace(e,"fringes",use_polarization=True)
        data=await detector(e,index,kind="coherent",coherent_type="Power",width=nx,height=1)
        flux=await detector(e,index,width=nx,height=1)
        e.check("plane-wave incoherent total W",flux["total_flux"],1)
        values=data["values"][0];denominator=(math.sqrt(.25)+math.sqrt(.75))**2
        records=[]
        for x,actual in zip(positions,values):
            expected=(1+2*math.sqrt(.25*.75)*math.cos(2*math.pi*x/period))/(nx*denominator)
            e.check(f"plane-wave fringe pixel at {x} mm W",actual,expected)
            records.append(dict(x_mm=x,expected_W=expected,actual_W=actual))
        phase=2*math.pi*np.array(positions)/period
        design=np.stack((np.ones(nx),np.cos(phase),np.sin(phase)),axis=1)
        coefficients=np.linalg.lstsq(design,np.array(values),rcond=None)[0]
        visibility=float(math.hypot(coefficients[1],coefficients[2])/coefficients[0])
        e.check("unequal-power spatial fringe visibility",visibility,2*math.sqrt(.25*.75))
        await e.call("save_lens_as",dict(path=str(e.folder/"plane_waves.zos")))
        (e.folder/"fringe_reference.json").write_text(json.dumps(dict(wavelength_mm=wavelength,
            sine_directions=[-sine,sine],distance_mm=z,expected_period_mm=period,pixel_width_mm=pixel,
            launch_phase="InitialPhase=k*l*x_start; propagation k*z/n; detector phase difference=2*k*sin(theta)*x",
            formula="per-pixel incoherent W * (1+2*sqrt(P1*P2)*cos(delta_phi))/(sqrt(P1)+sqrt(P2))^2",
            expected_visibility=2*math.sqrt(.25*.75),fitted_visibility=visibility,
            scope="sampled common-polarization plane waves, four samples per fringe, normalization off; not arbitrary partial coherence",
            rows=records),indent=2),encoding="utf-8")
    asyncio.run(execute("spatial_plane_wave_fringes",work))
