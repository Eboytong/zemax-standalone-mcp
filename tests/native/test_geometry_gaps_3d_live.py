"""Object-pair physical distances on a rotated native NSC baseline."""
import asyncio,json,math
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update

@pytest.mark.zemax
def test_native_3d_object_gap_and_clip():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=i,object_type='RectangularVolume',x=4*(i-1),tilt_y=30,material='N-BK7',data=dict(X1HalfWidth=1,Y1HalfWidth=1,X2HalfWidth=1,Y2HalfWidth=1,ZLength=2))for i in [1,2]])
        path=str(e.folder/'gap.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        baseline=await e.call('get_nsc_objects',dict(request={}))
        region=dict(x_min_mm=-2,x_max_mm=7,y_min_mm=-.5,y_max_mm=.5,z_min_mm=-1,z_max_mm=4)
        expected=4*math.cos(math.pi/6)-2
        for version,limit,box in [(1,1,{}),(2,2,{}),(3,1,region),(4,1,dict(region,x_min_mm=20,x_max_mm=30))]:
            policy=dict(version=version,constraints=[dict(id='gap',kind='min_gap',object=1,other_object=2,value_mm=limit,region=box,source='two translated rotated cubes',reason='known plane clearance')])
            result=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
            (e.folder/f'gap-{version}.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            check=result['geometry']['engineering_checks'][0]
            if version==4:
                assert check['state']=='unverified'and check['reason']=='region_has_no_selected_solid',check
                assert 'actual_interval_mm'not in check
            else:
                low,high=check['actual_interval_mm'];assert low<=expected<=high,check
                e.check('native rotated solid gap',sum([low,high])/2,expected,atol=1e-6,rtol=1e-7)
                assert check['state']==('violated'if version==2 else'satisfied'),check
            assert await e.call('get_nsc_objects',dict(request={}))==baseline
        await e.call('open_lens',dict(path=path));policy['version']=5;policy['constraints'][0]['region']=region
        final=await e.finish(await e.call('get_surface_geometry',dict(request=dict(scope='system',engineering_policy=policy))))
        assert final['geometry']['engineering_checks'][0]['state']=='satisfied'
        assert await e.call('get_nsc_objects',dict(request={}))==baseline
    asyncio.run(execute('geometry129_object_gap',work))
