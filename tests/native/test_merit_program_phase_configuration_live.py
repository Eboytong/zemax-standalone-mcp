"""Controlled GridPhase, per-configuration OPD groups and native wizard readback."""
import asyncio
import json
import math

import numpy as np
import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_merit_program_phase_surface_multiconfiguration_and_wizard():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces', dict(at=1, count=2))
        await e.call('update_system_settings', dict(settings=dict(
            aperture_value=5, material_catalogs=['SCHOTT'],
            fields=[dict(x=0, y=0), dict(x=.3, y=.7)],
            wavelengths=[dict(wavelength_um=.55)])))

        coefficient = .2
        radius = 5.
        spacing = .25
        path = e.folder / 'controlled-phase.dat'
        lines = ['65 65 0.25 0.25 0']
        for iy in range(65):
            for ix in range(65):
                x = (ix - 32) * spacing / radius
                y = (32 - iy) * spacing / radius
                phase_waves = coefficient * (x*x + y*y + .2*x + .1*y + .15*x*(x*x+y*y))
                dx = coefficient * (2*x + .2 + .15*(3*x*x+y*y)) / radius
                dy = coefficient * (2*y + .1 + .3*x*y) / radius
                dxy = coefficient * .3*y / radius**2
                lines.append(' '.join(map(str, (2 * math.pi * phase_waves,
                    2 * math.pi * dx, 2 * math.pi * dy, 2 * math.pi * dxy))))
        path.write_text('\n'.join(lines), encoding='ascii')
        await e.call('update_surfaces', dict(changes=[
            dict(surface=1, surface_type='GridPhase', import_file=str(path),
                 thickness=3, semi_diameter=5, replace_solves=True),
            dict(surface=2, radius=50, material='N-BK7', thickness=3, semi_diameter=5, replace_solves=True),
            dict(surface=3, radius=-50, thickness=48, semi_diameter=5, replace_solves=True)]))
        await e.call('update_configurations', dict(request=dict(
            actions=[dict(action='add', copy_current=True)],
            operands=[dict(type='THIC', parameters={'1': 3}, cells=[
                dict(configuration=1, value=48), dict(configuration=2, value=50)])])))
        await e.call('set_configuration', dict(configuration=1))
        configs_before = await e.call('get_configurations', dict(request={}))
        await e.call('save_lens_as', dict(path=str(e.folder / 'phase-mce.zos')))

        targets = [dict(kind='opd', reference=reference, configuration=configuration,
                        wavelength=1, hx=hx, hy=hy, rings=4, arms=16)
                   for configuration in (1, 2)
                   for hx, hy in ((0, 0), (.3, .7))
                   for reference in ('chief_ray', 'mean', 'mean_remove_tilt')]
        wizard = dict(kind='sequential', criterion='Wavefront', type='RMS',
                      reference='Centroid', use_gaussian_quadrature=True, rings=4,
                      use_all_fields=False, field_number=2,
                      use_all_configurations=False, configuration_number=1,
                      assume_axial_symmetry=False)
        result = await e.finish(await e.call('run_merit_program', dict(request=dict(
            wizard=wizard, targets=targets))), timeout_seconds=180)
        assert result['copy_closed'] and result['applied'] is False
        actual_wizard = result['wizard_settings']
        assert actual_wizard['Criterion'] == 'Wavefront'
        assert actual_wizard['Type'] == 'RMS'
        assert actual_wizard['Reference'] == 'Centroid'
        assert actual_wizard['Rings'] == 4
        assert actual_wizard['UseAllFields'] is False and actual_wizard['FieldNumber'] == 2
        assert actual_wizard['UseAllConfigurations'] is False and actual_wizard['ConfigurationNumber'] == 1
        assert actual_wizard['UseGaussianQuadrature'] is True

        rows = result['rows']
        evidence = []
        for group in result['groups']:
            req = group['request']
            conf = req['configuration']
            conf_rows = [row for row in rows[:group['start'] - 1] if row['type'] == 'CONF']
            assert conf_rows, (conf, group['index'])
            assert int(conf_rows[-1]['parameters']['2']['value']) == conf
            await e.call('set_configuration', dict(configuration=conf))
            trace = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(
                rays=[dict(wavelength=1, hx=req['hx'], hy=req['hy'],
                           px=node['px'], py=node['py']) for node in group['nodes']],
                opd=True))), timeout_seconds=120)
            direct = np.asarray([row['opd'] for row in trace['rows']], dtype=float)
            weights = np.asarray([node['area_weight'] for node in group['nodes']], dtype=float)
            if req['reference'] == 'chief_ray':
                reference = direct
            elif req['reference'] == 'mean':
                reference = direct - np.average(direct, weights=weights)
            else:
                matrix = np.column_stack((np.ones(len(group['nodes']),),
                    [node['px'] for node in group['nodes']],
                    [node['py'] for node in group['nodes']]))
                beta = np.linalg.lstsq(matrix * np.sqrt(weights[:, None]),
                                       direct * np.sqrt(weights), rcond=None)[0]
                reference = direct - matrix @ beta
            native = np.asarray([row['value'] for row in
                rows[group['start'] - 1:group['start'] - 1 + group['count']]])
            error = np.abs(native - reference)
            tolerance = 1e-5 + .01 * max(float(np.max(np.abs(reference))), 1e-12)
            assert float(np.max(error)) <= tolerance, dict(
                configuration=conf, reference=req['reference'],
                max_error=float(np.max(error)), tolerance=tolerance)
            evidence.append(dict(configuration=conf, opd_reference=req['reference'],
                                 hx=req['hx'], hy=req['hy'],
                                 max_error=float(np.max(error)), tolerance=tolerance,
                                 rms_residual_waves=group['rms_residual_waves']))

        assert [group['request']['configuration'] for group in result['groups']] == [1] * 6 + [2] * 6
        assert len([row for row in rows if row['type'] in ('OPDC', 'OPDM', 'OPDX')]) >= 6 * 4 * 16
        native_wizard = await e.finish(await e.call('run_optimization_wizard', dict(request=
            wizard | dict(apply=True))), timeout_seconds=120)
        assert native_wizard['applied'] and native_wizard['operands_after'] > 0
        assert native_wizard['settings_after']['Criterion'] == 'Wavefront'
        assert native_wizard['settings_after']['UseAllConfigurations'] is False
        assert native_wizard['settings_after']['ConfigurationNumber'] == 1
        assert native_wizard['settings_after']['UseAllFields'] is False
        assert native_wizard['settings_after']['FieldNumber'] == 2
        assert any(row['type'] in ('OPDX', 'OPDM', 'OPDC')
                   for row in native_wizard['operands']['operands'])
        native_eval = await e.call('evaluate_merit_function')
        assert math.isfinite(native_eval['merit_function'])
        await e.call('set_configuration', dict(configuration=1))
        assert await e.call('get_configurations', dict(request={})) == configs_before
        await e.call('open_lens', dict(path=str(e.folder / 'phase-mce.zos')))
        reloaded = await e.call('get_configurations', dict(request={}))
        assert reloaded['configuration_count'] == 2
        (e.folder / 'phase-mce-reference.json').write_text(json.dumps(dict(
            coefficient_waves=coefficient, pupil_radius_mm=radius,
            configurations=[1, 2], wizard_settings=actual_wizard, groups=evidence,
            max_error=max(item['max_error'] for item in evidence),
            tolerance='1e-5 waves + 1% of reference peak'), indent=2), encoding='utf-8')

    asyncio.run(execute('d020_phase_mce_wizard', work))
