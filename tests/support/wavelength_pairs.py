"""Matched local-medium fixtures and independent per-hit wavelength references."""
import json
import math
from pathlib import Path

from support.nsc import setup, update

WAVES=[.4375,.5,.515625,.5625,.625,.6875,.75]
TYPES=["DetectorPolar","DetectorRectangle","DetectorColor"]


def coefficients():
    catalog=Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF"
    selected=False
    for line in catalog.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if line.startswith("NM "):selected=line.split()[1]=="N-BK7"
        if selected and line.startswith("CD "):return catalog,list(map(float,line.split()[1:7]))
    raise AssertionError("official N-BK7 Sellmeier coefficients missing")


async def model(e,kind,converted):
    if kind=="DetectorPolar"and converted:
        spec=json.loads((Path(__file__).parents[1]/"reference_data/wavelength-filter.json").read_text(encoding="utf-8"))
        fixture=Path(spec["fluorescence_fixture"]).resolve()
        await e.call("open_lens",dict(path=str(fixture/"dilute_fluorescence.zos")))
        return fixture/"fluorescence.zrd",str(fixture/"dilute_fluorescence.zos"),True
    await setup(e,10)
    await e.call("update_system_settings",dict(settings=dict(
        wavelengths=[dict(wavelength_um=w)for w in ([.47]if converted else WAVES)],
        source_units="Watts",source_unit_prefix="None",analysis_units="WattsPerMMSq",analysis_unit_prefix="None")))
    volume=dict(object=1,object_type="RectangularVolume",z=-50,material="N-BK7",
        data=dict(X1HalfWidth=50,Y1HalfWidth=50,X2HalfWidth=50,Y2HalfWidth=50,ZLength=100))
    if converted:
        volume["volume"]=dict(model="PhotoluminescenceModel",settings=dict(BasicAlgorithm=False,
            AbsorptionFile="_sample_3.ZAS",EmissionFile="_sample_3.ZES",QuantumYield="_sample_3.zqe",
            EfficiencySpectrum="QuantumYield",ExtinctionCoefficient=1e5,ExtinctionWavelength=.47,
            PLDensity=1e14,ConsiderMieScattering=False))
    detector=dict(object=3,object_type=kind,inside_of=1,material="ABSORB")
    if kind=="DetectorPolar":
        detector["data"]=dict(MaxAngle=180,RadialSize=1,NumberPPixels=91,NumberAPixels=36)
    else:
        detector.update(z=1,data=dict(XHalfWidth=5,YHalfWidth=5,NumberXPixels=1,NumberYPixels=1),
                        type_settings=dict(UsePixelInterpolation=False))
        if kind=="DetectorColor":
            detector["type_settings"].update(RecordSpectralData=True,NumberOfSpectralData=81,
                SpectralDataMinWave=.4,SpectralDataMaxWave=.8)
    sources=[dict(object=2,object_type="SourceRay",inside_of=1,
        data=dict(NumberOfAnalysisRays=100000,Power=1,ZCosine=1,WaveNumber=1))] if converted else [
        dict(object=number,object_type="SourceRay",inside_of=1,x=i/100,
             data=dict(NumberOfAnalysisRays=1,Power=(i+1)/10,ZCosine=1,WaveNumber=i+1))
        for i,number in enumerate((2,4,5,6,7,8,9))]
    unused=[dict(object=i,object_type="NullObject")for i in range(4,10)]if converted else []
    # The target plane lies wholly inside this absorber. It cannot remove a ray
    # that would reach the target first, and prevents outer-glass TIR trapping.
    guard=dict(object=10,object_type="DetectorPolar",inside_of=1,material="ABSORB",
        data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=11,NumberAPixels=12))
    await update(e,[volume,*sources,*unused,detector,guard])
    baseline=e.folder/"model.zos"
    await e.call("save_lens_as",dict(path=str(baseline)))
    zrd=e.folder/"rays.zrd"
    await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,scatter_rays=converted))))
    return zrd,str(baseline),False


async def hits(e,zrd,expression):
    collected=[];next_read={};pages=[]
    for _ in range(20):
        result=await e.finish(await e.call("read_zrd",dict(request=dict(path=str(zrd),filter=expression,max_segments=100000,**next_read))))
        summary=result["summary"]
        assert summary["actual_filter"]==expression
        pages.append(summary)
        for row in result["rows"]:
            if row["HitObject"]==3:
                collected.append(dict(ray=int(row["RayNumber"]),segment=int(row["segment_index"]),
                    wave_header=float(row["WlUM"]),power_W=float(row["Intensity"]),index=float(row["Index"]),
                    path_lu=float(row["OpticalPathLU"]),path_w=float(row["OpticalPathW"]),inside=int(row["InsideOf"])))
        next_read=summary["next_read"]
        if next_read is None:break
    else:raise AssertionError("native hit collection did not reach the end")
    return collected,pages


def reference(rows,converted,coeff):
    refs=[];invalid=[];errors=[]
    for row in rows:
        if row["inside"]!=1 or row["path_lu"]<=0 or row["path_w"]<=0:
            invalid.append(dict(ray=row["ray"],segment=row["segment"],reason="non-positive optical path or non-uniform inside medium"));continue
        wave=1000*row["path_lu"]/row["path_w"] if converted else row["wave_header"]
        l2=wave*wave
        index=math.sqrt(1+sum(coeff[i]*l2/(l2-coeff[i+1])for i in(0,2,4)))
        error=abs(row["index"]-index);errors.append(error)
        if error>2e-7:
            invalid.append(dict(ray=row["ray"],segment=row["segment"],reason="independent Sellmeier mismatch",error=error));continue
        if not converted and wave not in WAVES:
            invalid.append(dict(ray=row["ray"],segment=row["segment"],reason="unexpected fixed wavelength",wavelength_um=wave));continue
        refs.append(dict(**row,wavelength_um=wave,reference_index=index,index_error=error))
    return refs,invalid,max(errors,default=0.)
