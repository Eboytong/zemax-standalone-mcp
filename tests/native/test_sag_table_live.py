"""Manufacturing table native operands against analytic rotational surfaces."""
import asyncio,json,math
import numpy as np
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_sag_table_parabola_reference():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(row_atol=1e-8,row_rtol=1e-6,
            summary_atol=1e-6,summary_rtol=1e-5,volume_atol=1e-5,
            reference='z=a*y^2, a=1/80+.0001; MinimumVolume sphere touches vertex and edge; independent analytic slopes and radial-area quadrature'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=40,
            conic=-1,parameters={'1':.0001},semi_diameter=5,thickness=20,replace_solves=True)]))
        surfaces=await e.call('get_surfaces');merit=await e.call('get_merit_function');settings=await e.call('get_system_settings')
        r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1))))
        (e.folder/'table.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        a=.0126;edge=5.;radius=(edge*edge+(a*edge*edge)**2)/(2*a*edge*edge)
        e.check('BFS radius',r['summary']['radius'],radius,atol=1e-8,rtol=1e-6)
        for row in r['rows']:
            y=row['y'];root=math.sqrt(radius*radius-y*y);sag=a*y*y;bfs=y*y/(radius+root)
            expected=dict(sag=sag,bfs_sag=bfs,deviation=sag-bfs,removal_depth=sag-bfs,
                slope=2*a*y,bfs_slope=y/root,slope_difference=2*a*y-y/root)
            for key,value in expected.items():e.check(key+' at '+str(y),row[key],value,atol=1e-8,rtol=1e-6)
        y=np.linspace(0,edge,200001);root=np.sqrt(radius*radius-y*y)
        depth=a*y*y-y*y/(radius+root);ds=2*a*y-y/root
        expected=dict(maximum_removal_depth=float(depth.max()),removal_volume=float(2*math.pi*np.trapezoid(depth*y,y)),
            rms_removal_depth=math.sqrt(2*np.trapezoid(depth*depth*y,y)/(edge*edge)),
            maximum_slope_difference=float(np.max(np.abs(ds))),rms_slope_difference=math.sqrt(2*np.trapezoid(ds*ds*y,y)/(edge*edge)))
        for key,value in expected.items():e.check(key,r['summary'][key],value,atol=1e-5 if key=='removal_volume' else 1e-6,rtol=1e-5)
        assert await e.call('get_surfaces')==surfaces
        assert await e.call('get_merit_function')==merit
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('sag368_parabola',work))


@pytest.mark.zemax
@pytest.mark.parametrize('shape',['plane','sphere','concave'])
def test_sag_table_degenerate_and_signed_surfaces(shape):
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1))
        values=dict(plane=dict(radius='Infinity'),sphere=dict(radius=40),
            concave=dict(radius=-40,conic=-1,parameters={'1':-.0001}))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='EvenAspheric',
            semi_diameter=5,thickness=20,replace_solves=True)|values[shape]]))
        q=dict(kind='sag_table',surface=2)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'table.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        if shape=='plane':
            assert r['summary']['curvature']==0 and r['summary']['curvature_state']=='planar'
            assert r['summary']['radius'] is None or r['summary']['radius']>=1e10
        for row in r['rows']:
            y=row['y']
            if shape=='plane':sag=slope=0
            elif shape=='sphere':sag=y*y/(40+math.sqrt(1600-y*y));slope=y/math.sqrt(1600-y*y)
            else:sag=-.0126*y*y;slope=-.0252*y
            e.check('signed sag',row['sag'],sag,atol=1e-8,rtol=1e-6)
            e.check('signed slope',row['slope'],slope,atol=1e-8,rtol=1e-6)
            e.check('removed material sign',row['removal_depth'],row['deviation']-r['summary']['vertex_offset'],atol=1e-12)
            assert row['removal_depth']>=-1e-6
        if shape=='concave':
            assert r['summary']['vertex_offset']<0
            e.check('vertex removal depth',r['rows'][0]['removal_depth'],-r['summary']['vertex_offset'],atol=1e-12)
        else:
            for key in ['maximum_removal_depth','removal_volume','rms_removal_depth','maximum_slope_difference','rms_slope_difference']:
                e.check('plane/sphere '+key,r['summary'][key],0,atol=1e-7,rtol=0)
        annular=await e.finish(await e.call('run_analysis',dict(request=q|dict(minimum_radius=1,maximum_radius=3,samples=11))))
        assert len(annular['rows'])==11 and annular['rows'][0]['y']==1 and annular['rows'][-1]['y']==3
        assert annular['actual_settings']['effective_radius_range']==[1,3]
    asyncio.run(execute('sag371_'+shape,work))


@pytest.mark.zemax
def test_sag_table_paging_cancel_export_reload():
    import time
    from PIL import Image
    async def work(e):
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=40,
            conic=-1,parameters={'1':.0001},semi_diameter=5,thickness=20,replace_solves=True)]))
        caps=await e.call('get_capabilities')
        assert caps['analyses']['sag_table']['supported_criterion']=='MinimumVolume'
        assert caps['analyses']['sag_table']['verification'].startswith('implemented;')
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function');configs=await e.call('get_configurations',dict(request={}))
        q=dict(kind='sag_table',surface=1)
        result=await e.finish(await e.call('run_analysis',dict(request=q)));tid=result['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=tid,start=3,count=4))
        assert page['rows']==result['rows'][3:7]
        page=await e.call('get_task_result',dict(task_id=tid,series=1,start=3,count=4))
        assert page['series'][0]['y']==result['series'][1]['y'][3:7]
        png=e.folder/'sag-removal.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(png),item=1)))
        with Image.open(png) as image:assert image.width>0 and image.height>0
        bad=await e.call('run_analysis',dict(request=q|dict(surface=999)),okay=False)
        assert bad['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=q|dict(samples=10001)))
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+30
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled'
        await e.call('get_task_result',dict(task_id=task['task_id']))
        rerun=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert rerun['rows']==result['rows'] and rerun['summary']==result['summary']
        async def unchanged():
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
            assert await e.call('get_configurations',dict(request={}))==configs
        await unchanged()
        path=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path));await unchanged()
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('sag372_lifecycle',work))
