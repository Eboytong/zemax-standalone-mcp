import asyncio
import pytest
from support.native import execute
from zemax_mcp.extension_resources import EXTENSION_FOLDERS


@pytest.mark.zemax
def test_native_extension_resource_roots_and_paging():
    async def work(e):
        await e.model()
        before = await e.call('get_system_settings')
        surfaces = await e.call('get_surfaces')
        revision = e.calls[-1]['response']['context']['model_revision']
        for role in [*EXTENSION_FOLDERS, 'zpl']:
            result = await e.call('get_system_resources', {'request': {
                'kind': 'extension_files', 'extension_role': role, 'count': 2}})
            assert result['extension_role'] == role
            assert 'directory' in result
            assert len(result['items']) <= 2
            assert e.calls[-1]['response']['context']['model_revision'] == revision
            if result.get('next_start') is not None:
                page = await e.call('get_system_resources', {'request': {
                    'kind': 'extension_files', 'extension_role': role,
                    'start': result['next_start'], 'count': 2}})
                assert page['directory'] == result['directory']
                assert len(page['items']) <= 2
        assert await e.call('get_system_settings') == before
        assert await e.call('get_surfaces') == surfaces
        assert e.calls[-1]['response']['context']['model_revision'] == revision
    asyncio.run(execute('extension_resources', work))
