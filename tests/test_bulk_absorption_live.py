"""Catalog internal transmission and voxel absorption from independent formulas."""
import asyncio,json,math
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_catalog_absorption_and_volume_density_native():
    async def work(e):
        await setup(e,4)
        coefficients=None;internal=None;active=False
        for line in (Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF").read_text(encoding="utf-8-sig",errors="replace").splitlines():
            if line.startswith("NM "):active=line.split()[1]=="N-BK7"
            if active and line.startswith("CD "):coefficients=list(map(float,line.split()[1:7]))
            if active and line.startswith("IT ")and float(line.split()[1])==.3:internal=list(map(float,line.split()[1:4]))
        assert coefficients and internal
        wavelength,transmission,thickness=internal
        await e.call("update_system_settings",dict(settings=dict(wavelengths=[dict(wavelength_um=wavelength)])))
        n=math.sqrt(1+sum(coefficients[i]*wavelength**2/(wavelength**2-coefficients[i+1])for i in (0,2,4)))
        reflectance=((n-1)/(n+1))**2
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1),sources=dict(RandomPolarization=False,Jx=1,Jy=0)),
            dict(object=2,object_type="DetectorVolume",z=17.5,data=dict(XHalfWidth=2,YHalfWidth=2,ZHalfWidth=13.5,NumberXPixels=1,NumberYPixels=1,NumberZPixels=5)),
            dict(object=3,object_type="RectangularVolume",inside_of=2,z=5,material="N-BK7",data=dict(X1HalfWidth=2,Y1HalfWidth=2,X2HalfWidth=2,Y2HalfWidth=2,ZLength=thickness)),
            dict(object=4,object_type="DetectorRectangle",z=35,material="ABSORB",data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=4,NumberYPixels=4))])
        _,segments=await trace(e,"bulk",use_polarization=True)
        received=(await detector(e,4))["total_flux"]
        e.check("two Fresnel interfaces and catalog internal transmission W",received,(1-reflectance)**2*transmission)
        absorbed=await detector(e,2,kind="absorbed_flux",width=1,height=1,depth=5)
        density=await detector(e,2,kind="absorbed_density",width=1,height=1,depth=5)
        observed=sum(p[0][0]for p in absorbed["values"])
        e.check("bulk absorbed W",observed,(1-reflectance)*(1-transmission))
        voxel_mm3=4*4*(27/5)
        ratios=[d[0][0]/a[0][0] for a,d in zip(absorbed["values"],density["values"])if a[0][0]>1e-12]
        (e.folder/"density_reference.json").write_text(json.dumps(dict(wavelength_um=wavelength,
            catalog_internal_transmission=transmission,reference_thickness_mm=thickness,
            voxel_volume_mm3=voxel_mm3,native_density_to_absorbed_ratios=ratios,
            unit_candidates=dict(per_mm3=1/voxel_mm3,per_cm3=1000/voxel_mm3)),indent=2),encoding="utf-8")
        for ratio in ratios:e.check("absorbed density is W per cubic mm",ratio,1/voxel_mm3)
        await e.call("update_system_settings",dict(settings=dict(source_unit_prefix="Milli",analysis_unit_prefix="Micro")))
        await trace(e,"bulk_prefix",use_polarization=True)
        prefixed_abs=await detector(e,2,kind="absorbed_flux",width=1,height=1,depth=5)
        prefixed_density=await detector(e,2,kind="absorbed_density",width=1,height=1,depth=5)
        for a,d in zip(prefixed_abs["values"],prefixed_density["values"]):
            e.check("volume density uses source prefix and lens volume",d[0][0]/a[0][0],1/voxel_mm3)
        await e.call("save_lens_as",dict(path=str(e.folder/"absorption.zos")))
    asyncio.run(execute("catalog_volume_absorption",work))
