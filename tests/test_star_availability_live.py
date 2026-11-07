"""Record native STAR readiness and preserve catalog reuse after utility errors."""
import asyncio,json
import pytest
from support.native import execute


@pytest.mark.zemax
def test_star_availability_and_material_reuse():
    async def work(e):
        await e.model();await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        control=await e.call('get_star_data',dict(request=dict(surface=1,data_kind='deformation')),okay=False)
        if control.get('ok')is False:assert control['error']['code']=='FEATURE_UNAVAILABLE'
        q=dict(catalog='SCHOTT',material='N-BK7',include_internal_transmission=False,include_birefringence=False)
        initial=await e.call('get_material_properties',dict(request=q))
        sampled=await e.call('get_material_properties',dict(request=dict(**q,star_samples=[dict(wavelength_um=.5875618)])),okay=False)
        if sampled.get('ok')is False:
            assert sampled['error']['code']=='INVALID_RESULT_DATA'and sampled['error']['details']['value']=='0.0'
        again=await e.call('get_material_properties',dict(request=q));assert again==initial
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
        (e.folder/'readiness.json').write_text(json.dumps(dict(control=control,material_utility=sampled,catalog_reuse=True,source_preserved=True),ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('star192_availability',work))
