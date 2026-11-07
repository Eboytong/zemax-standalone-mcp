"""Off-center entrance-pupil curvature checked by spherical refraction."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_power_pupil_spherical_oblique_local_reference():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)],
            fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=50,
            material='N-BK7',semi_diameter=8,is_stop=True,replace_solves=True)]))
        glass=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7',
            include_internal_transmission=False,include_birefringence=False)))
        n=glass['properties']['Nd'];baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[];failures=[]
        for data in ['Tangential','Sagittal']:
            for quantity in ['Power','EFL']:
                q=dict(kind='power_pupil_map',surface=1,wavelength=1,field=1,
                    x_points=5,y_points=5,data_type=data,quantity=quantity)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                for iy in [1,3]:
                    row=next(r for r in result['rows'] if r['grid_y']==iy and r['grid_x']==2)
                    assert row['value']is not None
                    # For an axial parallel input, incidence on a spherical
                    # surface is given by sin(i)=|local intercept Y|/R.
                    y=row['reference_ray']['position'][1]
                    si=abs(y)/50;ci=math.sqrt(1-si*si);cr=math.sqrt(1-(si/n)**2)
                    efl=n*50*(cr*cr if data=='Tangential'else 1)/(n*cr-ci)
                    reference=efl if quantity=='EFL'else 1000/efl
                    records.append(dict(request=q,point=row,native=row['value'],reference=reference,
                        error=abs(row['value']-reference),local_incidence_radians=math.asin(si)))
                    try:e.check(data+quantity+' Py='+str(row['y']),row['value'],reference,atol=2e-4,rtol=2e-5)
                    except AssertionError:failures.append(e.checks[-1])
                (e.folder/'curvature.json').write_text(json.dumps(dict(refractive_index=n,
                    reference='Coddington local curvature; native central intercept only supplies incidence geometry',
                    comparisons=records,results=result),ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('power526_pupil_curvature',work))
