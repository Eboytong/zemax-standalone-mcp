"""Controlled equations for the eight planned geometric surface families."""
import asyncio
import json
import pytest
from tests.support.native import execute
from tests.support.finite_reference import snell,sellmeier,glass_coefficients
from tests.support.surface_reference import sag,normal

CASES={
 'Standard':{},
 'EvenAspheric':{1:1e-4,2:-1e-7},
 'Toroidal':{1:60,2:1e-4},
 'ChebyShv':{1:2,2:2,3:5,4:5,13:0,14:2e-5,15:0,16:1e-5,17:0,18:-1e-5,19:0,20:0},
 'ZernikeFringeSag':{**{i:0 for i in range(1,11)},13:6,14:5,15:0,16:.001,17:-.001,18:.002,19:.001,20:0},
 'Irregular':{1:0,2:0,3:0,4:0,5:.001,6:.002,7:.001,8:30},
 'Tilted':{1:.01,2:-.02},
 'GridSag':{**{i:0 for i in range(1,11)},13:0,14:5},
}


@pytest.mark.zemax
@pytest.mark.parametrize('kind',CASES)
def test_finite_geometric_surface_equation_native(kind):
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],temperature_c=20,adjust_index_to_environment=True)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=10,replace_solves=True),
            dict(surface=2,surface_type=kind,material='N-BK7',thickness=5,semi_diameter=5,replace_solves=True)]))
        # Active coefficient cells depend on the adopted polynomial order.
        # Select the order first, then read and edit the newly active cells.
        if kind=='ChebyShv':
            await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={1:2,2:2},replace_solves=True)]))
        if kind=='ZernikeFringeSag':
            await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={13:6},replace_solves=True)]))
        cells=(await e.call('get_surfaces',dict(start=2,count=1)))['surfaces'][0]['cells']
        change=dict(surface=2,replace_solves=True,parameters=CASES[kind])
        R=50 if cells['radius']['writable'] else None
        if R is not None:change['radius']=R
        if cells['conic']['writable']:change['conic']=0
        if kind=='GridSag':
            path=e.folder/'grid.dat';lines=['65 65 0.25 0.25 0']
            for iy in range(65):
                for ix in range(65):
                    x=(ix-32)*.25;y=(32-iy)*.25
                    lines.append(f'{.001*(x*x+2*y*y)} {.002*x} {.004*y} 0')
            path.write_text('\n'.join(lines),encoding='ascii');change['import_file']=str(path)
        await e.call('update_surfaces',dict(changes=[change]))
        saved=e.folder/'baseline.zos';await e.call('save_lens_as',dict(path=str(saved)))
        points=[(0.,0.),(.5,0.),(-.5,0.),(0.,.5),(0.,-.5),(.5,.75),(-.75,.5),(4.,0.),(0.,-4.)]
        n=sellmeier(.55,glass_coefficients());records=[]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(saved)))
            actual=(await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=x,y=y)for x,y in points]))))['rows']
            traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=2,
                rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in points]))))
            for (x,y),g,ray in zip(points,actual,traced['rows'],strict=True):
                expected=sag(kind,x,y,radius=R,parameters=CASES[kind])
                e.check('surface Sag mm',g['sag'],expected)
                e.check('independent vertical-ray intersection mm',ray['position'][2],expected)
                direction=snell((0,0,1),normal(kind,x,y,radius=R,parameters=CASES[kind]),1,n)
                for i in range(3):e.check('independent normal / Snell direction',ray['direction'][i],direction[i])
                records.append(dict(reloaded=reload,x_mm=x,y_mm=y,sag_mm=expected,ray=ray))
        controls={
            'Standard':[], 'EvenAspheric':list(range(1,9)), 'Toroidal':list(range(1,9)),
            'ChebyShv':[3,4,*range(13,21)], 'ZernikeFringeSag':[1,2,3,4,5,6,7,8,9,10,14,*range(15,21)],
            'Irregular':[5,6,7,8], 'Tilted':[1,2], 'GridSag':list(range(1,9)),
        }[kind]
        perturbations=[]
        for parameter in controls:
            nominal=CASES[kind].get(parameter,0.)
            delta=abs(nominal)*.01 if nominal else 1e-4/5**(2*parameter)if(
                kind in ('EvenAspheric','GridSag','ZernikeFringeSag')and parameter<=8)else 1e-4/5**(2*(parameter-1))if(
                kind=='Toroidal'and parameter>=2)else 1e-4
            for sign in (-1,1):
                await e.call('open_lens',dict(path=str(saved)))
                changed=dict(CASES[kind]);changed[parameter]=nominal+sign*delta
                await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={parameter:changed[parameter]},replace_solves=True)]))
                actual=(await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=x,y=y)for x,y in points]))))['rows']
                for (x,y),row in zip(points,actual,strict=True):
                    expected=sag(kind,x,y,radius=R,parameters=changed)
                    e.check(f'parameter_{parameter} signed perturbation Sag mm',row['sag'],expected)
                perturbations.append(dict(parameter=parameter,value=changed[parameter],sign=sign,checked_points=len(points)))
        (e.folder/'surface-equation-reference.json').write_text(json.dumps(dict(surface_type=kind,parameters=CASES[kind],
            manual_sections=['2.3.1.2.15','2.3.1.2.50','2.3.1.2.70','2.3.1.2.71','2.3.1.2.79'],
            scope='controlled parameters, signed continuous-parameter Sag changes, normals, refraction and reload; solve modes separately recorded',
            parameter_perturbations=perturbations,records=records),indent=2),encoding='utf-8')
    asyncio.run(execute('finite_surface_'+kind,work))
