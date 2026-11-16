"""Probe each remaining STAR analysis independently on 2026 R1."""
import asyncio
import pytest
from tests.support.native import execute
from tests.support.star_analysis_probe import probe_kind
from tests.support.star_2026r1_fixture import prepared_star_lens


@pytest.mark.zemax
@pytest.mark.parametrize('kind',[
    'star_align_check','star_sys_viewer','star_2d_def_plot',
    'star_perf_change','star_index_vs_temp','star_inspect_fea',
])
def test_2026r1_individual_star_analysis(kind):
    lens=prepared_star_lens(fitted=True)
    async def work(e):
        await e.call('open_lens',dict(path=str(lens)))
        await probe_kind(e,kind)
    asyncio.run(execute('2026r1_'+kind,work))
