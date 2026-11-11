"""Independent catalog attenuation and main-path mirror/film power references."""
import asyncio
import math
from pathlib import Path
from uuid import uuid4

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_energy_catalog_absorption_film_mirror_and_outputs():
    name = 'D22' + uuid4().hex[:6].upper()
    resource = Path.home() / 'Documents/Zemax/Coatings' / (name + '.DAT')
    text = f'MATE {name}_N\n0.25 1.38 0\n0.8 1.38 0\nCOAT {name}_FILM\n{name}_N .1 1 0\n'
    resource.write_text(text, encoding='ascii')

    async def work(e):
        (e.folder / resource.name).write_text(text, encoding='ascii')
        await e.model()
        await e.call('update_system_settings', dict(settings=dict(aperture_value=5,
            material_catalogs=['SCHOTT'], files=dict(coating_file=resource.name),
            wavelengths=[dict(wavelength_um=.3), dict(wavelength_um=.546)])))
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, thickness=25, material='N-BK7', radius=0, is_stop=True,
                 semi_diameter=5, replace_solves=True),
            dict(surface=2, thickness=5, material='', radius=0, semi_diameter=5, replace_solves=True)]))
        material = await e.call('get_material_properties', dict(request=dict(catalog='SCHOTT', material='N-BK7')))
        request = dict(kind='sequential_energy_budget', input_power_w=2,
            rays=[dict(hx=0, hy=0, px=px, py=0, wavelength=wave, weight=weight)
                  for wave in (1, 2) for px, weight in ((0, 1), (.1, 2), (-.1, 3))],
            first_surface=1, last_surface=3)
        baseline = await e.call('get_surfaces')
        bare = await e.finish(await e.call('run_analysis', dict(request=request)), timeout_seconds=120)
        references = {}
        for wave, wavelength in ((1, .3), (2, .546)):
            table = next(row for row in material['internal_transmission']
                         if math.isclose(row['wavelength_um'], wavelength, abs_tol=5e-8))
            internal = {1: .05, 2: .996}[wave]
            e.check(f'catalog IT row {wave}', table['transmission'], internal, atol=5e-8, rtol=0)
            entry = await e.call('get_coating_rta', dict(request=dict(surface=1,
                conditions=[dict(wavelength=wave, angle_deg=0, direction='inward')])))
            exit_data = await e.call('get_coating_rta', dict(request=dict(surface=2,
                conditions=[dict(wavelength=wave, angle_deg=0, direction='inward')])))
            expected = entry['samples'][0]['transmission']['s'] * internal * exit_data['samples'][0]['transmission']['s']
            references[wave] = expected
            for ray in [row for row in bare['rows'] if row['surface'] == 2 and row['input']['wavelength'] == wave]:
                e.check(f'25 mm catalog absorption wave {wave} ray {ray["ray_id"]}',
                        ray['intensity'], expected, atol=1e-8, rtol=1e-6)
        e.check('weighted two-wavelength output W', bare['surfaces'][-1]['output_power_w'],
                sum(references.values()), atol=1e-8, rtol=1e-6)
        assert await e.call('get_surfaces') == baseline
        assert bare['resources']['closed_child_tasks'] == 6
        page = await e.call('get_task_result', dict(task_id=bare['task']['task_id'], start=2, count=3))
        assert len(page['rows']) == 3
        await e.call('export_analysis_image', dict(request=dict(task_id=bare['task']['task_id'],
            path=str(e.folder / 'surface-loss.png'))))
        await e.call('export_evaluation_report', dict(task_ids=[bare['task']['task_id']], title='逐面损耗独立参考'))
        await e.call('update_surfaces', dict(changes=[dict(surface=1, coating=name + '_FILM')]))
        film = await e.finish(await e.call('run_analysis', dict(request=request)), timeout_seconds=120)
        for wave in (1, 2):
            rta = await e.call('get_coating_rta', dict(request=dict(surface=1,
                conditions=[dict(wavelength=wave, angle_deg=0, direction='inward')])))
            for ray in [row for row in film['rows'] if row['surface'] == 1 and row['input']['wavelength'] == wave]:
                e.check(f'lossless film wave {wave}', ray['intensity'], rta['samples'][0]['transmission']['s'], atol=1e-8, rtol=1e-6)
        await e.call('new_system')
        await e.call('update_system_settings', dict(settings=dict(aperture_value=5,
            wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces', dict(changes=[dict(surface=1, radius=0,
            material='MIRROR', thickness=-5, semi_diameter=5, replace_solves=True)]))
        reflected = await e.finish(await e.call('run_analysis', dict(request=dict(
            kind='sequential_energy_budget', rays=[dict(hx=0, hy=0, px=0, py=0)],
            input_power_w=2, first_surface=1, last_surface=2))), timeout_seconds=120)
        mirror = await e.call('get_coating_rta', dict(request=dict(surface=1,
            conditions=[dict(wavelength=1, angle_deg=0, direction='inward')])))
        e.check('native mirror main-path power W', reflected['surfaces'][-1]['output_power_w'],
                2 * mirror['samples'][0]['reflection']['s'], atol=1e-8, rtol=1e-6)

    try:
        asyncio.run(execute('d022_absorption_film_mirror', work))
    finally:
        resource.unlink(missing_ok=True)
