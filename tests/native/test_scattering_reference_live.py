"""Sequential scatter pages: final adoption, geometric tracing and persistence."""
import asyncio
import json

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_sequential_builtin_scattering_adoption_and_reload():
    async def work(e):
        await e.model()
        await e.call('update_surfaces', {'changes': [
            {'surface': 0, 'thickness': 1},
            {'surface': 1, 'thickness': 1, 'semi_diameter': 5,
             'replace_solves': True},
        ]})
        names = await e.call('get_system_resources', {'request': {
            'kind': 'scattering_files', 'scattering_type': 'ABg',
        }})
        assert 'ABG-EXAMPLE' in names['items'], names
        cases = [
            {'type': 'None'},
            {'type': 'Lambertian', 'scatter_fraction': .3},
            {'type': 'Gaussian', 'scatter_fraction': .4, 'sigma': 1.25},
            {'type': 'ABg', 'abg_name': 'ABG-EXAMPLE'},
        ]
        records = []
        for request in cases:
            await e.call('update_surfaces', {'changes': [
                {'surface': 1, 'scattering': request},
            ]})
            before = (await e.call('get_surfaces', {'start': 1, 'count': 1}))['surfaces'][0]
            actual = before['properties']['scattering']
            for name, value in request.items():
                assert actual[name] == value, (request, actual)
            trace = await e.finish(await e.call('run_batch_ray_trace', {'request': {
                'input_mode': 'Direct', 'start_surface': 0, 'target_surface': 2,
                'rays': [dict(x=x, y=y, z=0, l=0, m=0, n=1)
                         for x, y in [(0, 0), (.3, -.4)]],
            }}))
            assert len(trace['rows']) == 2
            for row, point in zip(trace['rows'], [(0, 0), (.3, -.4)]):
                assert row['error_code'] == 0 and row['vignette_code'] == 0, row
                for got, expected in zip(row['position'][:2], point):
                    e.check(request['type'] + ' geometric trace position', got, expected)
                for got, expected in zip(row['direction'], (0, 0, 1)):
                    e.check(request['type'] + ' geometric trace direction', got, expected)
            settings = await e.call('get_system_settings')
            path = str(e.folder / (request['type'] + '.zos'))
            await e.call('save_lens_as', {'path': path})
            await e.call('open_lens', {'path': path})
            after = (await e.call('get_surfaces', {'start': 1, 'count': 1}))['surfaces'][0]
            assert before['properties']['scattering'] == after['properties']['scattering']
            assert before['cells'] == after['cells']
            assert (await e.call('get_system_settings'))['configuration'] == settings['configuration']
            records.append(dict(request=request, actual=actual, model=path,
                                trace_scope='sequential direct geometric ray trace',
                                reloaded=after['properties']['scattering']))
        before = await e.call('get_surfaces')
        revision = e.calls[-1]['response']['context']['model_revision']
        rejected = await e.call('update_surfaces', {'changes': [{
            'surface': 1, 'scattering': {'type': 'ABg', 'abg_name': '__missing268__'},
        }]}, okay=False)
        assert rejected['error']['code'] == 'INVALID_RESOURCE', rejected
        assert await e.call('get_surfaces') == before
        assert e.calls[-1]['response']['context']['model_revision'] == revision
        (e.folder / 'scatter-adoption.json').write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')

    asyncio.run(execute('scatter268_builtins', work))
