"""Organized native point cloud grid, invalid mask, sag and normal references."""
import asyncio,math
import pytest
from support.native import execute
from support.pcd_reference import rows


@pytest.mark.zemax
def test_native_point_cloud_sag_and_sampling():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=1,count=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=10),dict(surface=1,surface_type='CoordinateBreak',thickness=3,parameters={1:2,2:-1,3:10,4:7},replace_solves=True),dict(surface=2,radius=20,semi_diameter=5,replace_solves=True)]))
        saved=str(e.folder/'point_reference.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        for units in ['Millimeters','Centimeters']:
            await e.call('update_system_settings',dict(settings=dict(lens_units=units)))
            before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
            for fmt in ['ASCII','Binary','CompressedBinary']:
                for normals in [False,True]:
                    q=dict(surface=2,path=str(e.folder/(units+fmt+str(normals)+'.pcd')),x_sampling=7,y_sampling=5,format=fmt,include_surface_normals=normals)
                    r=await e.call('export_point_cloud',dict(request=q));points=rows(r['path'],r['header'])
                    assert r['copy_closed']and len(points)==35 and r['header']['width']==7 and r['header']['height']==5
                    for i,p in enumerate(points):
                        x=-5+10*(i%7+.5)/7;y=-5+10*(i//7+.5)/5
                        e.check('PCD local x '+units,p['x'],x,atol=1e-8,rtol=1e-7);e.check('PCD local y '+units,p['y'],y,atol=1e-8,rtol=1e-7)
                        if x*x+y*y>25:
                            assert math.isnan(p['z'])
                            if normals:assert all(math.isnan(p[k])for k in ['normal_x','normal_y','normal_z'])
                        else:
                            z=20-math.sqrt(400-x*x-y*y);e.check('PCD sphere sag '+units,p['z'],z,atol=1e-8,rtol=1e-7)
                            if normals:
                                for k,ref in [('normal_x',x/20),('normal_y',y/20),('normal_z',-(20-z)/20)]:e.check('PCD sphere '+k,p[k],ref,atol=1e-8,rtol=1e-7)
                    assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
    asyncio.run(execute('point_cloud176_reference',work))
