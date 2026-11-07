"""Native shared interfaces and explicit relationship provenance."""
import asyncio,json,math
import pytest
from support.native import execute

@pytest.mark.zemax
def test_native_cemented_relation_and_conflict():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        await e.call('update_surfaces',dict(changes=[dict(surface=i,radius=0,material=m,thickness=t,semi_diameter=2,mechanical_semi_diameter=2,replace_solves=True)for i,m,t in [(1,'N-BK7',3),(2,'N-F2',4),(3,'',5)]]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        for version,kind in [(1,'cemented'),(2,'contact')]:
            policy=dict(version=version,constraints=[dict(id='center',kind='min_center_thickness',surface=1,value_mm=2,source='controlled slabs',reason='center thickness')],relations=[dict(id='bond',kind=kind,entities=['S1-S2','S2-S3'],source='shared native boundary',reason='cemented doublet')])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
            (e.folder/f'relation-{kind}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            solid=result['geometry']['solid_geometry']
            if kind=='cemented':
                assert solid['state']=='passed',solid
                assert solid['pairs'][0]['relation']=='cemented'
                assert solid['media_state']=='measured',solid['media']
                for medium in solid['media']:
                    interface=medium['interfaces'][0];assert interface['state']=='mapped'
                    e.check('shared cemented face area',sum(p['area_mm2']for p in interface['patches']),math.pi*4,atol=1e-6,rtol=1e-7)
                    for patch in interface['patches']:
                        first,second=patch['faces']
                        e.check('shared outward normal opposition',sum(a*b for a,b in zip(first['outward_normal'],second['outward_normal'])),-1,atol=1e-8,rtol=1e-7)
                        assert {first['material'],second['material']}=={'N-BK7','N-F2'}
                e.check('cemented contact distance',solid['pairs'][0]['distance_mm'],0,atol=1e-6,rtol=1e-7)
                for entity,t in zip(solid['entities'],[3,4]):e.check('cemented volume',entity['volume_mm3'],math.pi*4*t,atol=1e-6,rtol=1e-7)
            else:
                assert solid['state']=='unverified',solid
                assert any(issue['code']=='relationship_conflict'for issue in solid['issues'])
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute('geometry109_cemented',work))


@pytest.mark.zemax
def test_native_nested_boxes():
    from support.nsc import setup,update
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='RectangularVolume',material='N-BK7',data=dict(X1HalfWidth=2,Y1HalfWidth=2,X2HalfWidth=2,Y2HalfWidth=2,ZLength=6)),dict(object=2,object_type='RectangularVolume',z=2,inside_of=1,material='N-F2',data=dict(X1HalfWidth=1,Y1HalfWidth=1,X2HalfWidth=1,Y2HalfWidth=1,ZLength=2))])
        initialized=str(e.folder/'initialized.zos');await e.call('save_lens_as',dict(path=initialized));await e.call('open_lens',dict(path=initialized))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        for version,kind in [(1,'nested'),(2,'contact'),(3,'nested'),(4,'intentional_overlap'),(5,'nested')]:
            if version==3:await update(e,[dict(object=2,z=5)])
            if version==5:await update(e,[dict(object=2,z=2,inside_of=0)])
            current=await e.call('get_nsc_objects',dict(request={}))
            policy=dict(version=version,constraints=[dict(id='wall',kind='min_wall_thickness',object=2,faces=[1,2],value_mm=1,source='nested boxes',reason='known dimensions')],relations=[dict(id='inside',kind=kind,entities=['O1','O2'],source='native InsideOf',reason='nested volume')])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
            (e.folder/f'nested-{version}-{kind}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            solid=result['geometry']['solid_geometry']
            assert solid['state']==('passed'if version in [1,4]else'failed'),solid
            if version==3:assert solid['pairs'][0]['reason']=='nested_region_not_contained'
            if version==1:
                assert result['geometry']['state']=='passed',result['geometry']
                assert solid['media_state']=='measured',solid['media']
                assert [m['material']for m in solid['media']]==['N-BK7','N-F2']
                for medium,expected in zip(solid['media'],[88,8]):e.check('effective native material volume',medium['effective_volume_mm3'],expected,atol=1e-6,rtol=1e-7)
                assert solid['media'][0]['boundaries'][1]['normal_sign']==-1
                caps=sorted(solid['entities'][0]['faces'],key=lambda f:f['center_mm'][2])
                e.check('outer lower outward normal',caps[0]['outward_normal'][2],-1)
                e.check('outer upper outward normal',caps[-1]['outward_normal'][2],1)
            if version in [2,3,4,5]:assert solid['media_state']=='unverified'
            e.check('nested overlap volume',solid['pairs'][0]['intersection_volume_mm3'],4 if version in [3,4]else 8,atol=1e-6,rtol=1e-7)
            for entity,volume in zip(solid['entities'],[96,8]):e.check('native box volume',entity['volume_mm3'],volume,atol=1e-6,rtol=1e-7)
            assert await e.call('get_nsc_objects',dict(request={}))==current
        await update(e,[dict(object=2,z=2,inside_of=1)])
        saved=str(e.folder/'nested.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        policy['version']=6
        result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
        (e.folder/'nested-reloaded.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        assert result['geometry']['solid_geometry']['state']=='passed'
        assert result['geometry']['solid_geometry']['media_state']=='measured'
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('geometry110_nested',work))


@pytest.mark.zemax
def test_native_three_level_material_regions():
    from support.nsc import setup,update
    async def work(e):
        await setup(e,4)
        await update(e,[dict(object=i,object_type='RectangularVolume',x=x,z=z,inside_of=parent,material=m,data=dict(X1HalfWidth=h,Y1HalfWidth=h,X2HalfWidth=h,Y2HalfWidth=h,ZLength=L))for i,h,L,z,parent,m,x in [(1,5,10,0,0,'N-BK7',0),(2,3,6,2,1,'N-F2',0),(3,1,2,4,2,'',0),(4,.5,1,4,1,'N-F2',4)]])
        path=str(e.folder/'hierarchy.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        policy=dict(version=1,constraints=[dict(id='wall',kind='min_wall_thickness',object=1,faces=[1,2],value_mm=1,source='nested analytic boxes',reason='dimensions')],relations=[dict(id=f'nest{a}{b}',kind='nested',entities=[f'O{a}',f'O{b}'],source='InsideOf ancestry',reason='material region')for a,b in [(1,2),(2,3),(1,3),(1,4)]])
        for version in [1,2]:
            if version==2:await e.call('open_lens',dict(path=path));policy['version']=2
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
            (e.folder/f'hierarchy-{version}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            solid=result['geometry']['solid_geometry'];assert solid['state']=='passed'and solid['media_state']=='measured',solid
            assert [m['material']for m in solid['media']]==['N-BK7','N-F2','','N-F2']
            assert [m['parent']for m in solid['media']]==[None,'O1','O2','O1']
            for medium,volume in zip(solid['media'],[783,208,8,1]):e.check('three level effective material',medium['effective_volume_mm3'],volume,atol=1e-6,rtol=1e-7)
            assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('geometry120_hierarchy',work))
