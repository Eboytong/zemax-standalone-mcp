import asyncio,math
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_basic_analyses_stdio():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        ray=await e.finish(await e.call('run_analysis',dict(request=dict(kind='single_ray_trace',hy=.2,py=.5))))
        for row in ray['rows']:
            if row.get('ray_section')!='real' or not row.get('surface'):continue
            ref=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=[dict(hy=.2,py=.5)],target_surface=row['surface']))))
            for a,b in zip(row['position'],ref['rows'][0]['position']):e.check('real ray coordinate',a,b,atol=1e-8)
        grid=await e.finish(await e.call('run_analysis',dict(request=dict(kind='grid_distortion',field_width=10,aspect=.7))))
        rays=[dict(hx=r['field'][0]/20,hy=r['field'][1]/20) for r in grid['rows']]
        ref=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays))))
        for row,r in zip(grid['rows'],ref['rows']):
            for a,b in zip(row['actual'],r['position'][:2]):e.check('grid chief ray',a,b,atol=1e-5)
        await e.call('export_analysis_image',dict(request=dict(task_id=grid['task']['task_id'],path=str(e.folder/'distortion.png'))))
        seidel=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_coefficients'))))
        for section in {r['section'] for r in seidel['rows']}:
            rows=[r for r in seidel['rows'] if r['section']==section and r.get('coefficients')]
            total=[r for r in rows if r['row_label'].lower() in ('sum','total','累计')]
            if total and len(rows)>1:
                for key,value in total[0]['coefficients'].items():e.check('Seidel surface sum',sum(r['coefficients'][key] for r in rows if r not in total),value,atol=1e-5)
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=4,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=5,material='N-BK7',replace_solves=True),dict(surface=2,radius=-50,thickness=50,replace_solves=True)]))
        c=await e.finish(await e.call('run_analysis',dict(request=dict(kind='cardinal_points',end_surface=2))))
        l2=.55**2;n=math.sqrt(1+sum(b*l2/(l2-v) for b,v in [(1.03961212,.00600069867),(.231792344,.0200179144),(1.01046945,103.560653)]))
        power=(n-1)/50;C=-(2*power-5/n*power**2);f=-1/C;H=(-5*power/n)/C
        spherical=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_coefficients'))))
        height=2.;slope=0.;index=1.;s1=0.
        for radius,next_index,distance in ((50.,n,5.),(-50.,1.,0.)):
            invariant=index*(slope+height/radius)
            after=(index*slope-height*(next_index-index)/radius)/next_index
            s1-=invariant**2*height*(after/next_index-slope/index)
            height+=distance*after;slope=after;index=next_index
        totals=[r for r in spherical['rows'] if r.get('row_label','').lower() in ('sum','total','累计') and 'SPHA' in r.get('coefficients',{})]
        assert len(totals)==1
        e.check('independent spherical Seidel S1',totals[0]['coefficients']['SPHA'],s1,atol=1e-6)
        for orientation in ('YZ','XZ'):
            values={r['key']:r['value'] for r in c['rows'] if r['orientation']==orientation}
            for key,value in dict(image_focal_length=f,object_focal_length=-f,object_principal_plane=H,image_principal_plane=-H,image_focal_plane=f-H).items():e.check('ABCD '+key,values[key],value,atol=1e-4)
        await e.call('update_surfaces',dict(changes=[dict(surface=2,tilt_decenter=dict(before_decenter_x=1))]))
        await e.call('update_system_settings',dict(settings=dict(global_reference_surface=1)))
        coordinates=[]
        for global_frame in (False,True):
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='single_ray_trace',py=.3,use_global=global_frame))))
            coordinates.append(next(r['position'] for r in result['rows'] if r.get('ray_section')=='real' and r.get('surface')==2))
        e.check('decenter global-local X',coordinates[1][0]-coordinates[0][0],1,atol=1e-8)
    asyncio.run(execute('basic_analyses_validation',work))
