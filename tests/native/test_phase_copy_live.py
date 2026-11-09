"""Selected native phase reports, frozen source geometry and stdio ownership."""
import asyncio
import math
from pathlib import Path

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_phase_copy_selection_geometry_paging_reload_and_close():
    async def work(e):
        await e.call('open_lens', dict(path=str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_system_settings', dict(settings=dict(
            fields=[dict(x=0., y=0.), dict(x=0., y=5., weight=.7)],
            wavelengths=[dict(wavelength_um=.4861327, weight=.6), dict(wavelength_um=.6562725)],
            primary_wavelength=2)))
        baseline = {name: await e.call(name) for name in ('get_system_settings', 'get_surfaces', 'get_merit_function')}
        source = str(e.folder / 'source.zos')
        await e.call('save_lens_as', dict(path=source))
        request = dict(kind='phase_aberration', field=2, wavelength=2,
                       polarization=dict(jx=1., jy=1., x_phase=17., y_phase=73.))
        results = []
        for field, wave in ((1, 2), (2, 2)):
            result = await e.finish(await e.call('run_analysis', dict(request=dict(request, field=field, wavelength=wave))))
            results.append(result)
            actual = result['actual_settings']
            assert actual['geometry_after_analysis']['passed']
            assert actual['source_geometry_after_analysis']['passed']
            assert len(result['rows']) == 401
            e.check(f'field {field} wave {wave} adopted', result['input_header']['wavelength_um'],
                    baseline['get_system_settings']['wavelengths'][wave - 1]['wavelength_um'], atol=.000051, rtol=0)
            e.check(f'field {field} wave {wave} position', result['input_header']['field_position']['y'],
                    baseline['get_system_settings']['fields'][field - 1]['y'], atol=.0051, rtol=0)
            status = await e.call('get_task_status', dict(task_id=result['task']['task_id']))
            assert status['close_attempted'] and not status.get('cleanup_warnings')
            assert status['settings']['resource_close'] == dict(analysis_closed=True, system_closed=True)
            for name, value in baseline.items():
                assert await e.call(name) == value
        selected = results[1]
        page = await e.call('get_task_result', dict(task_id=selected['task']['task_id'], start=7, count=11))
        assert page['rows'] == selected['rows'][7:18] and page['next_start'] == 18
        await e.call('export_analysis_image', dict(request=dict(task_id=selected['task']['task_id'], path=str(e.folder / 'selected-phase.png'))))
        # Independent working-model control: freeze the same evaluated geometry,
        # then run the existing default native topic with the chosen inputs.
        changes = [dict(surface=c['surface'], replace_solves=True, **{c['cell']: c['value']})
                   for c in selected['actual_settings']['frozen_cells'] if math.isfinite(float(c['value']))]
        await e.call('update_surfaces', dict(changes=changes))
        await e.call('update_system_settings', dict(settings=dict(
            fields=[dict(x=0., y=5., weight=.7), dict(x=0., y=0.)], primary_wavelength=2,
            polarization=dict(unpolarized=False, **request['polarization']))))
        reference = await e.finish(await e.call('run_analysis', dict(request=dict(kind='phase_aberration'))))
        for row, expected in zip(selected['rows'], reference['rows'], strict=True):
            for section in ('sagittal', 'tangential'):
                for component in ('x_phase', 'y_phase'):
                    e.check(f'{section} {component} pupil {row["pupil"]}', row[section][component],
                            expected[section][component], atol=1e-9, rtol=0)
        await e.call('open_lens', dict(path=source))
        reloaded = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert reloaded['rows'] == selected['rows']
        rejected = await e.call('run_analysis', dict(request=dict(request, field=3)), okay=False)
        assert rejected['error']['code'] == 'INDEX_OUT_OF_RANGE'
        rejected_wave = await e.call('run_analysis', dict(request=dict(request, wavelength=1)), okay=False)
        assert rejected_wave['error']['code'] == 'SETTING_REJECTED'
        details = rejected_wave['error']['details']
        assert details['comparisons'] and any(not c['passed'] for c in details['comparisons'])
        assert details['actual_settings']['resource_close'] == dict(analysis_closed=False, system_closed=True)
        for name, value in baseline.items():
            assert await e.call(name) == value
        task = await e.call('run_analysis', dict(request=request))
        terminal = await e.call('cancel_task', dict(task_id=task['task_id']))
        while terminal['state'] not in {'succeeded', 'failed', 'cancelled'}:
            await asyncio.sleep(.02)
            terminal = await e.call('get_task_status', dict(task_id=task['task_id']))
        assert terminal['state'] in {'succeeded', 'cancelled'}
        assert terminal['settings']['resource_close'] == dict(analysis_closed=True, system_closed=True)
        e.checks.append(dict(label='native cancellation request and close', terminal=terminal, passed=True))
        await e.call('update_system_settings', dict(settings=dict(fields=[dict(x=0., y=0.), dict(x=5., y=0.)])))
        x_field = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert x_field['input_header']['field_position']['x'] == 5.
        assert x_field['input_header']['field_position']['y'] == 0.
        x_status = await e.call('get_task_status', dict(task_id=x_field['task']['task_id']))
        assert x_status['settings']['resource_close'] == dict(analysis_closed=True, system_closed=True)
        await e.call('open_lens', dict(path=source))
        reused = await e.finish(await e.call('run_analysis', dict(request=request)))
        assert reused['rows'] == selected['rows']
        for name, value in baseline.items():
            assert await e.call(name) == value
        e.checks.append(dict(label='field/Jones selection, source solves, report reference, paging, reload, nonprimary refusal and close', passed=True,
                             frozen=selected['actual_settings']['frozen_cells']))
    asyncio.run(execute('phase_copy', work))
