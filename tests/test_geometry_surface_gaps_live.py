"""Finite noncoaxial native patch distances against analytic support planes."""
import asyncio,json,math
import pytest
from support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('angle,offset,radius,kind',[(0,.5,0,'Standard'),(20,0,0,'Standard'),(20,0,-40,'Standard'),(0,.5,0,'EvenAspheric'),(0,.5,0,'ExtendedPolynomial')])
def test_native_finite_surface_gap(angle,offset,radius,kind):
    async def work(e):
        await e.model()
        if kind=='ExtendedPolynomial':
            await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type=kind,**({}if kind=='ExtendedPolynomial'else {'mechanical_semi_diameter':2}),parameters={'13':3,'14':1,'17':.002},replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=0,thickness=3,semi_diameter=2,mechanical_semi_diameter=2,replace_solves=True),dict(surface=2,surface_type=kind,parameters={'1':.002}if kind=='EvenAspheric'else {'13':3,'14':1,'17':.002}if kind=='ExtendedPolynomial'else{},radius=radius,thickness=5,semi_diameter=2,tilt_decenter=dict(before_decenter_x=offset,before_tilt_y=angle),replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        policy=dict(version=1,constraints=[dict(id='gap',kind='min_gap',surface=1,other_surface=2,value_mm=1,source='finite disk support formula',reason='tilted native boundary')])
        if kind=='ExtendedPolynomial':policy['mechanical_exteriors']=[dict(id='edge',surface=2,outer_radius_mm=2,source='controlled patch dimensions',reason='explicit circular mechanical edge')]
        sag=-4/(40+math.sqrt(1600-4))if radius else 0
        expected=3-2*math.sin(math.radians(angle))+sag*math.cos(math.radians(angle))
        for version in [1,2]:
            if version==2:
                path=str(e.folder/'patch.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path));policy['version']=2
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',check='quick',engineering_policy=policy))))
            (e.folder/f'patch-{version}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            rule=result['geometry']['engineering_checks'][0]
            low,high=rule['actual_interval_mm'];assert low<=expected<=high,rule
            e.check('finite global surface distance',sum([low,high])/2,expected,atol=1e-6,rtol=1e-7)
            assert rule['measurement_source']=='native_global_finite_surface_distance'and rule['state']=='satisfied',rule
            assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('geometry134_surface_gap',work))


@pytest.mark.zemax
def test_native_tilted_surface_regions():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=0,thickness=3,semi_diameter=2,mechanical_semi_diameter=2,replace_solves=True),dict(surface=2,radius=0,semi_diameter=2,mechanical_semi_diameter=2,tilt_decenter=dict(before_tilt_y=20),replace_solves=True)]))
        regions=[dict(x_min_mm=0,x_max_mm=1,y_min_mm=-.1,y_max_mm=.1),dict(r_min_mm=1,r_max_mm=1.5)]
        for version,(region,xmax)in enumerate(zip(regions,[1,1.5]),1):
            policy=dict(version=version,constraints=[dict(id='gap',kind='min_gap',surface=1,other_surface=2,region=region,value_mm=1,source='tilted finite planar patches',reason='local coordinate region')])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',check='quick',engineering_policy=policy))))
            (e.folder/f'region-{version}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            rule=result['geometry']['engineering_checks'][0];expected=3-xmax*math.sin(math.pi/9)
            low,high=rule['actual_interval_mm'];assert low<=expected<=high,rule
            e.check('tilted finite regional gap',sum([low,high])/2,expected,atol=1e-6,rtol=1e-7)
            assert result['geometry']['surface_gap_measurements'][0]['region_frame']=='each_surface_local_xy_mm'
    asyncio.run(execute('geometry135_patch_regions',work))
