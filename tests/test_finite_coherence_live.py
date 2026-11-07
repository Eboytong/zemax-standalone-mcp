"""A documented uniform wavelength interval gives a statistical coherence bound."""
import asyncio,math,json
import pytest
from support.native import execute
from support.nsc import setup,update,detector


@pytest.mark.zemax
def test_finite_coherence_degradation_bound_native():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=4000,Power=1,ZCosine=1,WaveNumber=1),
            sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=0,InitialPhaseDeg=0)),
            dict(object=2,object_type="DetectorRectangle",z=10,material="ABSORB",data=dict(NumberXPixels=8,NumberYPixels=8,XHalfWidth=2,YHalfWidth=2),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        values=[]
        for length,name in ((0,"monochromatic"),(.01,"finite")):
            await update(e,[dict(object=1,sources=dict(CoherenceLength=length))])
            await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(use_polarization=True,random_seed=42,save_zrd=str(e.folder/(name+".zrd"))))))
            result=await detector(e,2,kind="coherent",coherent_type="Power")
            values.append(sum(sum(row)for row in result["values"]))
        e.check("monochromatic coherent power W",values[0],1)
        wave=.00055;bandwidth=wave*wave/.01
        def mean(n):
            re=im=0.
            for i in range(n):
                wavelength=wave-bandwidth/2+(i+.5)*bandwidth/n
                phase=-2*math.pi*10/wavelength;re+=math.cos(phase);im+=math.sin(phase)
            return complex(re/n,im/n)
        low,high=mean(131072),mean(262144);allowance=10*abs(low-high)+1e-8
        expected_mean_upper=1/4000+(1-1/4000)*(abs(high)+allowance)**2
        bound=100*expected_mean_upper
        e.check("99-percent Markov bound excess W",max(0,values[1]-bound),0)
        (e.folder/"coherence_reference.json").write_text(json.dumps(dict(
            rays=4000,seed=42,path_mm=10,coherence_length_mm=.01,wavelength_mm=wave,
            uniform_bandwidth_mm=bandwidth,mean_field=[high.real,high.imag],quadrature_allowance=allowance,
            expected_mean_power_upper=expected_mean_upper,observed_power_W=values[1],bound_W=bound,
            criterion="Markov tail probability <=0.01 under independent uniform wavelength sampling",
            scope="degradation bound; no precise visibility-curve or arbitrary coherence-function claim"),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"finite_coherence.zos")))
    asyncio.run(execute("finite_coherence_statistical_bound",work))
