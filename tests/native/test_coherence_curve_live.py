"""Finite-bandwidth mean phasor power with a predeclared finite-N variance."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,detector


def power_moments(mu,mu2,n):
    m=abs(mu)**2
    second=1/n+(1-1/n)*m
    fourth=(n*(2*n-1)+n*(n-1)*abs(mu2)**2+4*n*(n-1)**2*m
            +2*n*(n-1)*(n-2)*(mu2*mu.conjugate()**2).real
            +n*(n-1)*(n-2)*(n-3)*m*m)/n**4
    return second,max(0.,fourth-second*second)


@pytest.mark.zemax
def test_finite_bandwidth_power_curve_native():
    async def work(e):
        import numpy as np
        n=10000;wave=.00055;coherence=.01;band=wave*wave/coherence
        distances=(.001,.0025,.005,.0075,.01,.0125,.02)
        records=[];await setup(e,2)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=n,Power=1,ZCosine=1,WaveNumber=1),
            sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=coherence,InitialPhaseDeg=0)),
            dict(object=2,object_type="DetectorRectangle",z=.001,material="ABSORB",data=dict(NumberXPixels=1,NumberYPixels=1,XHalfWidth=1,YHalfWidth=1,Polarization=0),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        for distance in distances:
            references=[]
            for count in (32768,65536):
                wavelength=wave-band/2+(np.arange(count)+.5)*band/count
                phase=-2*np.pi*distance/wavelength
                references.append((complex(np.exp(1j*phase).mean()),complex(np.exp(2j*phase).mean())))
            mu,mu2=references[-1];expected,variance=power_moments(mu,mu2,n)
            integration_error=10*sum(abs(a-b)for a,b in zip(*references))+1e-8
            tolerance=6*math.sqrt(variance)+integration_error
            await update(e,[dict(object=2,z=distance)])
            await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(use_polarization=True,random_seed=42))))
            data=await detector(e,2,kind="coherent",coherent_type="Power",width=1,height=1)
            observed=data["values"][0][0]
            records.append(dict(path_mm=distance,expected_W=expected,variance=variance,atol=tolerance,actual_W=observed))
            (e.folder/"coherence-curve-reference.json").write_text(json.dumps(dict(rays=n,seed=42,
                mean_wavelength_mm=wave,coherence_length_mm=coherence,uniform_wavelength_bandwidth_mm=band,
                formula="E(P)=1/N+(1-1/N)|E(exp(-i*2pi*L/lambda))|^2; exact fourth phasor moment gives variance",
                criterion="six standard deviations plus independently refined quadrature allowance; no seed selection",
                scope="single-source uniform wavelength interval, scalar detector flag0; not arbitrary stochastic coherence functions",
                rows=records),indent=2),encoding="utf-8")
            e.check(f"finite bandwidth curve L={distance}mm",observed,expected,atol=tolerance,rtol=0)
        await e.call("save_lens_as",dict(path=str(e.folder/"coherence_curve.zos")))
    asyncio.run(execute("coherence_curve",work))
