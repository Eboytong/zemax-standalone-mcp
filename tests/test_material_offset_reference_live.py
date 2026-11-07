"""MaterialOffset checked against the documented model-glass difference."""
import asyncio
import json

import pytest

from support.native import execute
from support.material_reference import abbe, model_indices, sellmeier1, snell_indices


@pytest.mark.zemax
@pytest.mark.parametrize('band', ['visible', 'boundary', 'below_visible'])
def test_material_offset_dispersion_definition(band):
    async def work(e):
        await e.model()
        wavelengths = ([.5875618, .5876, .4861327, .4861, .6562725, .6563]
                       if band == 'visible' else
                       [.3 if band == 'boundary' else .29, .4861327, .5875618, .6562725])
        material = 'LITHOSIL-Q' if band == 'below_visible' else 'N-BK7'
        await e.call('update_system_settings', {'settings': {
            'wavelengths': [dict(wavelength_um=w) for w in wavelengths],
            'primary_wavelength': 2 if band == 'visible' else 3,
        }})
        await e.call('update_surfaces', {'changes': [
            {'surface': 0, 'thickness': 1},
            {'surface': 1, 'radius': 'Infinity', 'thickness': 1,
             'material': material, 'replace_solves': True},
        ]})
        catalog = await e.call('get_material_properties', {'request': {
            'catalog': 'SCHOTT', 'material': material,
            'include_internal_transmission': False, 'include_birefringence': False,
        }})
        props = catalog['properties']
        assert props['MaterialFormula'] == 'Sellmeier1'
        assert props['MinimumWavelength'] <= min(wavelengths) <= max(wavelengths) <= props['MaximumWavelength']
        base = [sellmeier1(w, catalog['coefficients']) for w in wavelengths]
        actual_base = await snell_indices(e, wavelengths)
        for measured, expected in zip(actual_base, base):
            e.check('catalog Sellmeier reference', measured, expected, atol=1e-10, rtol=1e-10)
        merit = await e.call('get_merit_function')
        use_model = band in {'visible', 'boundary'}
        model_base = await model_indices(e, wavelengths, props) if use_model else None
        records = []
        for dn, dv in [(0, 0), (.001, 0), (0, 1), (.001, 1), (-.001, -1)]:
            if use_model:
                plus = await model_indices(e, wavelengths, props, dn, dv)
                expected = [n + adjusted - initial
                            for n, adjusted, initial in zip(base, plus, model_base)]
                reference = 'Sellmeier1 + Model(Nd+dN,Vd+dV,dPgF) - Model(Nd,Vd,dPgF)'
            else:
                expected = [n + dn for n in base]
                reference = 'minimum wavelength 0.29 um: constant index offset; Vd offset inactive'
            await e.call('update_surfaces', {'changes': [{
                'surface': 1, 'material': material, 'replace_solves': True,
                'solves': {'material': {'mode': 'fixed'}},
            }]})
            request = dict(mode='material_offset', nd_offset=dn, vd_offset=dv)
            await e.call('update_surfaces', {'changes': [{
                'surface': 1, 'solves': {'material': request}, 'replace_solves': True,
            }]})
            measured = await snell_indices(e, wavelengths)
            for got, want in zip(measured, expected):
                e.check('offset index versus documented reference', got, want, atol=1e-6, rtol=1e-7)
            if band == 'visible':
                # The model difference defines the expected dispersion; its fitted
                # Abbe increment need not equal the input Vd parameter increment.
                e.check('offset rounded Abbe versus documented reference',
                        abbe(measured[1::2])-abbe(base[1::2]),
                        abbe(expected[1::2])-abbe(base[1::2]), atol=1e-5, rtol=1e-7)
            before = (await e.call('get_surfaces', {'start': 1, 'count': 1}))['surfaces'][0]
            solve = before['cells']['material']['solve']
            assert solve['type'] == 'MaterialOffset', solve
            assert solve['nd_offset'] == dn and solve['vd_offset'] == dv, solve
            settings = await e.call('get_system_settings')
            path = str(e.folder / ('offset_' + str(dn) + '_' + str(dv) + '.zos'))
            await e.call('save_lens_as', {'path': path})
            await e.call('open_lens', {'path': path})
            after = (await e.call('get_surfaces', {'start': 1, 'count': 1}))['surfaces'][0]
            assert before['cells'] == after['cells']
            assert (await e.call('get_system_settings'))['configuration'] == settings['configuration']
            assert await e.call('get_merit_function') == merit
            reloaded = await snell_indices(e, wavelengths)
            for got, want in zip(reloaded, expected):
                e.check('reloaded offset index', got, want, atol=1e-6, rtol=1e-7)
            records.append(dict(request=request, actual_solve=solve, reference=reference,
                                wavelengths=wavelengths, measured=measured,
                                expected=expected, reloaded=reloaded))
        (e.folder / 'offset-reference.json').write_text(
            json.dumps(dict(catalog=catalog, cases=records), ensure_ascii=False, indent=2),
            encoding='utf-8')

    asyncio.run(execute('material272_offset_' + band, work))
