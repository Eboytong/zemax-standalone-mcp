"""Constant-throughput axial plate: native full pupil, batch grid and Fresnel."""
import asyncio
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_transmission_pupil_plate_matches_independent_fresnel_and_jones():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5876)], fields=[dict(x=0, y=0)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius='Infinity', thickness=1, semi_diameter=6,
                 coating='', replace_solves=True, solves=dict(material=dict(
                     mode='material_model', index_nd=1.5, abbe_vd=60, dpgf=0))),
            dict(surface=2, radius='Infinity', thickness=10, semi_diameter=6,
                 material='', coating='', replace_solves=True)]))
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        # No bulk absorption in the controlled model glass; two normal interfaces.
        index = 1.5
        reflection = ((index - 1) / (index + 1)) ** 2
        reference = (1 - reflection) ** 2
        pupils = [(x/16,y/16) for y in range(-16,17) for x in range(-16,17) if x*x+y*y<=256]
        rays = [dict(hx=0, hy=0, px=x, py=y, wavelength=1) for x, y in pupils]
        batch_means = []
        try:
            for jx, jy in [(1., 0.), (0., 1.)]:
                await e.call('update_system_settings', dict(settings=dict(polarization=dict(
                    unpolarized=False, jx=jx, jy=jy, x_phase=0, y_phase=0))))
                result = await e.finish(await e.call('run_analysis', dict(request=dict(kind='polarization_transmission'))))
                assert result['input_header']['unpolarized'] is False
                assert result['input_header']['jones']['jx'] == jx
                assert result['input_header']['jones']['jy'] == jy
                assert result['input_header']['grid'] == dict(nx=32, ny=32)
                assert len(result['fields']) == 1
                measured = result['fields'][0]['wavelengths'][0]['transmission']
                e.check(f'native pupil {jx},{jy} versus Fresnel', measured, reference, atol=1e-6, rtol=1e-6)
                trace = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                    rays=rays, polarization=dict(jx=jx, jy=jy)))))
                assert len(trace['rows']) == len(rays)
                assert all(r['state'] == 'succeeded' and r['error_code'] == 0 for r in trace['rows'])
                mean = math.fsum(r['intensity'] for r in trace['rows']) / len(rays)
                batch_means.append(mean)
                e.check(f'batch pupil {jx},{jy} versus Fresnel', mean, reference, atol=1e-6, rtol=1e-6)
                e.check(f'native versus batch {jx},{jy}', measured, mean, atol=1e-8, rtol=1e-7)
                assert result['chief_ray_surfaces']
                for chief in result['chief_ray_surfaces']:
                    e.check(f'chief final {jx},{jy}', chief['final_total'], reference, atol=1e-6, rtol=1e-6)
            await e.call('update_system_settings', dict(settings=dict(polarization=dict(unpolarized=True))))
            unpolarized = await e.finish(await e.call('run_analysis', dict(request=dict(kind='polarization_transmission'))))
            assert unpolarized['input_header']['unpolarized'] is True
            measured = unpolarized['fields'][0]['wavelengths'][0]['transmission']
            e.check('native unpolarized versus Fresnel', measured, reference, atol=1e-6, rtol=1e-6)
            e.check('native unpolarized versus orthogonal mean', measured, sum(batch_means) / 2,
                    atol=1e-8, rtol=1e-7)
        finally:
            await e.call('update_system_settings', dict(settings=dict(polarization=before['polarization'])))
            assert await e.call('get_system_settings') == before
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('transmission_pupil_reference', work))


@pytest.mark.zemax
def test_transmission_nonconstant_pupil_spherical_plano_fresnel():
    from tests.support.transmission_reference import spherical_plano_power

    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5876)], fields=[dict(x=0, y=0)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=20, thickness=5, semi_diameter=6, coating='',
                 replace_solves=True, solves=dict(material=dict(
                     mode='material_model', index_nd=1.5, abbe_vd=60, dpgf=0))),
            dict(surface=2, radius='Infinity', thickness=10, semi_diameter=6,
                 material='', coating='', replace_solves=True)]))
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        pupils = [(x/16,y/16) for y in range(-16,17) for x in range(-16,17) if x*x+y*y<=256]
        rays = [dict(hx=0, hy=0, px=x, py=y, wavelength=1) for x,y in pupils]
        try:
            for jx,jy in [(1.,0.), (0.,1.)]:
                await e.call('update_system_settings', dict(settings=dict(polarization=dict(
                    unpolarized=False, jx=jx, jy=jy, x_phase=0, y_phase=0))))
                result = await e.finish(await e.call('run_analysis', dict(request=dict(
                    kind='polarization_transmission'))))
                assert result['input_header']['jones']['jx'] == jx
                assert result['input_header']['jones']['jy'] == jy
                assert result['input_header']['grid'] == dict(nx=32, ny=32)
                trace = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                    rays=rays, polarization=dict(jx=jx, jy=jy)))))
                assert len(trace['rows']) == len(rays)
                references = [spherical_plano_power(5*x,5*y,jx=jx,jy=jy) for x,y in pupils]
                assert max(references)-min(references) > .005
                for i,(row,ref) in enumerate(zip(trace['rows'],references)):
                    assert row['state']=='succeeded' and row['error_code']==0
                    e.check(f'nonconstant Fresnel {jx},{jy} ray {i}', row['intensity'], ref,
                            atol=1e-6, rtol=1e-6)
                measured = result['fields'][0]['wavelengths'][0]['transmission']
                e.check(f'nonconstant full pupil {jx},{jy}', measured,
                        math.fsum(references)/len(references), atol=1e-6, rtol=1e-6)
            await e.call('update_system_settings', dict(settings=dict(polarization=dict(unpolarized=True))))
            unpolarized = await e.finish(await e.call('run_analysis', dict(request=dict(
                kind='polarization_transmission'))))
            assert unpolarized['input_header']['unpolarized'] is True
            reference = math.fsum(
                (spherical_plano_power(5*x,5*y,jx=1,jy=0)
                 + spherical_plano_power(5*x,5*y,jx=0,jy=1))/2 for x,y in pupils)/len(pupils)
            e.check('nonconstant full pupil unpolarized',
                    unpolarized['fields'][0]['wavelengths'][0]['transmission'], reference,
                    atol=1e-6, rtol=1e-6)
        finally:
            await e.call('update_system_settings', dict(settings=dict(polarization=before['polarization'])))
            assert await e.call('get_system_settings') == before
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('transmission_nonconstant_pupil', work))

@pytest.mark.zemax
def test_transmission_pupil_vignetting_inclusive_node_grid_reference():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0)],
            wavelengths=[dict(wavelength_um=.5876)],polarization=dict(unpolarized=True))))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',thickness=1,semi_diameter=6,coating='',replace_solves=True,
                 solves=dict(material=dict(mode='material_model',index_nd=1.5,abbe_vd=60,dpgf=0))),
            dict(surface=2,radius='Infinity',thickness=10,semi_diameter=6,material='',coating='',replace_solves=True)]))
        # Candidate defined before the five-radius control: 32 intervals, 33 nodes.
        pupil=[(x/16,y/16) for y in range(-16,17) for x in range(-16,17) if x*x+y*y<=256]
        assert len(pupil)==797
        reference=(1-((1.5-1)/(1.5+1))**2)**2
        for radius in [1.1,2.3,2.5,3.7,4.9]:
            await e.call('update_surfaces',dict(changes=[dict(surface=2,
                aperture=dict(type='CircularAperture',maximum_radius=radius))]))
            before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
            through=sum(25*(x*x+y*y)<=radius*radius+1e-12 for x,y in pupil)/len(pupil)
            measured=result['fields'][0]['wavelengths'][0]['transmission']
            e.check('inclusive node grid radius '+str(radius),measured,through*reference,atol=1e-6,rtol=1e-6)
            selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',field=1,wavelength=1,include_chief_ray=False))))
            e.check('selectable clipped native radius '+str(radius),selected['fields'][0]['wavelengths'][0]['transmission'],measured,atol=1e-6,rtol=1e-6)
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_vignetting_nodes',work))


@pytest.mark.zemax
def test_transmission_pupil_catalog_bulk_absorption():
    from pathlib import Path
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0)],
            wavelengths=[dict(wavelength_um=.5876)],polarization=dict(unpolarized=True))))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',thickness=1,semi_diameter=6,coating='',replace_solves=True,
                 solves=dict(material=dict(mode='material_model',index_nd=1.5,abbe_vd=60,dpgf=0))),
            dict(surface=2,radius='Infinity',thickness=10,semi_diameter=6,material='',coating='',
                 aperture=dict(type='CircularAperture',maximum_radius=2.5),replace_solves=True)]))
        catalog=Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF'
        lines=catalog.read_text(encoding='utf-8-sig').splitlines()
        start=next(i for i,line in enumerate(lines) if line.split()[:2]==['NM','N-BK7'])
        end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('NM ')),len(lines))
        block=lines[start:end]
        coefficients=next([float(v) for v in line.split()[1:7]] for line in block if line.startswith('CD '))
        point=next([float(v) for v in line.split()[1:4]] for line in block if line.startswith('IT ') and abs(float(line.split()[1])-.4)<1e-12)
        wave,internal,thickness=point
        n=math.sqrt(1+sum(coefficients[i]*wave*wave/(wave*wave-coefficients[i+1]) for i in (0,2,4)))
        expected=(1-((n-1)/(n+1))**2)**2*internal
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=wave)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',thickness=thickness,replace_solves=True),
             dict(surface=2,aperture=dict(type='CircularAperture',maximum_radius=6),replace_solves=True)]))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
        e.check('catalog exact IT wavelength/thickness times two Fresnel interfaces',
            result['fields'][0]['wavelengths'][0]['transmission'],expected,atol=1e-6,rtol=1e-6)
        selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',field=1,wavelength=1))))
        e.check('selectable bulk absorption versus independent reference',selected['fields'][0]['wavelengths'][0]['transmission'],expected,atol=1e-6,rtol=1e-6)
        assert selected['chief_ray_surfaces'][0]['final_total']==pytest.approx(expected,abs=1e-6)
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_catalog_absorption',work))

@pytest.mark.zemax
def test_transmission_selectable_pupil_native_equivalence_and_paging():
    from pathlib import Path
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
        adapted=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',method='ray_trace',include_chief_ray=False))),timeout_seconds=180)
        assert adapted['computation_method']=='native_batch_polarized_pupil_trace'
        assert adapted['actual_settings']['pupil_sample_count']==797
        for original,actual in zip(native['fields'],adapted['fields'],strict=True):
            for nw,aw in zip(original['wavelengths'],actual['wavelengths'],strict=True):
                e.check('Cooke selectable native full pupil '+str((actual['field_number'],aw['wavelength_um'])),
                    aw['transmission'],nw['transmission'],atol=1e-6,rtol=1e-6)
        selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',field=2,wavelength=2,sampling=16,
            polarization=dict(jx=1,jy=1,x_phase=30,y_phase=120)))),timeout_seconds=180)
        assert selected['actual_settings']['field_numbers']==[2]
        assert selected['actual_settings']['wavelength_numbers']==[2]
        assert selected['actual_settings']['sampling_nodes_per_diameter']==17
        assert len(selected['fields'])==len(selected['chief_ray_surfaces'])==1
        assert [r['surface'] for r in selected['chief_ray_surfaces'][0]['rows']]==list(range(1,len(surfaces['surfaces']) if isinstance(surfaces,dict) else len(surfaces)))
        tid=selected['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=tid,start=3,count=5))
        assert page['rows']==selected['rows'][3:8]
        image=e.folder/'selected-pupil.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(image))))
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        for child_id in selected['ray_trace_tasks']:
            status=await e.call('get_task_status',dict(task_id=child_id))
            assert status['state']=='succeeded' and not status.get('cleanup_warnings'),status
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_selectable_pupil',work))

@pytest.mark.zemax
def test_transmission_selectable_apodization_cancel_reuse_and_reload():
    import time
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5876)],fields=[dict(x=0,y=0)],
            polarization=dict(unpolarized=True))))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius='Infinity',thickness=1,semi_diameter=6,coating='',replace_solves=True,
            solves=dict(material=dict(mode='material_model',index_nd=1.5,abbe_vd=60,dpgf=0))),
            dict(surface=2,radius='Infinity',thickness=10,semi_diameter=6,material='',coating='',replace_solves=True,
                aperture=dict(type='CircularAperture',maximum_radius=2.5))]))
        for kind,factor in [('Uniform',0),('Gaussian',1)]:
            await e.call('update_system_settings',dict(settings=dict(aperture_options=dict(apodization_type=kind,apodization_factor=factor))))
            native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
            selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',method='ray_trace',include_chief_ray=False))))
            e.check(kind+' apodized selectable versus native',selected['fields'][0]['wavelengths'][0]['transmission'],native['fields'][0]['wavelengths'][0]['transmission'],atol=1e-6,rtol=1e-6)
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        task=await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',method='ray_trace',sampling=128)))
        task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state'] not in {'succeeded','failed','cancelled'},task
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+45
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.03);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        rejected=await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',method='native',field=1)),okay=False)
        assert rejected['error']['code']=='UNSUPPORTED_SETTING'
        q=dict(kind='polarization_transmission',field=1,wavelength=1,sampling=16,include_chief_ray=False)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        await e.call('save_lens_as',dict(path=str(e.folder/'transmission-reload.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'transmission-reload.zos')))
        repeated=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert repeated['fields']==result['fields']
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_selectable_lifecycle',work))

@pytest.mark.zemax
def test_transmission_selectable_jones_independent_fresnel_and_weighted_native_totals():
    from pathlib import Path
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',thickness=0,material='N-BK7',semi_diameter=20,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=10,material='',semi_diameter=20,replace_solves=True),
            dict(surface=3,semi_diameter=20,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=30)],
            wavelengths=[dict(wavelength_um=.55,weight=.3),dict(wavelength_um=.65,weight=.7)])))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        lines=(Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig').splitlines()
        start=next(i for i,line in enumerate(lines) if line.split()[:2]==['NM','N-BK7'])
        coefficients=next([float(v) for v in line.split()[1:7]] for line in lines[start+1:] if line.startswith('CD '))
        wave=.65;n=math.sqrt(1+sum(coefficients[i]*wave*wave/(wave*wave-coefficients[i+1]) for i in (0,2,4)))
        c=math.cos(math.radians(30));ct=math.sqrt(1-(.5/n)**2)
        ts=1-((c-n*ct)/(c+n*ct))**2;tp=1-((n*c-ct)/(n*c+ct))**2
        for pol in [dict(jx=1,jy=0),dict(jx=0,jy=1),dict(jx=1,jy=1,x_phase=30,y_phase=120)]:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',field=2,wavelength=2,sampling=8,polarization=pol))))
            reference=(pol['jx']**2*ts**2+pol['jy']**2*tp**2)/(pol['jx']**2+pol['jy']**2)
            e.check('selected Jones Fresnel '+str(pol),result['fields'][0]['wavelengths'][0]['transmission'],reference,atol=1e-6,rtol=1e-6)
            e.check('selected Jones chief '+str(pol),result['chief_ray_surfaces'][0]['final_total'],reference,atol=1e-6,rtol=1e-6)
        native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
        selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',method='ray_trace',include_chief_ray=False))))
        for nf,sf in zip(native['fields'],selected['fields'],strict=True):
            e.check('nonuniform wavelength weights field '+str(sf['field_number']),sf['total_transmission'],nf['total_transmission'],atol=1e-6,rtol=1e-6)
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_selectable_jones',work))

@pytest.mark.zemax
def test_transmission_selectable_field_vignetting_factor_equivalence():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0)],wavelengths=[dict(wavelength_um=.5876)],polarization=dict(unpolarized=True))))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius='Infinity',thickness=1,semi_diameter=6,replace_solves=True,
            solves=dict(material=dict(mode='material_model',index_nd=1.5,abbe_vd=60,dpgf=0))),
            dict(surface=2,radius='Infinity',thickness=10,semi_diameter=6,material='',replace_solves=True)]))
        for factors in [dict(vcx=.2,vcy=.3,vdx=0,vdy=0,van=0),dict(vcx=.2,vcy=.3,vdx=.1,vdy=-.1,van=30)]:
            await e.call('update_system_settings',dict(settings=dict(field_updates=[dict(number=1,**factors)])))
            before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
            native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission'))))
            selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission',field=1,wavelength=1,include_chief_ray=False))))
            e.check('field vignette '+str(factors),selected['fields'][0]['wavelengths'][0]['transmission'],native['fields'][0]['wavelengths'][0]['transmission'],atol=1e-6,rtol=1e-6)
            e.check('field vignette adjusted '+str(factors),selected['fields'][0]['total_vignetted_transmission'],native['fields'][0]['total_vignetted_transmission'],atol=1e-6,rtol=1e-6)
            assert native['fields'][0]['field_position_values']==[0.]
            assert native['fields'][0]['relative_vignetted_pupil_area']==pytest.approx(.56)
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('transmission_field_vignetting',work))
