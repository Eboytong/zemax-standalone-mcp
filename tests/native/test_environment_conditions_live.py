import asyncio

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_environment_condition_rejection_precedes_write_and_enabled_values_are_adopted():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings', dict(settings=dict(adjust_index_to_environment=False)))
        settings = await e.call('get_system_settings')
        status = await e.call('get_status')
        response = await e.call('update_system_settings', dict(settings=dict(pressure_atm=0)), okay=False)
        assert response['error']['code'] == 'SETTING_INACTIVE'
        assert response['error']['details']['partial_changes_possible'] is False
        assert await e.call('get_system_settings') == settings
        after = await e.call('get_status')
        assert after['model_revision'] == status['model_revision']
        try:
            actual = await e.call('update_system_settings', dict(settings=dict(
                adjust_index_to_environment=True, pressure_atm=0, temperature_c=10)))
            assert actual['pressure_atm'] == 0
            assert actual['temperature_c'] == 10
            assert actual['adjust_index_to_environment'] is True
        finally:
            await e.call('update_system_settings', dict(settings=dict(adjust_index_to_environment=False)))
            assert await e.call('get_system_settings') == settings
    asyncio.run(execute('environment_conditions', work))
