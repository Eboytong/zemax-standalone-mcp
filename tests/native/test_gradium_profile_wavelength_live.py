"""Q3 minimal native probe: which wavelength does the GrinProfile column report?

The manual states that parameter 3 (``n_ref``) is the vertex index at the
*glass-family* reference wavelength from ``SGRIN.DAT`` and that this is not
necessarily the system wavelength. The GrinProfile analysis exposes a wavelength
selector, so the returned index column must be attributed explicitly:

* reference-wavelength reading -> the two curves agree to floating point;
* system-wavelength reading    -> the two curves differ by the GSF dispersion
  step, of order 1e-3 index units between 0.58756 um and 0.55 um.

Both curves are native; the comparison is the discriminator. Diagnostic pass
(curve returned, provenance readback, model preserved, clean close) is asserted.
The attribution verdict is recorded as a numeric diagnostic, not asserted.

Run only through the runtime worker with --run-zemax.
"""
import asyncio
import json

import pytest

from tests.support.native import execute

PROFILE = 'G14SFN'
THICKNESS = 0.4
OFFSET = 1.0


@pytest.mark.zemax
def test_gradium_profile_wavelength_attribution():
    async def work(e):
        record = dict(experiment='Q3 wavelength attribution of the profile index column',
                      conditions=dict(profile=PROFILE, thickness=THICKNESS, offset=OFFSET,
                                      wavelengths_um=[0.58756, 0.55], show_index_vs='Z'),
                      predictions=dict(reference_wavelength='curves identical to floating point',
                                       system_wavelength='curves differ by the GSF dispersion step, order 1e-3'),
                      curves={})
        def save():
            (e.folder / 'attribution.json').write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str),
                                                      encoding='utf-8')
        save()
        await e.call('new_system')
        await e.call('insert_surfaces', dict(at=2))
        await e.call('update_system_settings', dict(settings=dict(
            wavelengths=[dict(wavelength_um=.58756), dict(wavelength_um=.55)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, radius=0, thickness=1, material='', semi_diameter=8, replace_solves=True),
            dict(surface=3, radius=0, material='', semi_diameter=8, replace_solves=True)]))
        await e.call('update_surfaces', dict(changes=[dict(surface=2, surface_type='Gradium', material=PROFILE,
            radius=0, thickness=THICKNESS, semi_diameter=6,
            parameters={1: .01, 2: OFFSET, 8: 3}, replace_solves=True)]))
        surfaces = await e.call('get_surfaces')
        settings = await e.call('get_system_settings')
        merit = await e.call('get_merit_function')
        for wavelength in (1, 2):
            request = dict(kind='grin_profile', surface=2, wavelength=wavelength, show_index_vs='Z',
                           minimum_z=0, maximum_z=THICKNESS, x_value=0, y_value=0)
            curve = await e.finish(await e.call('run_analysis', dict(request=request)))
            series = curve['series'][0]
            assert series['wavelength_number'] == wavelength
            source = curve['task']['settings']['source_surface']
            assert source['material'] == PROFILE and source['surface_type'] == 'Gradium'
            status = await e.call('get_task_status', dict(task_id=curve['task']['task_id']))
            assert status['state'] == 'succeeded' and status['close_attempted'] and not status.get('cleanup_warnings')
            record['curves'][str(wavelength)] = dict(
                x_unit=series['x_unit'], native_axes=series.get('native_axes'),
                x=series['x'], y=[row[0] for row in series['y']],
                display_reference_index=source['gradium']['reference_vertex_index'],
                requested_wavelength=curve['task']['settings']['requested']['wavelength'],
                native_wavelength=curve['task']['settings']['native'].get('Wavelength'))
            assert record['curves'][str(wavelength)]['native_wavelength'] == wavelength
            save()
        first, second = record['curves']['1'], record['curves']['2']
        assert first['x'] == second['x']
        differences = [abs(a - b) for a, b in zip(first['y'], second['y'], strict=True)]
        record['comparison'] = dict(
            points=len(differences), maximum_absolute_difference=max(differences),
            identical=differences and max(differences) == 0.0,
            reference_index_difference=[first['display_reference_index'], second['display_reference_index']],
            attribution='reference_wavelength' if max(differences) <= 1e-12 else 'system_wavelength',
            basis='1e-12 separates floating-point agreement from the order 1e-3 GSF dispersion step')
        record['native_settings'] = dict(
            wavelength_selector_first=first['native_wavelength'], wavelength_selector_second=second['native_wavelength'],
            note='IAS_GrinProfile.Wavelength readback recorded for both runs')
        assert record['comparison']['attribution'] == 'system_wavelength'
        assert record['comparison']['maximum_absolute_difference'] > 1e-3
        assert await e.call('get_surfaces') == surfaces
        assert await e.call('get_system_settings') == settings
        assert await e.call('get_merit_function') == merit
        record['preserved'] = True
        record['diagnostic_pass'] = True
        save()

    async def guarded(e):
        try:
            await work(e)
        except BaseException:
            await e.call('disconnect', okay=False)
            raise

    asyncio.run(execute('gradium_q3_wavelength_attribution', guarded))
