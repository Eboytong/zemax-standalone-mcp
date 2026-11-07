"""Installed normal-incidence ABg coefficients integrated as a BRDF reference."""
import asyncio,math,json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_abg_distribution_native():
    async def work(e):
        path=Path.home()/"Documents/Zemax/ABg_Data/ABG_DATA.DAT"
        selected=False;coefficients=None
        for line in path.read_text(encoding="ascii").splitlines():
            if line.startswith("NM "):selected=line.split()[1]=="ABG-EXAMPLE"
            if selected and line.startswith("DT 0 "):coefficients=tuple(map(float,line.split()[3:6]));break
        assert coefficients is not None
        a,b,g=coefficients;assert g==2
        tis=math.pi*a*math.log((b+1)/b);rays=3000
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=rays,Power=1,ZCosine=1)),
            dict(object=2,object_type="Rectangle",z=5,material="MIRROR",data=dict(XHalfWidth=3,YHalfWidth=3),
                faces=[dict(face=0,scatter_model="ABg",settings=dict(ReflectName="ABG-EXAMPLE"),number_of_rays=1)]),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=91,NumberAPixels=36))])
        _,segments=await trace(e,"abg",scatter_rays=True,max_segments=20000)
        hits=[r for r in segments if r["HitObject"]==3]
        angles=[math.acos(min(1,max(-1,-r["N"])))for r in hits]
        scattered=[theta for theta in angles if theta>1e-8]
        e.check("ABg total detected W",(await detector(e,3,width=91,height=36))["total_flux"],1)
        e.check("ABg total integrated scatter probability",len(scattered)/len(hits),tis,atol=6*math.sqrt(tis*(1-tis)/len(hits)),rtol=0)
        for degrees in (15,30,60):
            theta=math.radians(degrees);expected=math.log(1+math.sin(theta)**2/b)/math.log(1+1/b)
            observed=sum(v<=theta for v in scattered)/len(scattered)
            e.check("ABg conditional angular CDF "+str(degrees),observed,expected,atol=6*math.sqrt(expected*(1-expected)/len(scattered)),rtol=0)
        (e.folder/"abg_reference.json").write_text(json.dumps(dict(file=str(path),definition="ABG-EXAMPLE",a=a,b=b,g=g,
            brdf="A/(B+sin(theta)^2)",tis=tis,rays=rays,seed=42,criterion="six binomial standard errors"),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"abg.zos")))
    asyncio.run(execute("abg_distribution",work))
