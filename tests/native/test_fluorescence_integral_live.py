"""Installed sample_3 photon spectrum, Stokes energy and wavelength-filtered ZRD."""
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup, update, detector


@pytest.mark.zemax
@pytest.mark.parametrize("criterion",["total_energy","spectrum"])
def test_sample3_fluorescence_photon_energy_native(criterion):
    spectral_failures=[]
    async def work(e):
        import numpy as np
        root=Path.home()/"Documents/Zemax/Objects/Phosphors and Fluorescence Files"
        lines=[s for s in (root/"_sample_3.ZES").read_text().splitlines() if s.strip() and not s.startswith("!")]
        assert lines[0].split()==["1000","1","1"]
        spectrum=np.array([list(map(float,l.split())) for l in lines[2:]])
        x,y=spectrum[:,0],spectrum[:,1]
        norm=float(np.trapezoid(y,x));density=1e14;extinction=1e5;radius=1.;n=100000
        excitation=470.;mu=math.log(10)*extinction*density*100/6.02214076e23
        probability=-math.expm1(-mu*radius)
        # Dilute, enclosing detector inside the same material: no exit interfaces.
        # Additional emission absorption is bounded below, not silently omitted.
        budget=dict(seed=42,rays=n,mean_absorbed_fraction=probability,absolute_power_allowance=2e-5,
                    basis="six Bernoulli standard errors plus allowance for weak reabsorption, catalog absorption and spectral interpolation")
        await setup(e,3)
        await e.call("update_system_settings",dict(settings=dict(wavelengths=[dict(wavelength_um=.47)],source_units="Watts",source_unit_prefix="None")))
        await update(e,[dict(object=1,object_type="RectangularVolume",z=-50,material="N-BK7",
                data=dict(X1HalfWidth=50,Y1HalfWidth=50,X2HalfWidth=50,Y2HalfWidth=50,ZLength=100),
                volume=dict(model="PhotoluminescenceModel",settings=dict(BasicAlgorithm=False,
                    AbsorptionFile="_sample_3.ZAS",EmissionFile="_sample_3.ZES",QuantumYield="_sample_3.zqe",
                    EfficiencySpectrum="QuantumYield",ExtinctionCoefficient=extinction,ExtinctionWavelength=.47,
                    PLDensity=density,ConsiderMieScattering=False))),
            dict(object=2,object_type="SourceRay",inside_of=1,data=dict(NumberOfAnalysisRays=n,Power=1,ZCosine=1)),
            dict(object=3,object_type="DetectorPolar",inside_of=1,material="ABSORB",data=dict(MaxAngle=180,RadialSize=radius,NumberPPixels=91,NumberAPixels=36))])
        zrd=e.folder/"fluorescence.zrd"
        await e.call("save_lens_as",dict(path=str(e.folder/"dilute_fluorescence.zos")))
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),scatter_rays=True,random_seed=42))))
        flux=await detector(e,3,width=91,height=36)
        records=[]
        # W tests source wavelength. X_WAVERANGE tests wavelength at the detector.
        for lower,upper in zip(range(500,750,25),range(525,751,25)):
            filt=f"X_WAVERANGE(3,{lower/1000},{upper/1000-1e-12})"
            data=await e.finish(await e.call("read_zrd",dict(request=dict(path=str(zrd),filter=filt,max_segments=10000))))
            assert not data["summary"]["truncated"],"increase bounded reads before interpreting a partial spectrum"
            hits=[r for r in data["rows"]if r["HitObject"]==3]
            assert len({r["RayNumber"]for r in hits})==len(hits),"branch count requires an independent multiplicity model"
            grid=np.linspace(lower,upper,1001);pdf=np.interp(grid,x,y)/norm
            q=float(np.trapezoid(pdf,grid));energy=float(np.trapezoid(pdf*excitation/grid,grid))
            second=float(np.trapezoid(pdf*(excitation/grid)**2,grid))
            observed=sum(r["Intensity"]for r in hits)
            allowed=6*math.sqrt(max(0,probability*second-(probability*energy)**2)/n)+2e-5
            records.append(dict(lower_nm=lower,upper_nm=upper,hits=len(hits),actual_W=observed,
                                expected_W=probability*energy,atol_W=allowed,expected_photon_fraction=probability*q))
        record=dict(reference_files=[str(root/name)for name in ("_sample_3.ZAS","_sample_3.ZES","_sample_3.zqe")],
            budget=budget,mu_per_mm=mu,emission=records,total_detected_W=flux["total_flux"],
            formula="mu=ln(10)*epsilon*(density/NA)*100 per mm; Iout=Iabsorbed*Q*lambda_in/lambda_out; ZES is photon density",
            wavelength_path="X_WAVERANGE(object,a,b) in micrometers at detector; WlUM retained as source-header wavelength",
            scope="dilute PL, Q=1, 1mm enclosing detector in uniform N-BK7; repeated reabsorption and extraction not generalized")
        for r in records:
            p=r["expected_photon_fraction"]
            count_atol=6*math.sqrt(p*(1-p)/n)+2e-5
            if abs(r["actual_W"]-r["expected_W"])>r["atol_W"] or abs(r["hits"]/n-p)>count_atol:
                spectral_failures.append(r)
        grid=np.linspace(500,750,10001);pdf=np.interp(grid,x,y)/norm
        mean_loss=float(np.trapezoid(pdf*(1-excitation/grid),grid))
        second_loss=float(np.trapezoid(pdf*(1-excitation/grid)**2,grid))
        expected=1-probability*mean_loss
        energy_atol=6*math.sqrt((probability*second_loss-(probability*mean_loss)**2)/n)+2e-5
        record.update(expected_total_W=expected,total_power_atol_W=energy_atol,
                      spectral_status="numeric_failure"if spectral_failures else"numeric_pass",spectral_failures=spectral_failures,
                      expected_conversion_count=n*probability,observed_conversion_count=sum(r["hits"]for r in records))
        (e.folder/"fluorescence-integral-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        e.check("full detected Stokes energy",flux["total_flux"],expected,atol=energy_atol,rtol=0)
        e.check("total converted photon fraction",sum(r["hits"]for r in records)/n,probability,
                atol=6*math.sqrt(probability*(1-probability)/n)+2e-5,rtol=0)
    asyncio.run(execute("fluorescence_integral_"+criterion,work,role="fixture"))
    if criterion=="spectrum":
        assert not spectral_failures, "Native wavelength sub-bins fail the fixed sample_3 spectrum criterion; see fluorescence-integral-reference.json: "+str(spectral_failures)
