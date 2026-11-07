import asyncio,json
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_power_maps_cooke_grid_stdio():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        results=[]
        for kind in ['power_field_map','power_pupil_map']:
            q=dict(kind=kind,surface=6,wavelength=2,x_points=7,y_points=5)
            if kind=='power_field_map':q.update(x_field_width=10,y_field_width=10)
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            g=r['grids'][0];assert g['nx']==7 and g['ny']==5 and len(g['values'])==5 and len(g['values'][0])==7
            assert any(v is not None for row in g['values'] for v in row)
            assert g['value_unit']=='diopters'
            page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],grid=0,x_start=1,y_start=1,width=3,height=2))
            assert page
            await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/(kind+'.png')))))
            results.append(r)
        assert await e.call('get_surfaces')==before
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        (e.folder/'power-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('power446_cooke',work))


@pytest.mark.zemax
def test_power_map_paraxial_analytic_reference():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=10)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=100,semi_diameter=5,replace_solves=True)]))
        for kind in ['power_field_map','power_pupil_map']:
            for quantity,expected in [('Power',10.),('EFL',100.)]:
                q=dict(kind=kind,surface=1,quantity=quantity,x_points=3,y_points=3)
                if kind=='power_field_map':q.update(x_field_width=2,y_field_width=2)
                r=await e.finish(await e.call('run_analysis',dict(request=q)))
                (e.folder/(kind+quantity+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
                e.check(kind+quantity+' axial analytic focal100mm',r['grids'][0]['values'][1][1],expected,atol=1e-6,rtol=1e-6)
    asyncio.run(execute('power447_paraxial',work))


@pytest.mark.zemax
def test_power_maps_single_interface_eFL_and_power_reference():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)])))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=10,y=10)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=50,material='N-BK7',semi_diameter=8,replace_solves=True)]))
        glass=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7',include_internal_transmission=False,include_birefringence=False)))
        n=glass['properties']['Nd'];radius=50.;expected_efl=n*radius/(n-1);expected_power=1000/expected_efl
        for kind in ['power_field_map','power_pupil_map']:
            q=dict(kind=kind,surface=1,wavelength=1,x_points=3,y_points=3)
            if kind=='power_field_map':q.update(x_field_width=8,y_field_width=8)
            for quantity,expected in [('Power',expected_power),('EFL',expected_efl)]:
                result=await e.finish(await e.call('run_analysis',dict(request=q|dict(quantity=quantity))))
                e.check(kind+' single-surface '+quantity,result['grids'][0]['values'][1][1],expected,atol=2e-4,rtol=2e-5)
            for data in ['Spherical','Maximum','Minimum','Tangential','Sagittal','X','Y']:
                result=await e.finish(await e.call('run_analysis',dict(request=q|dict(data_type=data))))
                e.check(kind+' on-axis rotational '+data,result['grids'][0]['values'][1][1],expected_power,atol=2e-4,rtol=2e-5)
            for data in ['Cylinder','Astigmatic']:
                result=await e.finish(await e.call('run_analysis',dict(request=q|dict(data_type=data))))
                e.check(kind+' on-axis rotational zero '+data,result['grids'][0]['values'][1][1],0,atol=2e-4,rtol=0)
    asyncio.run(execute('power474_reference',work))


@pytest.mark.zemax
def test_power_maps_spherical_symmetry_offset_and_lifecycle():
    import time
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)])))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=10,y=10)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=50,material='N-BK7',semi_diameter=8,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        maps={}
        for kind in ['power_field_map','power_pupil_map']:
            q=dict(kind=kind,surface=1,wavelength=1,x_points=7,y_points=5)
            q.update(x_field_width=8,y_field_width=8) if kind=='power_field_map' else None
            base=await e.finish(await e.call('run_analysis',dict(request=q)))
            shifted=await e.finish(await e.call('run_analysis',dict(request=q|dict(offset=2.5))))
            a,b=base['grids'][0],shifted['grids'][0]
            assert a['array_order'].startswith('values[y][x]') and len(a['values'])==5 and len(a['values'][0])==7
            for iy,row in enumerate(a['values']):
                for ix,value in enumerate(row):
                    other=b['values'][iy][ix]
                    if value is None:assert other is None
                    else:e.check(kind+' additive offset',other-value,2.5,atol=1e-9,rtol=1e-9)
            page=await e.call('get_task_result',dict(task_id=base['task']['task_id'],grid=0,x_start=1,y_start=1,width=3,height=2))
            assert page['grid']['values']==[r[1:4]for r in a['values'][1:3]]
            png=e.folder/(kind+'.png');await e.call('export_analysis_image',dict(request=dict(task_id=base['task']['task_id'],path=str(png))))
            assert png.is_file() and png.stat().st_size>0
            maps[kind]=base
        pupil=maps['power_pupil_map']['grids'][0]['values']
        for (y1,x1),(y2,x2) in [((0,3),(4,3)),((2,0),(2,6)),((1,2),(3,4)),((1,3),(3,3))]:
            e.check('axisymmetric pupil ring symmetry',pupil[y1][x1],pupil[y2][x2],atol=2e-7,rtol=2e-7)
        task=await e.call('run_analysis',dict(request=dict(kind='power_pupil_map',surface=1,x_points=129,y_points=129,field=1)))
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+30
        while task['state']not in('succeeded','failed','cancelled'):
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        cancelled=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert not cancelled['completed']
        for expected,actual in [(baseline,await e.call('get_surfaces')),(settings,await e.call('get_system_settings')),(merit,await e.call('get_merit_function'))]:assert actual==expected
        await e.call('save_lens_as',dict(path=str(e.folder/'reloaded.zos')));await e.call('open_lens',dict(path=str(e.folder/'reloaded.zos')))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings and await e.call('get_merit_function')==merit
        for q in [dict(kind='power_field_map',surface=1,x_points=3,y_points=3,x_field_width=8,y_field_width=8),dict(kind='power_pupil_map',surface=1,x_points=3,y_points=3)]:
            await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('power475_lifecycle',work))


@pytest.mark.zemax
def test_power_maps_biconic_principal_direction_reference():
    """Single refracting interface: f_x/y=n R_x/y/(n-1)."""
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5875618)],
            fields=[dict(x=0,y=0),dict(x=10,y=10)])))
        glass=await e.call('get_material_properties',dict(request=dict(
            catalog='SCHOTT',material='N-BK7',include_internal_transmission=False,
            include_birefringence=False)))
        n=glass['properties']['Nd'];records=[];failures=[]
        conditions=dict(reference='Paraxial principal curvatures of a single Biconic refracting interface; EFL=n R/(n-1)',
                        tolerance=dict(absolute=2e-4,relative=2e-5),wavelength_um=.5875618,
                        cases=[[100,50],[50,100],[-100,-50]])
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        for rx,ry in conditions['cases']:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Biconic',
                radius=ry,conic=0,parameters={'1':rx,'2':0},thickness=20,
                material='N-BK7',semi_diameter=5,replace_solves=True)]))
            baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
            for kind in ['power_field_map','power_pupil_map']:
                q=dict(kind=kind,surface=1,wavelength=1,x_points=3,y_points=3)
                if kind=='power_field_map':q.update(x_field_width=2,y_field_width=2)
                for quantity in ['Power','EFL']:
                    vx,vy=((1000*(n-1)/(n*rx),1000*(n-1)/(n*ry)) if quantity=='Power'
                           else (n*rx/(n-1),n*ry/(n-1)))
                    expected=dict(X=vx,Y=vy,Astigmatic=vx-vy,
                                  Maximum=max(vx,vy),Minimum=min(vx,vy),Cylinder=abs(vx-vy))
                    for data,value in expected.items():
                        result=await e.finish(await e.call('run_analysis',dict(request=q|dict(quantity=quantity,data_type=data))))
                        actual=result['grids'][0]['values'][1][1]
                        records.append(dict(rx=rx,ry=ry,kind=kind,quantity=quantity,data_type=data,
                                            actual=actual,reference=value,error=actual-value))
                        try:e.check(f'{kind} {rx}/{ry} {quantity} {data}',actual,value,atol=2e-4,rtol=2e-5)
                        except AssertionError:failures.append(e.checks[-1])
                        status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                        assert status['state']=='succeeded'
                        # POWF/POWP run as composite jobs; batch trace owns native closure.
                        assert not status.get('cleanup_warnings')
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
        (e.folder/'principal-reference.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('power486_biconic',work))


@pytest.mark.zemax
def test_power_field_tangent_sampling_coordinates_and_lifecycle():
    import math
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=30,y=20)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',
            parameters={'1':100},thickness=100,semi_diameter=5,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function')
        q=dict(kind='power_field_map',surface=1,x_points=5,y_points=3,
               x_field_width=60,y_field_width=40,use_tangent_of_field_angle=True)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        grid=result['grids'][0];actual=result['actual_settings']
        assert actual['field_sampling']=='uniform tangent'
        assert grid['x_unit']==grid['y_unit']=='dimensionless tangent'
        for row in result['rows']:
            ix,iy=row['grid_x'],row['grid_y']
            fx=math.degrees(math.atan(grid['x'][ix]));fy=math.degrees(math.atan(grid['y'][iy]))
            for label,value,want in [('x angle',row['field_x'],fx),('y angle',row['field_y'],fy),
                    ('Hx query',row['native_arguments'][2],fx/math.hypot(30,20)),
                    ('Hy query',row['native_arguments'][3],fy/math.hypot(30,20))]:
                e.check(label,value,want,atol=1e-12,rtol=1e-12)
            assert row['field_x']==actual['physical_field_x'][ix]
            assert row['field_y']==actual['physical_field_y'][iy]
        e.check('on-axis ideal power',grid['values'][1][2],10,atol=1e-6,rtol=1e-6)
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,
            x_start=1,y_start=1,width=3,height=2))
        assert page['grid']['values']==[r[1:4] for r in grid['values'][1:3]]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],
            path=str(e.folder/'tangent-power.png'))))
        (e.folder/'tangent-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('power488_tangent',work))


@pytest.mark.zemax
def test_power_maps_lens_units_and_planar_limit():
    async def work(e):
        records=[];failures=[]
        for units,scale in [('Millimeters',1),('Centimeters',.1)]:
            await e.model()
            await e.call('update_system_settings',dict(settings=dict(lens_units=units,
                aperture_value=10*scale,wavelengths=[dict(wavelength_um=.5875618)],
                fields=[dict(x=0,y=0),dict(x=10,y=10)])))
            glass=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',
                material='N-BK7',include_internal_transmission=False,include_birefringence=False)))
            n=glass['properties']['Nd']
            for radius in [50*scale,0]:
                await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=radius,
                    thickness=50*scale,material='N-BK7',semi_diameter=8*scale,replace_solves=True)]))
                baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
                for kind in ['power_field_map','power_pupil_map']:
                    q=dict(kind=kind,surface=1,x_points=3,y_points=3)
                    if kind=='power_field_map':q.update(x_field_width=2,y_field_width=2)
                    for quantity in ['Power','EFL']:
                        result=await e.finish(await e.call('run_analysis',dict(request=q|dict(quantity=quantity))))
                        grid=result['grids'][0];value=grid['values'][1][1]
                        assert grid['value_unit']==('diopters' if quantity=='Power' else units)
                        records.append(dict(units=units,radius=radius,kind=kind,quantity=quantity,
                                            center_value=value,result=result))
                        if radius or quantity=='Power':
                            expected=(1000*(n-1)/(n*50) if quantity=='Power' else n*radius/(n-1)) if radius else 0
                            try:e.check(units+' '+kind+' '+quantity+' '+str(radius),value,expected,atol=2e-4,rtol=2e-5)
                            except AssertionError:failures.append(e.checks[-1])
                assert await e.call('get_surfaces')==baseline
                assert await e.call('get_system_settings')==settings
        (e.folder/'unit-planar-reference.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('power492_units_planar',work))


