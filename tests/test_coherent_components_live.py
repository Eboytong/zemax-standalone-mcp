"""Detector Polarization=0 is scalar; local X/Y selectors resolve orthogonal inputs."""
import asyncio
import json

import pytest

from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_orthogonal_jones_component_selectors_native():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=i,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=p,ZCosine=1,WaveNumber=1),
            sources=dict(RandomPolarization=False,Jx=int(i==1),Jy=int(i==2),CoherenceLength=0,InitialPhaseDeg=0))for i,p in ((1,.25),(2,.75))]+
            [dict(object=3,object_type="DetectorRectangle",z=10,material="ABSORB",
                data=dict(NumberXPixels=8,NumberYPixels=8,XHalfWidth=2,YHalfWidth=2,Polarization=0),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        rows=[]
        for phase in (0,90,180,270):
            await update(e,[dict(object=2,sources=dict(InitialPhaseDeg=phase))])
            components=[]
            for flag,expected in ((1,.25),(2,.75)):
                await update(e,[dict(object=3,data=dict(Polarization=flag))])
                await trace(e,f"component_{phase}_{flag}",use_polarization=True)
                result=await detector(e,3,kind="coherent",coherent_type="Power")
                assert result["coherence"]["polarization_flag"]==flag
                actual=sum(v for row in result["values"]for v in row if v is not None)
                e.check(f"orthogonal Jones phase {phase} flag {flag} W",actual,expected)
                components.append(actual)
            e.check("independent orthogonal component sum W",sum(components),1)
            rows.append(dict(phase_deg=phase,x_W=components[0],y_W=components[1],sum_W=sum(components)))
        (e.folder/"component_reference.json").write_text(json.dumps(dict(
            source="manual Detector Rectangle parameter 16, lines 14132 and 14229-14237",
            definition="flag 0 uses scalar intensity/geometric phase; flags 1 and 2 select electric-field components",
            scope="two orthogonal axial SourceRays, one common pixel, normalization off; component sums from separate cleared traces",
            rows=rows),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"component_selectors.zos")))
    asyncio.run(execute("coherent_component_selectors",work))
