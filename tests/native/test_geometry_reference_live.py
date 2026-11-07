"""Controlled plane slabs exercise native extraction and engineering measurements."""
import asyncio,json,math
import pytest
from tests.support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('gap',[2,1,.5,0,-.5])
def test_native_plane_slabs(gap):
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2,count=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        await e.call('update_surfaces',dict(changes=[dict(surface=i,radius=0,thickness=t,material=m,semi_diameter=2,mechanical_semi_diameter=2,replace_solves=True) for i,t,m in [(1,3,'N-BK7'),(2,gap,''),(3,4,'N-BK7'),(4,5,'')]]))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        policy=dict(version=1,constraints=[dict(id='wall',kind='min_wall_thickness',surface=1,faces=[2,3],value_mm=2,source='parallel plane slab dimensions',reason='3mm wall'),dict(id='gap',kind='min_gap',surface=2,value_mm=1,source='parallel plane slab dimensions',reason='specified air clearance')])
        if gap==0:policy['relations']=[dict(id='contact',kind='contact',entities=['S1-S2','S3-S4'],source='zero air spacing',reason='plane cap contact')]
        result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))),timeout_seconds=150)
        (e.folder/'geometry-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        fact=result['geometry'];solid=fact['solid_geometry']
        assert len(solid['entities'])==2,solid
        for entity,thickness in zip(solid['entities'],[3,4]):
            e.check('plane slab volume',entity['volume_mm3'],math.pi*4*thickness,atol=1e-6,rtol=1e-7)
        rows=fact['rows'];assert [r['medium']for r in rows]==['glass','air','glass'],rows
        ordered=sorted(solid['entities'][0]['faces'],key=lambda f:f['center_mm'][2])
        caps=[ordered[0],ordered[-1]]
        for cap in caps:e.check('plane cap area',cap['area_mm2'],math.pi*4,atol=1e-6,rtol=1e-7)
        policy['version']=2;policy['constraints'][0]['faces']=[f['id']for f in caps]
        result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))),timeout_seconds=150)
        (e.folder/'geometry-wall-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        fact=result['geometry'];solid=fact['solid_geometry']
        clearance=next(c for c in fact['engineering_checks']if c['id']=='gap')
        assert clearance['actual_interval_mm'][0]<=gap<=clearance['actual_interval_mm'][1],clearance
        assert clearance['state']==('satisfied'if gap>=1 else 'violated'),clearance
        wall=next(c for c in fact['engineering_checks']if c['id']=='wall')
        assert wall['actual_interval_mm'][0]<=3<=wall['actual_interval_mm'][1],wall
        e.check('independent solid distance',solid['pairs'][0]['distance_mm'],max(0,gap),atol=1e-6,rtol=1e-7)
        bounds=solid['pairs'][0]['distance_interval_mm']
        assert bounds[0]<=max(0,gap)<=bounds[1],bounds
        assert solid['state']==('failed' if gap<0 else 'passed'),solid
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        # Saving and reopening rebinds the explicit engineering policy version.
        path=str(e.folder/'slabs.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        policy['version']=3
        reloaded=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))),timeout_seconds=150)
        (e.folder/'geometry-reloaded.json').write_text(json.dumps(reloaded,indent=2),encoding='utf-8')
        measurement=next(c for c in reloaded['geometry']['engineering_checks']if c['id']=='wall')
        assert measurement['actual_interval_mm'][0]<=3<=measurement['actual_interval_mm'][1]
        restored=next(c for c in reloaded['geometry']['engineering_checks']if c['id']=='gap')
        assert restored['actual_interval_mm'][0]<=gap<=restored['actual_interval_mm'][1],restored
        assert restored['state']==clearance['state']
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('geometry093_slabs',work))


@pytest.mark.zemax
def test_native_explicit_gap_scope():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=3,replace_solves=True)]))
        for version,extra,reason in [(1,{'other_surface':3},'selected_boundary_unavailable'),(2,{'region':{'x_min':1}},'engineering_region_adapter_required'),(3,{'other_surface':2},None)]:
            policy=dict(version=version,constraints=[dict(id='gap',kind='min_gap',surface=1,value_mm=1,source='plane gap',reason='clearance',**extra)])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',check='quick',engineering_policy=policy))))
            rule=result['geometry']['engineering_checks'][0]
            if reason:
                assert rule['state']=='unverified'and rule['reason']==reason,rule
                assert 'actual_interval_mm'not in rule
            else:
                assert rule['state']=='satisfied',rule
                assert rule['actual_interval_mm'][0]<=3<=rule['actual_interval_mm'][1]
    asyncio.run(execute('geometry101_scope',work))


@pytest.mark.zemax
def test_native_nonadjacent_annular_gap():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=2))
        await e.call('update_surfaces',dict(changes=[dict(surface=i,radius=-20 if i==4 else 0,material='',thickness=i,semi_diameter=2,mechanical_semi_diameter=2,replace_solves=True)for i in range(1,5)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        for version,region,radius in [(1,{},2),(2,{'r_min_mm':1,'r_max_mm':1.5},1.5),(3,{'x_min_mm':.5,'x_max_mm':1,'y_min_mm':.2,'y_max_mm':.6},math.hypot(1,.6))]:
            policy=dict(version=version,constraints=[dict(id='selected',kind='min_gap',surface=1,other_surface=4,region=region,value_mm=5,source='plane/sphere native model',reason='selected axial separation')])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',check='quick',engineering_policy=policy))))
            (e.folder/f'gap-{version}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            rule=result['geometry']['engineering_checks'][0]
            expected=6-20+math.sqrt(400-radius**2)
            low,high=rule['actual_interval_mm'];assert low<=expected<=high,rule
            e.check('selected native axial gap',high,expected,atol=1e-6,rtol=1e-7)
            assert rule['boundary_surfaces']==[1,4]and rule['state']=='satisfied'
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':2},cells=[dict(configuration=1,value=2),dict(configuration=2,value=4)])])))
        configurations=await e.call('get_configurations',dict(request={}))
        policy['version']=4
        for reload in [False,True]:
            if reload:
                path=str(e.folder/'selected.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path));policy['version']=5
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',check='quick',configuration_scope='required',engineering_policy=policy))))
            (e.folder/f'gap-configurations-{reload}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            assert result['geometry']['checked_configurations']==[1,2]
            for fact in result['geometry']['configurations']:
                rule=fact['engineering_checks'][0];expected=(6 if fact['configuration']==1 else 8)-20+math.sqrt(400-radius**2)
                low,high=rule['actual_interval_mm'];assert low<=expected<=high,rule
                e.check('configured selected gap',high,expected,atol=1e-6,rtol=1e-7)
            assert await e.call('get_configurations',dict(request={}))==configurations
    asyncio.run(execute('geometry104_selected',work))
