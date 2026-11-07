"""Unequal-power coherent sums with independent source phase and path length."""
import asyncio,math,json
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_unequal_power_path_coherence_native():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=i,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=p,ZCosine=1,WaveNumber=1),
            sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=0,InitialPhaseDeg=0))for i,p in ((1,.25),(2,.75))]+
            [dict(object=3,object_type="DetectorRectangle",z=10,material="ABSORB",data=dict(NumberXPixels=8,NumberYPixels=8,XHalfWidth=2,YHalfWidth=2),type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        denominator=(math.sqrt(.25)+math.sqrt(.75))**2
        for displacement,initial_phase in [(0,p)for p in range(0,361,30)]+[(.00055/4,0),(.00055/4,90)]:
            await update(e,[dict(object=2,z=displacement,sources=dict(InitialPhaseDeg=initial_phase))])
            await trace(e,"coherent_"+str(len(e.checks)),use_polarization=True)
            r=await detector(e,3,kind="coherent",coherent_type="Power")
            power=sum(sum(row)for row in r["values"])
            phase=2*math.pi*displacement/.00055-math.radians(initial_phase)
            expected=(1+2*math.sqrt(.25*.75)*math.cos(phase))/denominator
            e.check("unequal-power phase/path coherent W",power,expected)
        await e.call("save_lens_as",dict(path=str(e.folder/"unequal_coherence.zos")))
    asyncio.run(execute("unequal_coherent_path",work))
