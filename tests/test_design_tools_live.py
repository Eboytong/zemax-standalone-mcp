"""Serial design-tool adoption and controlled references; requires native license."""
import asyncio
import math
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('payload',[
    dict(kind='scale_factor',factor=2),dict(kind='scale_units',unit='Inches'),
])
def test_design_scale_numeric(payload):
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=10,conic=-.5,replace_solves=True)]))
        await e.call('get_design_tool_options',dict(request=dict(kind=payload['kind'])))
        result=await e.finish(await e.call('run_design_tool',dict(request=payload)))
        row=result['after']['surfaces'][1]
        factor=2 if payload['kind']=='scale_factor'else 1/25.4
        e.check('scaled radius',row['radius'],50*factor,atol=1e-8,rtol=1e-7)
        e.check('scaled thickness',row['thickness'],10*factor,atol=1e-8,rtol=1e-7)
        e.check('conic unchanged',row['conic'],-.5,atol=1e-12,rtol=1e-12)
        path=str(e.folder/'scaled.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        rows=(await e.call('get_surfaces',dict(start=1,count=1)))['surfaces']
        e.check('reloaded radius',rows[0]['cells']['radius']['value'],50*factor,atol=1e-8,rtol=1e-7)
    asyncio.run(execute('design_scale020_'+payload['kind'],work))

@pytest.mark.zemax
def test_design_convert_sag():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=50,conic=-.5,replace_solves=True)]))
        points=[dict(x=x,y=0)for x in [0,1,2,3,4]]
        before=await e.call('get_surface_geometry',dict(request=dict(surface=1,points=points)))
        result=await e.finish(await e.call('run_design_tool',dict(request=dict(kind='convert_asphere',surface=1,asphere_type='ExtendedAsphere',number_of_terms=8))))
        assert math.isfinite(result['ResidualRMSError'])
        after=await e.call('get_surface_geometry',dict(request=dict(surface=1,points=points)))
        for a,b in zip(before['rows'],after['rows']):e.check('converted sag',b['sag'],a['sag'],atol=1e-8,rtol=1e-7)
        expected=(await e.call('get_surfaces',dict(start=1,count=1)))['surfaces'][0]
        path=str(e.folder/'converted.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=(await e.call('get_surfaces',dict(start=1,count=1)))['surfaces'][0]
        assert reloaded['surface_type']==expected['surface_type']
        assert reloaded['cells']==expected['cells']
        restored=await e.call('get_surface_geometry',dict(request=dict(surface=1,points=points)))
        for a,b in zip(after['rows'],restored['rows']):e.check('reloaded converted sag',b['sag'],a['sag'],atol=1e-8,rtol=1e-7)
    asyncio.run(execute('design_convert020',work))

@pytest.mark.zemax
@pytest.mark.parametrize('kind',['quick_adjust','find_best_asphere','ray_aiming_wizard','sequential'])
def test_design_cooke(kind):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        if kind=='sequential':
            await e.call('get_optimization_wizard_options',dict(request=dict(kind=kind)))
            result=await e.finish(await e.call('run_optimization_wizard',dict(request=dict(kind=kind,criterion='Spot',type='RMS',apply=True))))
            assert result['applied']and result['operands_after']>1
        else:
            await e.call('get_design_tool_options',dict(request=dict(kind=kind)))
            q=dict(kind=kind)
            if kind=='quick_adjust':q.update(surface=6,replace_solve=True)
            if kind=='find_best_asphere':
                await e.call('update_merit_function',dict(mode='rms_spot_wizard'))
                await e.call('set_variables',dict(variables=[dict(surface=2,cell='radius',variable=True)]))
                q.update(first_surface=1,last_surface=6)
            result=await e.finish(await e.call('run_design_tool',dict(request=q)),timeout_seconds=180)
            if kind=='find_best_asphere':assert result['BestMeritFunction']<=result['StartMeritFunction']+1e-8
            if kind=='ray_aiming_wizard':assert result['applied']is False and result['recommended']
        path=str(e.folder/'design.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
    asyncio.run(execute('design_cooke020_'+kind,work))

@pytest.mark.zemax
@pytest.mark.parametrize('kind',['nsc','bitmap','roadway'])
def test_design_nsc_wizard_options(kind):
    async def work(e):
        await e.call('new_system',dict(mode='NonSequential'))
        await e.call('insert_nsc_objects',dict(request=dict(at=1)))
        await e.call('update_nsc_objects',dict(request=dict(changes=[
            dict(object=1,object_type='SourceRay',data={'NumberOfAnalysisRays':10,'ZCosine':1}),
            dict(object=2,object_type='DetectorRectangle',z=10,data={'NumberXPixels':8,'NumberYPixels':8})])))
        opts=await e.call('get_optimization_wizard_options',dict(request=dict(kind=kind)))
        assert opts['settings'] and opts['selections']
        if kind=='nsc':
            result=await e.finish(await e.call('run_optimization_wizard',dict(request=dict(kind=kind,apply=True))))
            assert result['applied']and result['operands_after']>0
        else:
            q=dict(kind=kind,apply=True)
            if kind=='bitmap':
                entries=opts['bitmap_files']['GetBitmapFileAt']['entries']
                square=next((item for item in entries if item.get('label','').casefold()=='square.bmp'),None)
                assert square is not None,opts['bitmap_files']
                q['bitmap_file']=square['native_index']
            result=await e.finish(await e.call('run_optimization_wizard',dict(request=q)))
            assert result['applied'] and result['operands_after']>0
        before=await e.call('get_merit_function')
        path=str(e.folder/'wizard.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        after=await e.call('get_merit_function')
        assert after['total']==before['total'] and after['operands']==before['operands']
    asyncio.run(execute('design_nsc020_'+kind,work))


@pytest.mark.zemax
def test_quick_adjust_independent_focus():
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2)))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius=50,thickness=5,material='N-BK7',replace_solves=True),
            dict(surface=2,radius=-50,thickness=45,semi_diameter=5,replace_solves=True)]))
        adjusted=await e.finish(await e.call('run_design_tool',dict(request=dict(kind='quick_adjust',surface=2,replace_solve=True))))
        focus=adjusted['after']['surfaces'][2]['thickness']
        rays=[dict(px=x/10,py=y/10,wavelength=1) for y in range(-10,11) for x in range(-10,11) if x*x+y*y<=100]
        async def variance(z):
            await e.call('update_surfaces',dict(changes=[dict(surface=2,thickness=z,replace_solves=True)]))
            result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(target_surface=3,rays=rays))))
            rows=result['rows']
            assert len(rows)==len(rays) and all(r['error_code']==0 and r['vignette_code']==0 for r in rows)
            x=[r['position'][0] for r in rows];y=[r['position'][1] for r in rows]
            return sum((a-sum(x)/len(x))**2+(b-sum(y)/len(y))**2 for a,b in zip(x,y))/len(x)
        left,center,right=[await variance(focus+delta) for delta in [-.1,0,.1]]
        curvature=(left+right-2*center)/.01
        assert curvature>0
        independent_focus=focus-(right-left)/.2/curvature
        e.check('QuickAdjust focus versus independent quadratic ray variance',focus,independent_focus,atol=.01,rtol=0)
        await e.call('update_surfaces',dict(changes=[dict(surface=2,thickness=focus,replace_solves=True)]))
        settings=await e.call('get_system_settings')
        path=str(e.folder/'applied.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        assert (await e.call('get_system_settings'))['ray_aiming']==settings['ray_aiming']
    asyncio.run(execute('design_focus_apply049',work))
