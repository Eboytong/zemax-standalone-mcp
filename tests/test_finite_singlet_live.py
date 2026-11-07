"""Fixed-image-plane chromatic singlet; independent analytic Snell reference."""
import asyncio
import json
import math
import pytest
from support.native import execute
from support.finite_reference import glass_coefficients, sellmeier, singlet_ray


@pytest.mark.zemax
@pytest.mark.parametrize('angle', [0, 5])
def test_finite_chromatic_singlet_native(angle):
    async def work(e):
        await e.model()
        await e.call('insert_surfaces', dict(at=2, count=2))
        waves = [.486, .55, .644]; coefficients = glass_coefficients()
        paraxial = singlet_ray(.0001, 0, 0, sellmeier(.55, coefficients))
        focus = -paraxial['back'][0]*paraxial['outside'][2]/paraxial['outside'][0]
        await e.call('update_system_settings', dict(settings=dict(
            material_catalogs=['SCHOTT'], temperature_c=20, adjust_index_to_environment=True,
            fields=[dict(x=angle, y=0)], wavelengths=[dict(wavelength_um=w) for w in waves])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, thickness=1, semi_diameter=10, replace_solves=True),
            dict(surface=2, radius=50, material='N-BK7', thickness=5, semi_diameter=5, is_stop=True, replace_solves=True),
            dict(surface=3, radius='Infinity', material='', thickness=focus, semi_diameter=5, replace_solves=True)]))
        baseline=e.folder/'baseline.zos'
        await e.call('save_lens_as', dict(path=str(baseline)))
        records=[]
        for wi,w in enumerate(waves, 1):
            n=sellmeier(w, coefficients)
            points=[(0.,0.),(1.,0.),(-1.,0.),(0.,1.),(0.,-1.),(2.,1.)]
            rays=[dict(wavelength=wi, x=x, y=y, z=0, l=math.sin(math.radians(angle)), m=0,
                       n=math.cos(math.radians(angle))) for x,y in points]
            for target in (2,3,4):
                data=await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                    input_mode='Direct',start_surface=1,target_surface=target,rays=rays))))
                for (x,y),row in zip(points,data['rows'],strict=True):
                    assert row['error_code']==row['vignette_code']==0,row
                    ref=singlet_ray(x,y,angle,n)
                    if target==2:
                        position=list(ref['front']); position[2]-=1; direction=ref['inside']
                    elif target==3:
                        position=list(ref['back']); position[2]-=6; direction=ref['outside']
                    else:
                        position=[ref['back'][i]+focus*ref['outside'][i]/ref['outside'][2] for i in range(3)]
                        position[2]-=6+focus; direction=ref['outside']
                    for i in range(3):
                        e.check(f'{w}um S{target} position{i} mm',row['position'][i],position[i])
                        e.check(f'{w}um S{target} direction{i}',row['direction'][i],direction[i])
                    records.append(dict(wavelength_um=w,target=target,input=[x,y],actual=row,expected_position_mm=position,expected_direction=direction))
        await e.call('open_lens',dict(path=str(baseline)))
        (e.folder/'singlet-reference.json').write_text(json.dumps(dict(angle_deg=angle,
            fixed_image_distance_mm=focus,coefficient_source='SCHOTT.AGF N-BK7 CD',coefficients=coefficients,
            formula='analytic sphere intersection, vector Snell refraction, planar exit and image intercept',
            records=records),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_singlet_'+str(angle),work))
