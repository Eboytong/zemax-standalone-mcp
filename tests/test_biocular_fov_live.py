import asyncio,math,json
import pytest
from support.native import execute

@pytest.mark.zemax
def test_fov_two_plane_circular_apertures_and_scan_border():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(boundary_radius_atol_mm=.02,reference='At distance d, aperture test (d*tanX)^2+(d*tanY)^2<10^2; STOP at1 and aperture at2.'),indent=2),encoding='utf-8')
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=50,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,thickness=50,semi_diameter=100,aperture=dict(type='CircularAperture',maximum_radius=10),replace_solves=True),dict(surface=3,semi_diameter=100,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=50),dict(configuration=2,value=100)])])))
        before=await e.call('get_surfaces');configs=await e.call('get_configurations',dict(request={}));merit=await e.call('get_merit_function')
        q=dict(kind='biocular_field_of_view',configurations=[1,0,2],left=-14,right=14,bottom=-9,top=9,x_points=13,y_points=9,refinement_steps=8)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        assert len(r['grids'])==2
        for row in r['rows']:
            if row['role']!='grid':continue
            d=50 if row['configuration']==1 else 100
            radius=math.hypot(d*math.tan(math.radians(row['x'])),d*math.tan(math.radians(row['y'])))
            assert row['passed']==(radius<10)
        for c in r['contours']:
            assert c['closed']
            if c['configuration']==2:
                assert not c['scan_limited']
                for x,y in c['points']:e.check('refined circular radius',math.hypot(100*math.tan(math.radians(x)),100*math.tan(math.radians(y))),10,atol=.02,rtol=0)
            else:assert c['scan_limited']
        assert all(c['closed']for c in r['validation_copies'])
        assert await e.call('get_surfaces')==before and await e.call('get_configurations',dict(request={}))==configs
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('fov416_circle',work))


@pytest.mark.zemax
def test_fov_native_annulus_and_separated_regions():
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=50,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,thickness=50,semi_diameter=100,aperture=dict(type='CircularAperture',minimum_radius=3,maximum_radius=10),replace_solves=True),dict(surface=3,semi_diameter=100,replace_solves=True)]))
        q=dict(kind='biocular_field_of_view',left=-15,right=15,bottom=-15,top=15,x_points=17,y_points=17,refinement_steps=8)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'annulus.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        assert len(r['contours'])==2 and all(c['closed']and not c['scan_limited']for c in r['contours'])
        for c in r['contours']:
            radii=[math.hypot(50*math.tan(math.radians(x)),50*math.tan(math.radians(y)))for x,y in c['points']]
            target=3 if sum(radii)/len(radii)<6 else 10
            for radius in radii:e.check('annulus boundary radius',radius,target,atol=.02,rtol=0)
        await e.call('update_surfaces',dict(changes=[dict(surface=2,aperture=dict(type='CircularAperture',maximum_radius=10)),dict(surface=3,aperture=dict(type='RectangularObscuration',x_half_width=1,y_half_width=100))]))
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'islands.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        assert len(r['contours'])==2 and all(c['closed']for c in r['contours'])
        for c in r['contours']:
            xs=[x for x,y in c['points']];assert min(xs)>0 or max(xs)<0
        assert all(c['closed']for c in r['validation_copies'])
    asyncio.run(execute('fov418_topology',work))

@pytest.mark.zemax
def test_fov_cosine_four_configurations():
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=50,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,thickness=50,semi_diameter=100,aperture=dict(type='CircularAperture',maximum_radius=10),replace_solves=True),dict(surface=3,semi_diameter=100,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)]*3,operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=i+1,value=d)for i,d in enumerate([50,75,100,125])])])) )
        await e.call('set_configuration',dict(configuration=3))
        before=await e.call('get_surfaces');configs=await e.call('get_configurations',dict(request={}));settings=await e.call('get_system_settings')
        q=dict(kind='biocular_field_of_view',configurations=[1,2,3,4],use_angles=False,left=-.25,right=.25,bottom=-.2,top=.2,x_points=9,y_points=7,refinement_steps=4)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert len(r['grids'])==4
        for row in r['rows']:
            if row['role']!='grid':continue
            d=[50,75,100,125][row['configuration']-1];radius=d*math.hypot(row['x'],row['y'])/math.sqrt(1-row['x']**2-row['y']**2)
            assert row['passed']==(radius<10)
        assert await e.call('get_surfaces')==before and await e.call('get_configurations',dict(request={}))==configs and await e.call('get_system_settings')==settings
    asyncio.run(execute('fov419_cosines',work))


@pytest.mark.zemax
def test_fov_pre_stop_ignore_full_empty_and_lifecycle():
    import time
    from PIL import Image
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=25,semi_diameter=100,aperture=dict(type='CircularObscuration',maximum_radius=1000),replace_solves=True),dict(surface=2,thickness=50,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=3,thickness=50,semi_diameter=100,aperture=dict(type='CircularAperture',maximum_radius=2),replace_solves=True),dict(surface=4,semi_diameter=100,replace_solves=True)]))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        q=dict(kind='biocular_field_of_view',left=-1,right=1,bottom=-1,top=1,x_points=5,y_points=3,refinement_steps=2)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert all(v==1 for row in r['grids'][0]['values']for v in row) and len(r['contours'])==1 and r['contours'][0]['scan_limited']
        tid=r['task']['task_id'];page=await e.call('get_task_result',dict(task_id=tid,grid=0,x_start=1,y_start=1,width=3,height=2))
        assert page['grid']['values']==[[1,1,1],[1,1,1]]
        page=await e.call('get_task_result',dict(task_id=tid,start=2,count=3));assert page['rows']==r['rows'][2:5]
        png=e.folder/'fov.png';await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(png),item=0)))
        with Image.open(png)as image:assert image.width>0
        bad=await e.call('run_analysis',dict(request=q|dict(configurations=[999])),okay=False);assert bad['error']['code']=='INDEX_OUT_OF_RANGE'
        t=await e.call('run_analysis',dict(request=q|dict(x_points=257,y_points=257)))
        t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='running'
        t=await e.call('cancel_task',dict(task_id=t['task_id']));deadline=time.monotonic()+60
        while t['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='cancelled'
        cancelled=await e.call('get_task_result',dict(task_id=t['task_id']));assert all(c['closed']for c in cancelled.get('validation_copies',[]))
        await e.finish(await e.call('run_analysis',dict(request=q)))
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings and await e.call('get_merit_function')==merit
        path=str(e.folder/'saved.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        assert await e.call('get_surfaces')==before
        await e.call('update_surfaces',dict(changes=[dict(surface=4,aperture=dict(type='CircularObscuration',maximum_radius=1000))]))
        empty=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert not empty['contours'] and empty['summary']['passed']==0 and all(v==0 for row in empty['grids'][0]['values']for v in row)
        assert all(c['closed']for c in empty['validation_copies'])
    asyncio.run(execute('fov420_lifecycle',work))


@pytest.mark.zemax
def test_fov_automatic_aperture_rejected_and_copy_closed():
    async def work(e):
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,replace_solves=True),dict(surface=2,solves={'semi_diameter':dict(mode='automatic')},replace_solves=True)]))
        before=await e.call('get_surfaces')
        q=dict(kind='biocular_field_of_view',x_points=3,y_points=3,refinement_steps=0)
        t=await e.call('run_analysis',dict(request=q))
        while t['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        result=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert t['state']=='failed' and result['error']['code']=='PRECONDITION_FAILED'
        assert all(c['closed']for c in result['validation_copies'])
        assert await e.call('get_surfaces')==before
        await e.call('update_surfaces',dict(changes=[dict(surface=2,semi_diameter=100,replace_solves=True)]))
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('fov422_precondition',work))
