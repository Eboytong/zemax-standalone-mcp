"""Independent source sag and volume references in physical units."""
import asyncio,json,math
from decimal import Decimal,localcontext
import pytest
from support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('kind,unit,scale',[('sphere','Millimeters',1),('asphere','Millimeters',1),('asphere','Centimeters',10)])
def test_native_geometry_source_reference(kind,unit,scale):
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(lens_units=unit,material_catalogs=['SCHOTT'])))
        front=dict(surface=1,surface_type='EvenAspheric'if kind=='asphere'else'Standard',radius=0 if kind=='asphere'else 40/scale,material='N-BK7',thickness=3/scale,semi_diameter=2/scale,mechanical_semi_diameter=2/scale,replace_solves=True)
        if kind=='asphere':front['parameters']={'1':.002*scale}
        await e.call('update_surfaces',dict(changes=[front,dict(surface=2,radius=0 if kind=='asphere'else -40/scale,thickness=5/scale,semi_diameter=2/scale,mechanical_semi_diameter=2/scale,replace_solves=True)]))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        points=[dict(x=r/scale,y=0)for r in [0,.3,1,1.9]]
        sag=await e.call('get_surface_geometry',dict(request=dict(surface=1,points=points)))
        for row,r in zip(sag['rows'],[0,.3,1,1.9]):
            expected=.002*r*r if kind=='asphere'else r*r/(40+math.sqrt(1600-r*r))
            e.check('source sag mm',row['sag']*scale,expected,atol=1e-8,rtol=1e-7)
        request=dict(scope='system',representation_tolerance_mm=1e-7)
        result=await e.finish(await e.call('get_surface_geometry',dict(request=request)),timeout_seconds=150)
        (e.folder/'source.json').write_text(json.dumps(dict(sag=sag,result=result),indent=2),encoding='utf-8')
        solid=result['geometry']['solid_geometry'];assert solid['state']=='passed',solid
        entity=solid['entities'][0];assert entity['representation_error_mm']<=1.001e-7,entity
        assert entity['definition_length_unit']=='mm'
        if kind=='asphere':assert entity['native_definition']['target_error_mm']==1e-7
        with localcontext()as context:
            context.prec=50;R=Decimal(40);a=Decimal(2)
            integral=R*a*a/2-(R**3-(R*R-a*a)**Decimal('1.5'))/3
            volume=math.pi*4*3-4*math.pi*float(integral)if kind=='sphere'else math.pi*4*3-.002*math.pi*16/2
        e.check('independent physical volume',entity['volume_mm3'],volume,atol=1e-6,rtol=1e-7)
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        path=str(e.folder/'source.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=await e.finish(await e.call('get_surface_geometry',dict(request=request)),timeout_seconds=150)
        (e.folder/'reloaded.json').write_text(json.dumps(reloaded,indent=2),encoding='utf-8')
        e.check('reloaded physical volume',reloaded['geometry']['solid_geometry']['entities'][0]['volume_mm3'],volume,atol=1e-6,rtol=1e-7)
        assert await e.call('get_surfaces')==before
        if kind=='sphere':
            await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=3/scale),dict(configuration=2,value=4/scale)])])))
            configurations=await e.call('get_configurations',dict(request={}))
            multi=await e.finish(await e.call('get_surface_geometry',dict(request=dict(request,configuration_scope='required'))),timeout_seconds=150)
            (e.folder/'configurations.json').write_text(json.dumps(multi,indent=2),encoding='utf-8')
            for fact in multi['geometry']['configurations']:
                expected=volume+(math.pi*4 if fact['configuration']==2 else 0)
                e.check('configured source volume',fact['solid_geometry']['entities'][0]['volume_mm3'],expected,atol=1e-6,rtol=1e-7)
            assert await e.call('get_configurations',dict(request={}))==configurations
    asyncio.run(execute('geometry124_'+kind+'_'+unit,work))


@pytest.mark.zemax
def test_native_box_reference_transform():
    from support.nsc import setup,update
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='RectangularVolume',x=3,y=-2,z=5,tilt_y=30,material='N-BK7',data=dict(X1HalfWidth=2,Y1HalfWidth=1,X2HalfWidth=2,Y2HalfWidth=1,ZLength=4)),dict(object=2,object_type='RectangularVolume',ref_object=1,inside_of=1,z=1,material='N-F2',data=dict(X1HalfWidth=.5,Y1HalfWidth=.5,X2HalfWidth=.5,Y2HalfWidth=.5,ZLength=1))])
        baseline=await e.call('get_nsc_objects',dict(request={}))
        policy=dict(version=1,constraints=[dict(id='wall',kind='min_wall_thickness',object=1,faces=[1,2],value_mm=1,source='rotated box',reason='known dimensions')],relations=[dict(id='inside',kind='nested',entities=['O1','O2'],source='InsideOf',reason='referenced body')])
        result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
        (e.folder/'transform.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        solid=result['geometry']['solid_geometry'];assert solid['state']=='passed',solid
        e.check('rotated parent effective volume',solid['media'][0]['effective_volume_mm3'],31,atol=1e-6,rtol=1e-7)
        c=math.cos(math.pi/6);s=math.sin(math.pi/6)
        def rotation(p):x,y,z=p;return [c*x+s*z,y,-s*x+c*z]
        for position,normal in [((-2,0,2),(-1,0,0)),((2,0,2),(1,0,0)),((0,-1,2),(0,-1,0)),((0,1,2),(0,1,0)),((0,0,0),(0,0,-1)),((0,0,4),(0,0,1))]:
            expected=[v+t for v,t in zip(rotation(position),[3,-2,5])]
            face=min(solid['entities'][0]['faces'],key=lambda f:math.dist(f['center_mm'],expected))
            for actual,value in zip(face['center_mm'],expected):e.check('global face centroid',actual,value,atol=1e-6,rtol=1e-7)
            for actual,value in zip(face['outward_normal'],rotation(normal)):e.check('global outward normal',actual,value,atol=1e-8,rtol=1e-7)
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('geometry125_transform',work))
