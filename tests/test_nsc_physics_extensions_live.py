"""Deterministic directions and explicit statistical optical references."""
import asyncio,json,math
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_lambertian_distribution_native():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=4000,Power=1,ZCosine=1)),
            dict(object=2,object_type="Rectangle",z=5,material="MIRROR",data=dict(XHalfWidth=3,YHalfWidth=3),
                faces=[dict(face=0,scatter_model="Lambertian",number_of_rays=1,settings=dict(ScatterFraction=1))]),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=91,NumberAPixels=36))])
        _,segments=await trace(e,"lambertian",scatter_rays=True,max_segments=20000)
        hits=[r for r in segments if r["HitObject"]==3]
        assert len(hits)>=1000
        power=sum(r["Intensity"]for r in hits)
        e.check("Lambertian collected W",power,1)
        e.check("Lambertian detector W",(await detector(e,3,width=91,height=36))["total_flux"],1)
        references=[]
        for angle in (30,60):
            expected=math.sin(math.radians(angle))**2
            actual=sum(r["Intensity"]for r in hits if -r["N"]>=math.cos(math.radians(angle)))/power
            tolerance=6*math.sqrt(expected*(1-expected)/len(hits))
            e.check("Lambertian cosine hemisphere CDF "+str(angle),actual,expected,rtol=0,atol=tolerance)
            references.append(dict(angle_deg=angle,expected=expected,actual=actual,absolute_tolerance=tolerance))
        (e.folder/"statistical_reference.json").write_text(json.dumps(dict(seed=42,rays=len(hits),criterion="six binomial standard errors",cdf=references),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"lambertian.zos")))
    asyncio.run(execute("lambertian_distribution",work))


@pytest.mark.zemax
@pytest.mark.parametrize("order",[-1,0,1])
def test_diffraction_grating_direction_native(order):
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DiffractionGrating",z=5,material="MIRROR",data=dict(Radius1=0,Clear1=5,Clear2=5,Thickness=1,LinesPerMicron=.6,DiffOrder=order)),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=91,NumberAPixels=36))])
        status=await e.call("get_system_summary")
        (e.folder/"system_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
        _,segments=await trace(e,"grating")
        hit=next(r for r in segments if r["HitObject"]==3)
        e.check("grating X direction",hit["L"],0)
        # Local grating lines are parallel X; signed order controls the Y momentum.
        e.check("grating Y direction",hit["M"],order*.55*.6)
        e.check("grating reflected Z",hit["N"],-math.sqrt(1-(order*.55*.6)**2))
        e.check("ideal grating power W",hit["Intensity"],1)
        await e.call("save_lens_as",dict(path=str(e.folder/"grating.zos")))
    asyncio.run(execute("grating_order_"+str(order),work))
