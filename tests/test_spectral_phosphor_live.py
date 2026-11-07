"""Installed spectrum resources and bounded photoluminescence references."""
import asyncio,json,math
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_uniform_source_spectrum_native():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1000,Power=1,ZCosine=1),
            spectrum=dict(mode="UniformPowerSpectrum",settings=dict(WavelengthFrom=.45,WavelengthTo=.65,SpectrumCount=3))),
            dict(object=2,object_type="DetectorPolar",material="ABSORB",data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=91,NumberAPixels=36))])
        _,segments=await trace(e,"spectrum",max_segments=10000)
        hits=[r for r in segments if r["HitObject"]==2]
        e.check("uniform spectrum total W",sum(r["Intensity"]for r in hits),1)
        wavelengths=[r["WlUM"]for r in hits]
        assert all(min(abs(w-v)for v in (.45,.55,.65))<1e-7 for w in wavelengths)
        expected=.55;observed=sum(r["WlUM"]*r["Intensity"]for r in hits)
        e.check("uniform three-bin weighted mean um",observed,expected,atol=6*.1/math.sqrt(len(hits)),rtol=0)
        await e.call("save_lens_as",dict(path=str(e.folder/"uniform_spectrum.zos")))
    asyncio.run(execute("uniform_spectrum",work))


@pytest.mark.zemax
def test_installed_phosphor_reference_native():
    async def work(e):
        await setup(e,3)
        await e.call("update_system_settings",dict(settings=dict(wavelengths=[dict(wavelength_um=.47)])))
        root=Path.home()/"Documents/Zemax/Objects/Phosphors and Fluorescence Files"
        for name in ("_sample_3.ZAS","_sample_3.ZES","_sample_3.zqe"):assert (root/name).is_file()
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=500,Power=1,ZCosine=1)),
            dict(object=2,object_type="RectangularVolume",z=5,material="N-BK7",
                data=dict(X1HalfWidth=3,Y1HalfWidth=3,X2HalfWidth=3,Y2HalfWidth=3,ZLength=.1),
                volume=dict(model="PhotoluminescenceModel",settings=dict(BasicAlgorithm=False,
                    AbsorptionFile="_sample_3.ZAS",EmissionFile="_sample_3.ZES",QuantumYield="_sample_3.zqe",
                    EfficiencySpectrum="QuantumYield",ExtinctionCoefficient=1e5,ExtinctionWavelength=.47,
                    PLDensity=3.1e17,ConsiderMieScattering=False))),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=91,NumberAPixels=36))])
        objects=await e.call("get_nsc_objects",dict(request={}))
        assert objects["rows"][1]["volume"]["settings"]["AreSettingsValid"]
        _,segments=await trace(e,"phosphor",scatter_rays=True,max_segments=30000)
        hits=[r for r in segments if r["HitObject"]==3]
        total=sum(r["Intensity"]for r in hits)
        assert 0<total<=1+1e-7
        shifted=[r["WlUM"]for r in hits if r["WlUM"]>.471]
        limitations=[]
        if shifted:
            assert min(shifted)>=.5-1e-7 and max(shifted)<=.751
        else:limitations.append("ZRD WlUM未提供可确认的转换后逐段波长；未完成发射谱数值验收")
        (e.folder/"phosphor_reference.json").write_text(json.dumps(dict(
            resource_files=[str(root/name)for name in ("_sample_3.ZAS","_sample_3.ZES","_sample_3.zqe")],
            excitation_um=.47,observed_output_power=total,observed_shifted_wavelengths=shifted,
            numerical_scope="validity, passive energy bound and observed spectral support only",
            pending=["quantum-yield energy conversion statistics","emission distribution numerical integration"]+limitations),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"phosphor.zos")))
    asyncio.run(execute("phosphor_installed_resource",work))
