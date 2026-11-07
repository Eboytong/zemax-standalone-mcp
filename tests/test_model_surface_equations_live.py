"""Documented native polynomial surfaces: sag, independent normals and reload."""
import asyncio,json,math
import pytest
from support.native import execute
from support.finite_reference import snell,sellmeier,glass_coefficients
from support.surface_reference import conic_sag

CASES={
    'Polynomial':{1:.001,2:-.00001,5:.002,6:.00002},
    'Periodic':{1:.01,2:.3,3:.2},
    'ExtendedAsphere':{13:240,14:2,15:.001,21:.002,254:.0001},
    'ExtendedOddAsphere':{13:240,14:2,15:.001,21:.002,254:.0001},
    'ExtendedPolynomial':{13:230,14:2,15:.001,21:.002,244:.0001},
}


def reference(kind,x,y,p):
    base=conic_sag(x,y,50)
    if kind=='Polynomial':return sum(p.get(i,0)*x**(2*i)+p.get(i+4,0)*y**(2*i)for i in range(1,5))
    if kind=='Periodic':return base-p[1]*(.25*(1+math.cos(2*math.pi*p[2]*x))*(1+math.cos(2*math.pi*p[3]*y))-1)
    if kind in ('ExtendedAsphere','ExtendedOddAsphere'):
        power=2 if kind=='ExtendedAsphere'else 1;r=math.hypot(x,y)/p[14]
        return base+sum(value*r**(power*(index-14))for index,value in p.items()if index>=15)
    terms=[(degree-j,j)for degree in range(1,21)for j in range(degree+1)]
    return base+sum(value*(x/p[14])**terms[index-15][0]*(y/p[14])**terms[index-15][1]for index,value in p.items()if index>=15)


@pytest.mark.zemax
@pytest.mark.parametrize('kind',CASES)
def test_documented_polynomial_surface_native(kind):
    async def work(e):
        p=CASES[kind];await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],temperature_c=20,adjust_index_to_environment=True)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,replace_solves=True),
            dict(surface=2,surface_type=kind,material='N-BK7',thickness=5,semi_diameter=3,parameters=p,replace_solves=True)]))
        if kind!='Polynomial':await e.call('update_surfaces',dict(changes=[dict(surface=2,radius=50,replace_solves=True)]))
        saved=e.folder/'surface.zos';await e.call('save_lens_as',dict(path=str(saved)))
        points=[(.2,.3),(-.5,.4),(.7,-.2),(1.2,.5)];n=sellmeier(.55,glass_coefficients());records=[]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(saved)))
            geometry=(await e.call('get_surface_geometry',dict(request=dict(surface=2,points=[dict(x=x,y=y)for x,y in points]))))['rows']
            rays=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=2,
                rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in points]))))
            for (x,y),g,r in zip(points,geometry,rays['rows'],strict=True):
                sag=reference(kind,x,y,p);e.check('documented sag mm',g['sag'],sag);e.check('ray intersection mm',r['position'][2],sag)
                h=1e-5;dx=(reference(kind,x+h,y,p)-reference(kind,x-h,y,p))/(2*h);dy=(reference(kind,x,y+h,p)-reference(kind,x,y-h,p))/(2*h)
                direction=snell((0,0,1),(-dx,-dy,1),1,n)
                for actual,expected in zip(r['direction'],direction):e.check('normal/Snell direction',actual,expected)
                records.append(dict(reloaded=reload,x=x,y=y,expected_sag=sag,ray=r))
        (e.folder/'surface-formula-reference.json').write_text(json.dumps(dict(kind=kind,parameters=p,
            reference='2024 R2 User Guide 2.3.1.2.25/.28/.29/.60/.61',records=records),indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_formula_'+kind,work))
