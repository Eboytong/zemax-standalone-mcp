"""Free propagation references for native Gaussian merit-operand queries."""
import asyncio
import json
import math

import pytest
from support.native import execute


@pytest.mark.zemax
def test_gaussian_free_propagation_and_preserved_model():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            atol=1e-8,rtol=1e-6,reference='q=z+i*pi*w0^2/lambda; embedded Gaussian with M2 scaling'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=5,replace_solves=True)]))
        surfaces=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        records=[]
        for request in [dict(kind='paraxial_gaussian_beam'),dict(kind='paraxial_gaussian_beam',m2=4,surface_1_to_waist=-10),
                        dict(kind='skew_gaussian_beam',waist_radius_x=.05,waist_radius_y=.08)]:
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            for row in result['rows']:
                waist=(request.get('waist_radius_x',.05) if row['axis']=='X' else request.get('waist_radius_y',.05))
                z=(0 if row['surface']==1 else 100)-request.get('surface_1_to_waist',0)
                zr=math.pi*waist*waist/.00055;m=math.sqrt(request.get('m2',1)) if row['beam_model']=='m2_scaled' else 1
                expected=dict(beam_radius=m*waist*math.sqrt(1+(z/zr)**2),waist_radius=m*waist,
                              position_from_waist=z,divergence_rad=m*math.atan(.00055/(math.pi*waist)),rayleigh_range=zr)
                for key,value in expected.items():e.check(request['kind']+' '+row['axis']+' '+str(row['surface'])+' '+key,row[key],value,atol=1e-8,rtol=1e-6)
                curvature=0 if row['phase_radius'] is None else 1/row['phase_radius']
                e.check('Gaussian phase curvature',curvature,z/(z*z+zr*zr),atol=1e-10,rtol=1e-6)
            assert result['computation_method']=='native_gaussian_merit_operands'
            assert result['series'] and len(result['rows'])==(8 if request.get('m2',1)>1 else 4)
        assert await e.call('get_surfaces')==surfaces
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('gaussian353_free',work))


@pytest.mark.zemax
def test_gaussian_astigmatic_lens_abcd_reference():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=1e-8,rtol=1e-6,
            reference='q_out=1/(1/q_in-P); q_image=q_out+70; P_x=.01 P_y=.02'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='ParaxialXY',
            parameters={'1':.01,'2':.02},thickness=70,semi_diameter=5,replace_solves=True)]))
        results=[]
        for kind in ['paraxial_gaussian_beam','skew_gaussian_beam']:
            request=dict(kind=kind)
            request.update(dict(surface_1_to_waist=-10,m2=4) if kind.startswith('paraxial') else
                           dict(start_surface_to_waist=-10,waist_radius_y=.08))
            result=await e.finish(await e.call('run_analysis',dict(request=request)));results.append(result)
            (e.folder/'outlets.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            for row in result['rows']:
                w=.08 if kind.startswith('skew') and row['axis']=='Y' else .05
                rayleigh=math.pi*w*w/.00055
                q=1/(1/complex(10,rayleigh)-(.01 if row['axis']=='X' else .02))
                if row['surface']==2:q+=70
                w0=math.sqrt(q.imag*.00055/math.pi)
                scale=2 if row['beam_model']=='m2_scaled' else 1
                expected=dict(position_from_waist=q.real,rayleigh_range=q.imag,waist_radius=w0*scale,
                    beam_radius=scale*math.sqrt(-.00055/(math.pi*(1/q).imag)),
                    divergence_rad=scale*math.atan(.00055/(math.pi*w0)),phase_radius=1/(1/q).real)
                for key,value in expected.items():
                    e.check(kind+' '+row['axis']+' '+str(row['surface'])+' '+row['beam_model']+' '+key,
                            row[key],value,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('gaussian356_lens',work))


@pytest.mark.zemax
def test_gaussian_selection_paging_cancel_export_and_reload():
    from pathlib import Path
    from PIL import Image
    import time
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        capabilities=await e.call('get_capabilities')
        for name in ('paraxial_gaussian_beam','skew_gaussian_beam'):
            assert capabilities['analyses'][name]['computation_method']=='native_gaussian_merit_operands'
            assert capabilities['analyses'][name]['verification'].startswith('accepted;')
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function');mce=await e.call('get_configurations',dict(request={}))
        for q in [dict(kind='paraxial_gaussian_beam',wavelength=2,orientation='Y',surface_start=2,surface_end=5,m2=2),
                  dict(kind='skew_gaussian_beam',wavelength=2,field=3,orientation='X',start_surface=2,end_surface=5,
                       start_surface_to_waist=3,waist_radius_x=.03)]:
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            tid=result['task']['task_id']
            assert {r['axis'] for r in result['rows']}=={q['orientation']}
            assert {r['surface'] for r in result['rows']}==set(range(2,6))
            page=await e.call('get_task_result',dict(task_id=tid,start=1,count=2))
            assert page['rows']==result['rows'][1:3]
            page=await e.call('get_task_result',dict(task_id=tid,series=0,start=1,count=2))
            assert page['series'][0]['y']==result['series'][0]['y'][1:3]
            png=e.folder/(q['kind']+'.png')
            await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(png),item=0)))
            with Image.open(png) as image:assert image.width>0 and image.height>0
            bad=await e.call('run_analysis',dict(request=q|dict(wavelength=999)),okay=False)
            assert bad['error']['code']=='INDEX_OUT_OF_RANGE'
            task=await e.call('run_analysis',dict(request=q))
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+30
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='cancelled',task
            await e.call('get_task_result',dict(task_id=task['task_id']))
            again=await e.finish(await e.call('run_analysis',dict(request=q)))
            assert again['rows']==result['rows']
        async def unchanged():
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
            assert await e.call('get_configurations',dict(request={}))==mce
        await unchanged()
        saved=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        await unchanged()
        await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('gaussian357_lifecycle',work))


@pytest.mark.zemax
def test_skew_off_axis_moving_frame_and_centimeter_units():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=1e-8,rtol=1e-6,
            reference='Free path thickness/cos(field angle), native Y beam size is surface-plane intercept radius (beam-normal size/cos(field angle)); waist/curvature in chief-ray frame; wavelength converted um to cm.'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(lens_units='Centimeters',aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0),dict(x=0,y=20)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=10,semi_diameter=10,replace_solves=True)]))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='skew_gaussian_beam',field=2,
            waist_radius_x=.005,waist_radius_y=.008,start_surface_to_waist=1))))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        assert result['length_unit']=='Centimeters'
        for row in result['rows']:
            waist=.005 if row['axis']=='X' else .008
            zr=math.pi*waist*waist/.000055
            z=-1 if row['surface']==1 else 10/math.cos(math.radians(20))-1
            expected=dict(position_from_waist=z,rayleigh_range=zr,waist_radius=waist,
                beam_radius=waist*math.sqrt(1+(z/zr)**2)/(math.cos(math.radians(20)) if row['axis']=='Y' else 1),divergence_rad=math.atan(.000055/(math.pi*waist)),
                phase_radius=(z*z+zr*zr)/z)
            for key,value in expected.items():e.check(row['axis']+' '+str(row['surface'])+' '+key,row[key],value,atol=1e-8,rtol=1e-6)
    asyncio.run(execute('gaussian360_skew_offaxis',work))


@pytest.mark.zemax
def test_gaussian_glass_plate_wavelength_and_configuration():
    from support.thin_film import bk7_index
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=1e-8,rtol=1e-6,
            reference='Plane air/glass interface q_out=n2/n1*q_in; BK7 Sellmeier; two wavelengths and plate thickness configurations'),indent=2),encoding='utf-8')
        await e.call('new_system');await e.call('insert_surfaces',dict(at=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',thickness=8,semi_diameter=5,replace_solves=True),
            dict(surface=2,thickness=20,semi_diameter=5,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=8),dict(configuration=2,value=13)])])))
        records=[]
        for configuration,thickness in [(1,8),(2,13)]:
            await e.call('set_configuration',dict(configuration=configuration))
            baseline=await e.call('get_surfaces');merit=await e.call('get_merit_function');settings=await e.call('get_system_settings')
            for wave,wavelength in [(1,.55),(2,.65)]:
              n=bk7_index(wavelength);zr=math.pi*.05**2/(wavelength*.001)
              for kind in ['paraxial_gaussian_beam','skew_gaussian_beam']:
                r=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,wavelength=wave,orientation='Y'))))
                records.append(r);(e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                assert r['actual_settings']['configuration']==configuration
                for row in r['rows']:
                    q=complex(0,n*zr) if row['surface']==1 else complex(thickness/n,zr)
                    if row['surface']==3:q+=20
                    medium=n if row['surface']==1 else 1
                    w0=math.sqrt(q.imag*wavelength*.001/(math.pi*medium))
                    expected=dict(position_from_waist=q.real,rayleigh_range=q.imag,waist_radius=w0,
                        beam_radius=math.sqrt(-wavelength*.001/(math.pi*medium*(1/q).imag)),
                        divergence_rad=math.atan(wavelength*.001/(math.pi*medium*w0)))
                    for key,value in expected.items():e.check(str(configuration)+' '+str(wave)+' '+kind+' '+str(row['surface'])+' '+key,row[key],value,atol=1e-8,rtol=1e-6)
                    e.check('Glass plate phase curvature',1/row['phase_radius'],(1/q).real,atol=1e-10,rtol=1e-6)
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_merit_function')==merit
            assert await e.call('get_system_settings')==settings
    asyncio.run(execute('gaussian362_glass',work))
