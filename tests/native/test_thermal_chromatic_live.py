"""SCHOTT thermo-optic and dispersion coefficients independently predict Snell rays."""
import asyncio,json,math
from pathlib import Path
import pytest
from tests.support.native import execute


def air_index(wavelength,temperature):
    l2=wavelength*wavelength
    return 1+(6432.8+2949810*l2/(146*l2-1)+25540*l2/(41*l2-1))*1e-8/(1+(temperature-15)*.0034785)


@pytest.mark.zemax
def test_catalog_thermal_and_chromatic_refraction_native():
    async def work(e):
        path=Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF"
        selected=False;cd=td=None
        for line in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
            if line.startswith("NM "):selected=line.split()[1]=="N-BK7"
            if selected and line.startswith("CD "):cd=list(map(float,line.split()[1:7]))
            if selected and line.startswith("TD "):td=list(map(float,line.split()[1:8]));break
        assert cd and td
        await e.model();await e.call("insert_surfaces",dict(at=2))
        wavelengths=(.486,.55,.644)
        await e.call("update_system_settings",dict(settings=dict(material_catalogs=["SCHOTT"],
            wavelengths=[dict(wavelength_um=w)for w in wavelengths],adjust_index_to_environment=True,pressure_atm=1)))
        await e.call("update_surfaces",dict(changes=[dict(surface=1,thickness=10),dict(surface=2,material="N-BK7",thickness=10,semi_diameter=100,replace_solves=True)]))
        sine=math.sin(math.radians(30));indices=[]
        for temp in (20,40,60):
            await e.call("update_system_settings",dict(settings=dict(temperature_c=temp)))
            result=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(input_mode="Direct",start_surface=1,target_surface=2,
                rays=[dict(wavelength=i+1,x=0,y=0,z=0,l=sine,m=0,n=math.sqrt(1-sine*sine))for i in range(3)]))))
            for wavelength,ray in zip(wavelengths,result["rows"]):
                # Manual 2.1.1.4.2: wavelength at reference air, then relative/absolute index.
                scaled=wavelength*air_index(wavelength,temp)/air_index(wavelength,td[6])
                l2=scaled*scaled;n=math.sqrt(1+sum(cd[i]*l2/(l2-cd[i+1])for i in (0,2,4)))
                delta=temp-td[6];d0,d1,d2,e0,e1,ltk,_=td
                dn=(n*n-1)/(2*n)*(d0*delta+d1*delta*delta+d2*delta**3+(e0*delta+e1*delta*delta)/(l2-math.copysign(ltk*ltk,ltk)))
                expected=(n*air_index(scaled,td[6])+dn)/air_index(wavelength,temp)
                actual=sine/ray["direction"][0]
                e.check(f"N-BK7 index at {temp}C {wavelength}um",actual,expected)
                indices.append(dict(temperature_c=temp,wavelength_um=wavelength,actual=actual,expected=expected))
        (e.folder/"thermal_reference.json").write_text(json.dumps(dict(catalog=str(path),dispersion=cd,thermal=td,
            model="manual 2.1.1.4.2 air normalization, Sellmeier and Schott thermal formula",indices=indices,
            scope="catalog index and planar Snell refraction; nonplanar thermal mounting remains separate"),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"thermal_glass.zos")))
    asyncio.run(execute("thermal_chromatic_index",work))
