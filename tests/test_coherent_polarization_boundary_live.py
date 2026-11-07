"""Record native coherent behavior separately from vector interference suitability."""
import asyncio,json,math
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_orthogonal_jones_native_boundary():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=i,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=p,ZCosine=1,WaveNumber=1),
            sources=dict(RandomPolarization=False,Jx=1 if i==1 else 0,Jy=0 if i==1 else 1,CoherenceLength=0,InitialPhaseDeg=0))for i,p in ((1,.25),(2,.75))]+
            [dict(object=3,object_type="DetectorRectangle",z=10,material="ABSORB",data=dict(NumberXPixels=8,NumberYPixels=8,XHalfWidth=2,YHalfWidth=2),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        references=[]
        for phase in (0,90,180,270):
            await update(e,[dict(object=2,sources=dict(InitialPhaseDeg=phase))])
            await trace(e,"orthogonal_"+str(phase),use_polarization=True)
            result=await detector(e,3,kind="coherent",coherent_type="Power")
            observed=sum(sum(row)for row in result["values"])
            scalar=(1+2*math.sqrt(.25*.75)*math.cos(math.radians(phase)))/(math.sqrt(.25)+math.sqrt(.75))**2
            e.check("recorded native scalar response "+str(phase),observed,scalar)
            references.append(dict(phase_deg=phase,observed_W=observed,scalar_reference_W=scalar,
                orthogonal_vector_reference_W=1,vector_reference_passed=abs(observed-1)<1e-7))
            assert "orthogonal-Jones"in result["coherence"]["polarization_scope"]
        assert any(not row["vector_reference_passed"]for row in references)
        (e.folder/"polarization_boundary.json").write_text(json.dumps(dict(
            fixture=dict(jones=[[1,0],[0,1]],powers_W=[.25,.75],normalization=False,one_common_pixel=True),
            status="native scalar response confirmed; vector no-interference reference not passed",
            checks=references,scope="This test records a limitation; it does not validate vector interference."),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"orthogonal_jones.zos")))
    asyncio.run(execute("orthogonal_jones_native_boundary",work))
