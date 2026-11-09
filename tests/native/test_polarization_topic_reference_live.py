"""Native default polarization ray: independent Fresnel and per-surface batch identity."""
import asyncio
import json
import math
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('radius', ['Infinity', 20])
def test_polarization_ray_topic_plate_reference(radius):
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5876)], fields=[dict(x=0, y=0)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=radius, thickness=5, semi_diameter=6,
                 coating='', replace_solves=True, solves=dict(material=dict(
                     mode='material_model', index_nd=1.5, abbe_vd=60, dpgf=0))),
            dict(surface=2, radius='Infinity', thickness=10, semi_diameter=6,
                 material='', coating='', replace_solves=True)]))
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        reference = dict(index=1.5, wavelength_um=.5876,
                         radius=radius,
                         formula='Rs=((n1*ci-n2*ct)/(n1*ci+n2*ct))^2; Rp=((n2*ci-n1*ct)/(n2*ci+n1*ct))^2; T=1-R',
                         field_reference='normalized E_i conjugate(E_j); invariant under common propagation phase',
                         power_atol=1e-6, power_rtol=1e-6,
                         coherency_atol=1e-8, coherency_rtol=1e-7)
        (e.folder / 'reference.json').write_text(json.dumps(reference, indent=2), encoding='utf-8')
        try:
            for jx, jy, phase in [(1., 0., 0.), (0., 1., 0.), (1., 1., 90.)]:
                await e.call('update_system_settings', dict(settings=dict(polarization=dict(
                    unpolarized=False, jx=jx, jy=jy, x_phase=0, y_phase=phase))))
                result = await e.finish(await e.call('run_analysis', dict(request=dict(
                    kind='polarization_ray_trace'))))
                header = result['input_header']
                e.check('reported wavelength', header['wavelength_um'], .5876, atol=1e-9, rtol=0)
                assert header['jones'] == dict(jx=jx, jy=jy, x_phase_deg=0., y_phase_deg=phase)
                ray = dict(header['pupil'], wavelength=1)
                assert all(ray[k] is not None for k in ('hx', 'hy', 'px', 'py'))
                from tests.support.transmission_reference import spherical_plano_power
                power = ((1-((1.5-1)/(1.5+1))**2)**2 if radius == 'Infinity' else
                         spherical_plano_power(5*ray['px'], 5*ray['py'], jx=jx, jy=jy))
                e.check('total two-interface power', result['total_transmission'],
                        power, atol=1e-6, rtol=1e-6)
                assert [row['surface'] for row in result['rows']] == [1, 2, 3]
                channel_powers = [1., 1.]
                for row in result['rows']:
                    label = f'Jones {jx},{jy},{phase} surface {row["surface"]}'
                    n1, n2 = {1: (1., 1.5), 2: (1.5, 1.), 3: (1., 1.)}[row['surface']]
                    ci = abs(sum(a*b for a,b in zip(row['incident_direction'], row['normal'])))
                    ct = math.sqrt(1-(n1/n2)**2*(1-ci*ci))
                    reflectances = [((n1*ci-n2*ct)/(n1*ci+n2*ct))**2,
                                    ((n2*ci-n1*ct)/(n2*ci+n1*ct))**2]
                    for channel in (0, 1):
                        e.check(label+' R '+str(channel), row['reflectance'][channel], reflectances[channel],
                                atol=1e-6, rtol=1e-6)
                        e.check(label+' T '+str(channel), row['transmittance'][channel], 1-reflectances[channel],
                                atol=1e-6, rtol=1e-6)
                        channel_powers[channel] *= 1-reflectances[channel]
                    batch = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                        target_surface=row['surface'], rays=[ray],
                        polarization=dict(jx=jx, jy=jy, y_phase=phase)))))
                    traced = batch['rows'][0]
                    assert traced['error_code'] == 0
                    for i in range(3):
                        e.check(label+f' position {i}', traced['position'][i], row['surface_coordinates'][i])
                        e.check(label+f' direction {i}', traced['direction'][i], row['exit_direction'][i])
                    e.check(label+' cumulative power', traced['intensity'],
                            (jx*jx*channel_powers[0]+jy*jy*channel_powers[1])/(jx*jx+jy*jy),
                            atol=1e-6, rtol=1e-6)
                    native = [complex(a, b) for a, b in zip(
                        row['e_after_coating_xyz']['real'], row['e_after_coating_xyz']['imag'])]
                    electric = traced['electric_field']
                    batch_field = [complex(electric[k+'_real'], electric[k+'_imag']) for k in ('ex','ey','ez')]
                    native_norm = math.fsum(abs(v)**2 for v in native)
                    batch_norm = math.fsum(abs(v)**2 for v in batch_field)
                    assert native_norm > 0 and batch_norm > 0
                    for i in range(3):
                        for j in range(3):
                            a = native[i]*native[j].conjugate()/native_norm
                            b = batch_field[i]*batch_field[j].conjugate()/batch_norm
                            e.check(label+f' coherency {i},{j} real', a.real, b.real)
                            e.check(label+f' coherency {i},{j} imag', a.imag, b.imag)
                page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=1, count=1))
                assert page['rows'] == result['rows'][1:2] and page['next_start'] == 2
                status = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
                assert status['state'] == 'succeeded' and not status.get('cleanup_warnings')
            current = await e.call('get_system_settings')
            await e.call('save_lens_as', dict(path=str(e.folder/'ray-topic-reload.zos')))
            await e.call('open_lens', dict(path=str(e.folder/'ray-topic-reload.zos')))
            assert await e.call('get_system_settings') == current
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
            repeated = await e.finish(await e.call('run_analysis', dict(request=dict(kind='polarization_ray_trace'))))
            assert repeated['input_header'] == result['input_header']
            assert repeated['rows'] == result['rows']
            e.check('reloaded total transmission', repeated['total_transmission'], result['total_transmission'])
        finally:
            await e.call('update_system_settings', dict(settings=dict(polarization=before['polarization'])))
            assert await e.call('get_system_settings') == before
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('polarization_topic_plate_'+str(radius), work))


@pytest.mark.zemax
def test_fiber_topic_method_identity_and_reload():
    async def work(e):
        sample = Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', dict(path=str(sample)))
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        request = dict(kind='fiber_coupling_settings')
        result = await e.finish(await e.call('run_analysis', dict(request=request)))
        native_text = next(a['path'] for a in result['artifacts'] if a['kind'] == 'native_text')
        title = next(line.strip() for line in Path(native_text).read_text(encoding='utf-16').splitlines() if line.strip())
        assert result['integration_method_source']['title'] == title
        if '惠更斯' in title or 'Huygens' in title:
            assert result['integration_method'] == 'huygens'
        elif '光线积分' in title or 'Ray-based' in title:
            assert result['integration_method'] == 'ray_based'
        else:
            assert result['integration_method'] is None
        assert result['receiver']['na_x'] > 0 and result['receiver']['na_y'] > 0
        assert result['selection']['writable_selectors'] == []
        task_id = result['task']['task_id']
        page = await e.call('get_task_result', dict(task_id=task_id, start=1, count=1))
        assert page['rows'] == result['rows'][1:2] and page['next_start'] == 2
        status = await e.call('get_task_status', dict(task_id=task_id))
        assert status['state'] == 'succeeded' and not status.get('cleanup_warnings')
        await e.call('save_lens_as', dict(path=str(e.folder/'fiber-topic-reload.zos')))
        await e.call('open_lens', dict(path=str(e.folder/'fiber-topic-reload.zos')))
        repeated = await e.finish(await e.call('run_analysis', dict(request=request)))
        for key in ('input_header', 'receiver', 'efficiencies', 'integration_method', 'integration_method_source'):
            assert repeated[key] == result[key]
        assert await e.call('get_system_settings') == before
        assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('fiber_topic_method', work))


@pytest.mark.zemax
def test_fiber_operand_selection_paging_reload_and_cancel():
    async def work(e):
        sample = Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens', dict(path=str(sample)))
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        merit = await e.call('get_merit_function')
        native = await e.finish(await e.call('run_analysis', dict(request=dict(kind='fiber_coupling_settings'))))
        request = dict(kind='fiber_coupling_settings', method='operand', wavelength=2,
                       field=1, sampling=64, integration='huygens', receiver_na=.1)
        result = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert result['computation_method'] == 'native_FICL_GetOperandValue'
        assert result['efficiencies']['total_coupling'] == pytest.approx(native['efficiencies']['total_coupling'], abs=5e-7)
        assert abs(result['consistency']['residual']) < 1e-12
        assert result['actual_settings']['wavelength']['wavelength_um'] == .55
        page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=1, count=1))
        assert page['rows'] == result['rows'][1:2] and page['next_start'] == 2
        changed = await e.finish(await e.call('run_analysis', dict(request=request | dict(receiver_na=.05))))
        assert abs(changed['efficiencies']['total_coupling'] - result['efficiencies']['total_coupling']) > .01
        await e.call('save_lens_as', dict(path=str(e.folder/'fiber-operand.zos')))
        await e.call('open_lens', dict(path=str(e.folder/'fiber-operand.zos')))
        repeated = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert repeated['efficiencies'] == result['efficiencies']
        task = await e.call('run_analysis', dict(request=request))
        cancelled = await e.call('cancel_task', dict(task_id=task['task_id']))
        status = await e.call('get_task_status', dict(task_id=task['task_id']))
        assert status['state'] in {'cancelled', 'succeeded'}, (cancelled, status)
        reused = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert reused['efficiencies'] == result['efficiencies']
        assert await e.call('get_system_settings') == before
        assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
        assert await e.call('get_merit_function') == merit
    asyncio.run(execute('fiber_operand', work))


@pytest.mark.zemax
def test_fiber_operand_independent_gaussian_pupil_reference():
    from tests.support.fiber_reference import circular_pupil_coupling

    async def work(e):
        for finite in (False, True):
            await e.call('new_system')
            await e.call('update_system_settings', dict(settings=dict(aperture_value=1., fields=[dict(x=0., y=0.)], wavelengths=[dict(wavelength_um=.55)])))
            distance = 200. if finite else 100.
            changes = [dict(surface=1, surface_type='Paraxial', parameters={'1': 100.}, thickness=distance, semi_diameter=.5, replace_solves=True),
                       dict(surface=2, semi_diameter=5., replace_solves=True)]
            if finite:
                changes.append(dict(surface=0, thickness=200., replace_solves=True))
            await e.call('update_surfaces', dict(changes=changes))
            before = await e.call('get_system_settings')
            surfaces = await e.call('get_surfaces', dict(start=0, count=100))
            na = .5 / distance
            scenarios = [(True, na, factor * na) for factor in (.5, 1., 2.)]
            if finite:
                scenarios += [(False, factor * na, na) for factor in (.5, 1., 2.)]
            for ignore, source_na, receiver_na in scenarios:
                expected = circular_pupil_coupling(.5, distance, receiver_na, **({} if ignore else dict(object_distance=200., source_na=source_na)))
                for sampling in (64, 128, 256):
                    request = dict(kind='fiber_coupling_settings', method='operand', integration='fast', sampling=sampling,
                                   field=1, wavelength=1, ignore_source=ignore, source_na=source_na, receiver_na=receiver_na)
                    result = await e.finish(await e.call('run_analysis', dict(request=request)))
                    e.check(f'finite={finite} ignore={ignore} NA={source_na},{receiver_na} sampling={sampling}',
                            result['efficiencies']['total_coupling'], expected, atol=5e-4, rtol=0)
                    assert abs(result['consistency']['residual']) < 1e-12
            assert await e.call('get_system_settings') == before
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('fiber_operand_reference', work))


@pytest.mark.zemax
def test_polarization_ray_coda_selects_field_wave_surface_and_matches_batch_field():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.5876)], fields=[dict(x=0, y=0)],
            polarization=dict(unpolarized=False, jx=0, jy=1, x_phase=0, y_phase=0))))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius='Infinity', thickness=5, semi_diameter=6, coating='',
                 replace_solves=True, solves=dict(material=dict(mode='material_model', index_nd=1.5, abbe_vd=60, dpgf=0))),
            dict(surface=2, radius='Infinity', thickness=10, semi_diameter=6, material='', coating='', replace_solves=True)]))
        baseline = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces', dict(start=0, count=100))
        topic = await e.finish(await e.call('run_analysis', dict(request=dict(kind='polarization_ray_trace'))))
        topic_rows = {row['surface']: row for row in topic['rows']}
        for selected_surface, trace_surface in [(1, 1), (2, 2), (0, 3)]:
            request = dict(kind='polarization_ray_trace', method='operand', field=1, wavelength=1,
                           surface=selected_surface, pupil_x=0, pupil_y=1)
            result = await e.finish(await e.call('run_analysis', dict(request=request)))
            selected = {row['quantity']: row['value'] for row in result['rows']}
            native_row = topic_rows[trace_surface]
            e.check(f'CODA {trace_surface} polarized intensity', selected['polarized_transmitted_intensity'],
                    native_row['intensity_after'], atol=1e-9, rtol=1e-8)
            for name, expected in zip(('ellipse_major_axis', 'ellipse_minor_axis'), native_row['ellipse_axes']):
                e.check(f'CODA {trace_surface} {name}', selected[name], expected, atol=1e-9, rtol=1e-8)
            delta = (selected['ellipse_angle_deg'] - native_row['ellipse_angle']['deg'] + 90) % 180 - 90
            e.check(f'CODA {trace_surface} ellipse angle', delta, 0, atol=1e-6, rtol=0)
            for polarization, index in [('s', 0), ('p', 1)]:
                for quantity in ('reflectance', 'transmittance'):
                    e.check(f'CODA {trace_surface} {polarization} {quantity}',
                            selected[f'{polarization}_{quantity}'], native_row[quantity][index],
                            atol=1e-9, rtol=1e-8)
                for quantity in ('transmission', 'reflection'):
                    amplitude = native_row[f'field_amplitude_{quantity}_{polarization}']
                    for component in ('real', 'imag'):
                        e.check(f'CODA {trace_surface} {polarization} {quantity} {component}',
                                selected[f'{polarization}_{quantity}_amplitude_{component}'], amplitude[component],
                                atol=1e-9, rtol=1e-8)
                e.check(f'CODA {trace_surface} {polarization} absorption',
                        selected[f'{polarization}_absorption'],
                        1 - native_row['reflectance'][index] - native_row['transmittance'][index],
                        atol=1e-9, rtol=0)
            for index, axis in enumerate(('x', 'y', 'z')):
                if native_row['amplitude_xyz'][index] > 1e-10:
                    expected_phase = math.degrees(native_row['phase_xyz'][index])
                    difference = (selected[f'phase_{axis}_deg'] - expected_phase + 180) % 360 - 180
                    e.check(f'CODA {trace_surface} {axis} phase degrees', difference, 0, atol=1e-6, rtol=0)
            page = await e.call('get_task_result', dict(task_id=result['task']['task_id'], start=14, count=3))
            assert page['rows'] == result['rows'][14:17] and page['next_start'] == 17
            status = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
            assert status['state'] == 'succeeded' and not status.get('cleanup_warnings')
            ray = dict(hx=0., hy=0., px=0., py=1., wavelength=1)
            batch = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                target_surface=trace_surface, rays=[ray], polarization=dict(jx=0, jy=1)))))
            field = batch['rows'][0]['electric_field']
            for axis in ('x', 'y', 'z'):
                e.check(f'surface {selected_surface} E{axis} real', selected[f'e{axis}_real'], field[f'e{axis}_real'], atol=1e-6, rtol=1e-6)
                e.check(f'surface {selected_surface} E{axis} imag', selected[f'e{axis}_imag'], field[f'e{axis}_imag'], atol=1e-6, rtol=1e-6)
            assert result['actual_settings']['field']['number'] == 1
            assert result['actual_settings']['wavelength']['wavelength_um'] == .5876
        assert await e.call('get_system_settings') == baseline
        assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('polarization_coda', work))


@pytest.mark.zemax
def test_polarization_coda_selection_matrix_reload_and_cancel():
    async def work(e):
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.4861), dict(wavelength_um=.6563)],
            fields=[dict(x=0, y=0), dict(x=0, y=5)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=20, thickness=5, semi_diameter=6, coating='', replace_solves=True,
                 solves=dict(material=dict(mode='material_model', index_nd=1.5, abbe_vd=60, dpgf=0))),
            dict(surface=2, radius='Infinity', thickness=10, semi_diameter=6, material='', coating='', replace_solves=True)]))
        unpolarized = {}
        for phase in (37., 90.):
            await e.call('update_system_settings', dict(settings=dict(polarization=dict(
                unpolarized=False, jx=1, jy=1, x_phase=0, y_phase=phase))))
            baseline = await e.call('get_system_settings')
            surfaces = await e.call('get_surfaces', dict(start=0, count=100))
            for field_number in (1, 2):
                for wavelength in (1, 2):
                    request = dict(kind='polarization_ray_trace', method='operand', field=field_number,
                                   wavelength=wavelength, surface=0, pupil_x=.25, pupil_y=.4)
                    result = await e.finish(await e.call('run_analysis', dict(request=request)))
                    values = {row['quantity']: row['value'] for row in result['rows']}
                    batch = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                        target_surface=3, rays=[dict(hx=0, hy=field_number-1, px=.25, py=.4, wavelength=wavelength)],
                        polarization=dict(jx=1, jy=1, x_phase=0, y_phase=phase)))))
                    assert batch['rows'][0]['error_code'] == 0
                    electric = batch['rows'][0]['electric_field']
                    label = f'field={field_number} wave={wavelength} JonesPhase={phase}'
                    e.check(f'{label} polarized power', values['polarized_transmitted_intensity'],
                            batch['rows'][0]['intensity'], atol=1e-9, rtol=1e-8)
                    key = (field_number, wavelength)
                    if key not in unpolarized:
                        powers = []
                        for jx, jy in ((1, 0), (0, 1)):
                            reference = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                                target_surface=3, rays=[dict(hx=0, hy=field_number-1, px=.25, py=.4, wavelength=wavelength)],
                                polarization=dict(jx=jx, jy=jy)))))
                            assert reference['rows'][0]['error_code'] == 0
                            powers.append(reference['rows'][0]['intensity'])
                        unpolarized[key] = sum(powers) / 2
                    e.check(f'{label} unpolarized power', values['unpolarized_transmitted_intensity'],
                            unpolarized[key], atol=1e-9, rtol=1e-8)
                    ex = complex(electric['ex_real'], electric['ex_imag'])
                    ey = complex(electric['ey_real'], electric['ey_imag'])
                    s0 = abs(ex)**2 + abs(ey)**2
                    s1 = abs(ex)**2 - abs(ey)**2
                    s2 = 2 * (ex * ey.conjugate()).real
                    discriminant = math.hypot(s1, s2)
                    for name, squared in (('ellipse_major_axis', (s0+discriminant)/2),
                                          ('ellipse_minor_axis', (s0-discriminant)/2)):
                        e.check(f'{label} {name}', values[name], math.sqrt(max(0, squared)), atol=1e-8, rtol=1e-7)
                    if discriminant > 1e-12 * s0:
                        orientation = math.degrees(math.atan2(s2, s1)) / 2
                        delta = (values['ellipse_angle_deg'] - orientation + 90) % 180 - 90
                        e.check(f'{label} ellipse orientation', delta, 0, atol=1e-6, rtol=0)
                    for axis in ('x', 'y', 'z'):
                        for component in ('real', 'imag'):
                            key = f'e{axis}_{component}'
                            e.check(f'{label} {key}', values[key], electric[key], atol=1e-6, rtol=1e-6)
                        z = complex(values[f'e{axis}_real'], values[f'e{axis}_imag'])
                        if abs(z) > 1e-10:
                            expected = math.degrees(math.atan2(z.imag, z.real))
                            delta = (values[f'phase_{axis}_deg'] - expected + 180) % 360 - 180
                            e.check(f'{label} phase {axis}', delta, 0, atol=1e-6, rtol=0)
                    assert result['actual_settings']['field']['number'] == field_number
                    assert result['actual_settings']['wavelength']['number'] == wavelength
                    relative = values['phase_x_deg'] - values['phase_y_deg']
                    delta = (values['phase_xy_deg'] - relative + 180) % 360 - 180
                    e.check(f'{label} phase x minus y', delta, 0, atol=1e-6, rtol=0)
            assert await e.call('get_system_settings') == baseline
            assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
        invalid = await e.call('run_analysis', dict(request=dict(request, field=3)), okay=False)
        assert not invalid['ok'] and invalid['error']['code'] == 'INDEX_OUT_OF_RANGE'
        task = await e.call('run_analysis', dict(request=request))
        cancelled = await e.call('cancel_task', dict(task_id=task['task_id']))
        while cancelled['state'] not in {'succeeded', 'failed', 'cancelled'}:
            await asyncio.sleep(.02)
            cancelled = await e.call('get_task_status', dict(task_id=task['task_id']))
        assert cancelled['state'] in {'succeeded', 'cancelled'}
        repeated = await e.finish(await e.call('run_analysis', dict(request=request)))
        saved = str(e.folder/'selected-ray.zos')
        await e.call('save_lens_as', dict(path=saved))
        await e.call('open_lens', dict(path=saved))
        reloaded = await e.finish(await e.call('run_analysis', dict(request=request)))
        for before, after in zip(repeated['rows'], reloaded['rows']):
            e.check('reload '+before['quantity'], after['value'], before['value'], atol=1e-10, rtol=1e-10)
        assert await e.call('get_system_settings') == baseline
        assert await e.call('get_surfaces', dict(start=0, count=100)) == surfaces
    asyncio.run(execute('polarization_coda_selection_matrix', work))
