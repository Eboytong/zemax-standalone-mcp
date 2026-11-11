import asyncio

import pytest

from tests.support.native import execute
from tests.support.disclosure_cases import run_case


@pytest.mark.zemax
@pytest.mark.parametrize('mode',['full','compact'])
def test_disclosure_installed_or_source_native_roundtrip(mode,monkeypatch):
    monkeypatch.setenv('ZEMAX_TEST_TOOL_MODE',mode)
    async def work(e):
        parent=e.folder
        for case in ['sequential_mtf','sequential_rays','sequential_wavefront']:
            e.folder=parent/case;e.folder.mkdir()
            await run_case(e,case)
        e.folder=parent
        unknown=await e.call('search_capabilities',{'query':'zzzzqqqqxxxx'})
        assert unknown['items']==[]
    asyncio.run(execute('d025_disclosure_'+mode,work))
