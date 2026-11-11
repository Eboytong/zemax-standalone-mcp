import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from zemax_mcp.capability_index import CapabilitySearch, build_index, describe, search
from zemax_mcp.models import COMMAND_MODELS, Capabilities
from zemax_mcp.errors import ZemaxError


def test_complete_schema_index_and_detailed_metadata():
    entries = build_index()
    assert {x['name'] for x in entries if x['category'] == 'tool'} == set(COMMAND_MODELS)
    mapping = COMMAND_MODELS['run_analysis'].model_json_schema()['properties']['request']['discriminator']['mapping']
    assert {x['name'] for x in entries if x['category'] == 'analysis'} == set(mapping)
    assert len({x['capability_id'] for x in entries}) == len(entries)
    assert sum(x['detailed'] for x in entries) >= 20
    for item in entries:
        assert item['request_schema']['properties'] is not None
        assert item['detail_request']['capability_id'] == item['capability_id']
        assert item['availability']['static'] == '已适配'


def test_frozen_chinese_query_recall():
    cases = json.loads((Path(__file__).parents[1] / 'fixtures/capability_queries.json').read_text(encoding='utf-8'))
    assert len(cases) == 30
    misses = []
    for case in cases:
        found = {x['capability_id'] for x in search(case['query'])['items']}
        if not found.intersection(case['expected']):
            misses.append(case['query'])
    assert len(misses) <= 3, misses


def test_pagination_details_conditions_and_schema():
    all_entries = build_index()
    pages = [describe(Capabilities(topic='index', start=i, count=100)) for i in range(1, len(all_entries) + 1, 100)]
    assert sum(len(p['items']) for p in pages) == len(all_entries)
    detail = describe(Capabilities(topic='detail', capability_id='tool:run_fft_mtf'))
    assert 'cycles/mm' in detail['units']
    assert 'sampling' in detail['request_schema']['properties']
    dependency = describe(Capabilities(topic='dependencies', capability_id='tool:run_pop'))
    assert 'ZBF' in dependency['prerequisites']
    with pytest.raises(ZemaxError):
        describe(Capabilities(topic='detail', capability_id='tool:missing'))
    assert describe(Capabilities(topic='index', start=10000))['items'] == []


def test_search_filter_no_match_and_validation():
    assert all(x['category'] == 'analysis' for x in search('光线', category='analysis')['items'])
    assert search('zzzzqqqqxxxx')['items'] == []
    for invalid in ({'query': ''}, {'query': 'a', 'limit': 0}, {'query': 'a', 'limit': True}, {'query': 'a', 'category': 'x'}):
        with pytest.raises(ValidationError):
            CapabilitySearch(**invalid)


def test_offline_backend_dispatch(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from types import SimpleNamespace
    backend = Backend(Config(tmp_path, tmp_path), native=SimpleNamespace(system=None))
    result = backend.dispatch('search_capabilities', {'query': '镀膜反射率'})
    assert result['ok'], result
    assert result['data']['items'][0]['capability_id'] == 'tool:get_coating_rta'
    assert result['context']['session_id'] is None


def test_real_stdio_offline_discovery(tmp_path):
    import asyncio
    import sys
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    async def run():
        source = str(Path(__file__).parents[2] / 'src')
        boot = f'import sys;sys.path.insert(0,{source!r});from zemax_mcp.server import main;main()'
        params = StdioServerParameters(command=sys.executable, args=['-B', '-c', boot],
            env={'PYTHONPATH': source, 'PYTHONUTF8': '1', 'ZEMAX_OUTPUT_DIR': str(tmp_path)})
        async with Client(params, read_timeout_seconds=60) as client:
            tools = (await client.list_tools()).tools
            assert {tool.name for tool in tools} == set(COMMAND_MODELS)
            tool = next(t for t in tools if t.name == 'search_capabilities')
            assert tool.annotations.read_only_hint is True
            result = (await client.call_tool('search_capabilities', {'query': '镀膜反射率'})).structured_content
            assert result['ok'], result
            item = result['data']['items'][0]
            detail = (await client.call_tool('get_capabilities', item['detail_request'])).structured_content
            assert detail['ok'] and detail['data']['request_schema']
            status = (await client.call_tool('get_status')).structured_content
            assert status['ok'] and status['data']['connected'] is False
    asyncio.run(run())
