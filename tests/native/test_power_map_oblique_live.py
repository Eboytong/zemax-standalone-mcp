"""Single spherical interface: independent oblique wavefront curvatures."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('rx,ry',[(50,50),(100,50),(50,100)])
def test_power_map_oblique_spherical_interface(rx,ry):
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)],
            fields=[dict(x=0,y=0),dict(x=0,y=20),dict(x=1,y=20)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Biconic',radius=ry,
            parameters={'1':rx,'2':0},thickness=50,
            material='N-BK7',semi_diameter=8,is_stop=True,replace_solves=True)]))
        glass=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7',
            include_internal_transmission=False,include_birefringence=False)))
        n=glass['properties']['Nd'];incidence=math.radians(20)
        ci=math.cos(incidence);cr=math.sqrt(1-(math.sin(incidence)/n)**2)
        # Coddington equations for an object at infinity, evaluated at the
        # vertex chief ray: n*cos(r)^2/s_t=(n*cos(r)-cos(i))/R.
        focal=dict(Tangential=n*ry*cr**2/(n*cr-ci),Sagittal=n*rx/(n*cr-ci))
        (e.folder/'conditions.json').write_text(json.dumps(dict(reference='Oblique spherical refraction wavefront curvatures',
            refractive_index=n,incidence_degrees=20,radius_x=rx,radius_y=ry,reference_efl_mm=focal,
            absolute_tolerance=2e-4,relative_tolerance=2e-5),indent=2),encoding='utf-8')
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[];failures=[]
        for kind in ['power_field_map','power_pupil_map']:
            for data,efl in focal.items():
                for quantity,reference in [('EFL',efl),('Power',1000/efl)]:
                    q=dict(kind=kind,surface=1,wavelength=1,x_points=3,y_points=3,data_type=data,quantity=quantity)
                    if kind=='power_field_map':q.update(x_field_width=2,y_field_width=40)
                    else:q['field']=2
                    result=await e.finish(await e.call('run_analysis',dict(request=q)))
                    value=result['grids'][0]['values'][2 if kind=='power_field_map'else 1][1]
                    assert value is not None, result['rows']
                    records.append(dict(request=q,result=result,native=value,reference=reference,error=abs(value-reference)))
                    try:e.check(kind+' oblique '+data+' '+quantity,value,reference,atol=2e-4,rtol=2e-5)
                    except AssertionError:failures.append(e.checks[-1])
                    (e.folder/'oblique.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute(f'power524_oblique_{rx}_{ry}',work))
