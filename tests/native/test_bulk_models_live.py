"""Controlled single-scattering and installed DLL models with explicit statistics."""
import asyncio,math,json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
@pytest.mark.parametrize("mode",["AngleScattering","DLLDefinedScattering"])
def test_bulk_scattering_reference_native(mode):
    async def work(e):
        await setup(e,3)
        settings=dict(MeanPath=2,Angle=10)
        extra={}
        if mode=="DLLDefinedScattering":settings["DLL"]="bulk_samp_1.DLL";extra["parameters"]={0:1}
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1500,Power=1,ZCosine=1)),
            dict(object=2,object_type="RectangularVolume",z=5,material="N-BK7",data=dict(X1HalfWidth=20,Y1HalfWidth=20,X2HalfWidth=20,Y2HalfWidth=20,ZLength=1),volume=dict(model=mode,settings=settings,**extra)),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=50,NumberPPixels=91,NumberAPixels=36))])
        _,segments=await trace(e,"bulk",scatter_rays=True,max_segments=30000)
        flux=await detector(e,3,width=91,height=36)
        assert .99<flux["total_flux"]<=1+1e-8
        hits=[r for r in segments if r["HitObject"]==3]
        assert len(hits)==1500
        scattered=[r for r in hits if math.hypot(r["L"],r["M"])>1e-10]
        expected=1-math.exp(-.5);fraction=len(scattered)/len(hits)
        e.check("probability of at least one bulk event",fraction,expected,rtol=0,atol=6*math.sqrt(expected*(1-expected)/len(hits)))
        reference=dict(model=mode,seed=42,rays=1500,mean_path_mm=2,axial_path_mm=1,
            expected_scatter_probability=expected,observed_fraction=fraction,criterion="six binomial standard errors",
            detected_W=flux["total_flux"],power_scope="passive bound; bulk glass attenuation not assigned to scattering",
            angular_distribution_status="multiple-event outgoing angles not used as a single-event distribution")
        (e.folder/"bulk_reference.json").write_text(json.dumps(reference,indent=2),encoding="utf-8")
        path=str(e.folder/"bulk.zos")
        await e.call("save_lens_as",dict(path=path));await e.call("open_lens",dict(path=path))
        obj=(await e.call("get_nsc_objects",dict(request={})))["rows"][1]
        assert obj["volume"]["model"]==mode
        e.check("persisted bulk path mm",obj["volume"]["settings"]["MeanPath"],2)
        if extra:e.check("persisted DLL parameter",obj["volume"]["parameters"][0]["value"],1)
    asyncio.run(execute("bulk_model_"+mode,work))
