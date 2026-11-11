"""Native sag, independent derivative and physical-line thickness references."""
import asyncio
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_manufacturing_geometry_stdio():
    async def work(e):
        await e.model()
        for shape in ('Standard','EvenAspheric'):
            conic = 0 if shape=='Standard' else -.5
            a4 = 0 if shape=='Standard' else 1e-5
            change=dict(surface=1,surface_type=shape,radius=40,conic=conic,thickness=3,
                        material='N-BK7',semi_diameter=3,replace_solves=True)
            if a4:change['parameters']={'1':0,'2':a4}
            await e.call('update_surfaces',dict(changes=[change,
                dict(surface=2,radius=-60,semi_diameter=3,thickness=10,replace_solves=True)]))
            before=await e.call('get_surfaces',dict(start=1,count=2))
            q=dict(kind='manufacturing_geometry',surface=1,back_surface=2,aperture_radius=2,
                   sampling='grid',samples=9,meridians=16,
                   limits=dict(max_abs_sag=.001,max_slope_rad=.2,min_edge_thickness=2))
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            assert result['summary']['invalid_count']==0
            assert result['summary']['samples_per_axis']==17
            assert result['thresholds'][0]['state']=='violated'
            assert result['thresholds'][1]['state']=='satisfied'
            for row in result['rows']:
                x,y=row['x'],row['y'];r2=x*x+y*y
                root=math.sqrt(1-(1+conic)*r2/40**2)
                sag=r2/40/(1+root)+a4*r2*r2
                dx=x/(40*root)+4*a4*x*r2
                dy=y/(40*root)+4*a4*y*r2
                back=-r2/60/(1+math.sqrt(1-r2/60**2))
                e.check(shape+' sag',row['sag'],sag,atol=1e-8,rtol=1e-7)
                e.check(shape+' slope X',row['slope_x'],dx,atol=1e-6,rtol=0)
                e.check(shape+' slope Y',row['slope_y'],dy,atol=1e-6,rtol=0)
                e.check(shape+' thickness',row['thickness'],3+back-sag,atol=1e-8,rtol=1e-7)
                if shape=='Standard':
                    e.check('sphere departure',row['departure'],0,atol=1e-8,rtol=0)
                    e.check('sphere curvature',row['abs_curvature'],1/40,atol=1e-6,rtol=0)
            assert result['convergence']['absolute_change']['max_abs_sag']<1e-8
            page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=3,count=5))
            assert page['rows']==result['rows'][3:8]
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],
                item=1,path=str(e.folder/(shape+'.png')))))
            assert await e.call('get_surfaces',dict(start=1,count=2))==before

        # Translate and tilt the back sphere; evaluate thickness at the same physical
        # line rather than subtracting sag at unrelated local coordinates.
        await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='CoordinateBreak',
            thickness=0,parameters={'1':.2,'2':-.1,'4':2},replace_solves=True)]))
        path=e.folder/'decentered.zos'
        await e.call('save_lens_as',dict(path=str(path),overwrite=True))
        await e.call('open_lens',dict(path=str(path)))
        q=dict(kind='manufacturing_geometry',surface=1,back_surface=3,aperture_radius=2,
               samples=9,meridians=8,center_x=.1,center_y=.2,refine=True,
               reference=dict(kind='specified_sphere',radius=40,vertex_sag=.01))
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['summary']['invalid_count']==0
        rf,tf=result['actual_settings']['front_transform']
        rb,tb=result['actual_settings']['back_transform']
        center=[tb[i]-60*rb[i][2] for i in range(3)]
        direction=[rf[i][2] for i in range(3)]
        for row in result['rows']:
            p=[tf[i]+sum(rf[i][j]*v for j,v in enumerate((row['x'],row['y'],row['sag']))) for i in range(3)]
            w=[p[i]-center[i] for i in range(3)]
            dot=sum(w[i]*direction[i] for i in range(3))
            disc=dot*dot-sum(v*v for v in w)+60**2
            guess=sum((tb[i]-p[i])*direction[i] for i in range(3))
            roots=[-dot-math.sqrt(disc),-dot+math.sqrt(disc)]
            expected=min(roots,key=lambda v:abs(v-guess))
            e.check('decentered physical thickness',row['thickness'],expected,atol=1e-8,rtol=1e-7)
        before=await e.call('get_surfaces',dict(start=1,count=3))
        pending=await e.call('run_analysis',dict(request=q|dict(samples=101,meridians=64)))
        await e.call('cancel_task',dict(task_id=pending['task_id']))
        for _ in range(200):
            terminal=await e.call('get_task_status',dict(task_id=pending['task_id']))
            if terminal['state'] in {'cancelled','succeeded','failed'}:break
            await asyncio.sleep(.02)
        assert terminal['state']=='cancelled'
        assert await e.call('get_surfaces',dict(start=1,count=3))==before

        await e.call('new_system')
        change=dict(surface=1,surface_type='ExtendedPolynomial',
            radius=0,semi_diameter=2,thickness=5,replace_solves=True,
            parameters={'13':5,'14':1,'15':0,'16':0,'17':.02,'18':.01,'19':.03})
        await e.call('update_surfaces',dict(changes=[change]))
        freeform=await e.finish(await e.call('run_analysis',dict(request=dict(
            kind='manufacturing_geometry',surface=1,aperture_radius=1,sampling='grid',samples=9,
            reference=dict(kind='specified_sphere',radius=0)))))
        for row in freeform['rows']:
            x,y=row['x'],row['y']
            e.check('freeform sag',row['sag'],.02*x*x+.01*x*y+.03*y*y,atol=1e-8,rtol=1e-7)
            e.check('freeform slope X',row['slope_x'],.04*x+.01*y,atol=1e-6,rtol=0)
            e.check('freeform slope Y',row['slope_y'],.01*x+.06*y,atol=1e-6,rtol=0)

    async def guarded(e):
        try:await work(e)
        finally:await e.call('disconnect')
    asyncio.run(execute('manufacturing_geometry',guarded))
