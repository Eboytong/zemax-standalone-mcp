"""DetectorColor against an independent, officially published CIE 1931 table."""
import asyncio
import json
import pytest
from tests.support.native import execute
from tests.support.nsc import setup, update, detector
from tests.support.numeric_reference import cie_xyz, chromaticities


SPECTRA = {
    "450": [(450, 1.)], "550": [(550, 1.)], "650": [(650, 1.)],
    "combination": [(450, .2), (550, .5), (650, .3)],
    "visible_comb": [(nm, 1/48) for nm in range(360, 831, 10)],
    "flat_visible_trapezoid": [(nm, (.5 if nm in (360,830) else 1)/94) for nm in range(360,831,5)],
}


@pytest.mark.zemax
@pytest.mark.parametrize("name", list(SPECTRA))
def test_cie_integrated_spectrum_native(name):
    async def work(e):
        spectrum=SPECTRA[name]
        n=max(i for i in range(1,17) if len(spectrum)%i==0)
        await setup(e,n+1)
        await e.call("update_system_settings",dict(settings=dict(
            source_units="Watts",source_unit_prefix="None",analysis_units="WattsPerMMSq",analysis_unit_prefix="None")))
        await update(e,[dict(object=i+1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=spectrum[i][1],ZCosine=1))for i in range(n)]+[dict(object=n+1,object_type="DetectorColor",z=10,material="ABSORB",
            data=dict(XHalfWidth=.5,YHalfWidth=.5,NumberXPixels=1,NumberYPixels=1),type_settings=dict(UsePixelInterpolation=False))
        ])
        for start in range(0,len(spectrum),n):
            chunk=spectrum[start:start+n]
            assert len(chunk)==n
            await e.call("update_system_settings",dict(settings=dict(wavelengths=[dict(wavelength_um=nm/1000)for nm,_ in chunk])))
            await update(e,[dict(object=i+1,data=dict(Power=chunk[i][1],WaveNumber=i+1))for i in range(n)])
            await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42,detector_policy="clear"if start==0 else"accumulate"))))
        expected=cie_xyz(spectrum);channels={}
        for channel in ("radiometric_flux","photometric_flux","tristimulus_x","tristimulus_y","tristimulus_z","chromaticity_x","chromaticity_y","u_prime","v_prime"):
            r=await detector(e,n+1,color_channel=channel,width=1,height=1);channels[channel]=r["values"][0][0]
        record=dict(spectrum_nm_integrated_W=spectrum,expected_xyz=expected,actual=channels,
            reference="CIE 018:2019 Table6, DOI10.25039/CIE.DS.xvudnb9b; XYZ=683*sum(power_W*CMF)",
            budget=dict(relative_xyz=.003,absolute_chromaticity=.001,reason="independent 1nm standard data versus installed native color table interpolation; wavelengths lie on integer nm"))
        if name=="flat_visible_trapezoid":
            refined=cie_xyz([(nm,(.5 if nm in(360,830) else 1)/470)for nm in range(360,831)])
            record["flat_spectrum_refinement"]=dict(coarse_step_nm=5,fine_step_nm=1,fine_xyz=refined,rtol=.001)
            for coarse,fine in zip(expected,refined):e.check("visible integral 5nm to1nm refinement",coarse,fine,rtol=.001)
        (e.folder/"cie-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        e.check("radiometric integrated W",channels["radiometric_flux"],sum(p for _,p in spectrum))
        for axis,value in zip("xyz",expected):e.check("independent CIE "+axis,channels["tristimulus_"+axis],value,rtol=.003,atol=1e-5)
        e.check("photometric integrated lumens",channels["photometric_flux"],expected[1],rtol=.003,atol=1e-5)
        for key,value in chromaticities(expected).items():e.check("independent "+key,channels[key],value,atol=.001,rtol=0)
        await e.call("save_lens_as",dict(path=str(e.folder/"cie.zos")))
    asyncio.run(execute("cie_integral_"+name,work))
