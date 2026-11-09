"""Queued native jobs for the STAR special analyses (D012).

Prepared, not started. The module state in ``development/evidence/CV-01`` and
``development/evidence/EXT-STAR/readiness193.json`` was recorded on 2026-11-06 and is
historical; every assertion here re-reads the availability live and records it, so a run
never reports a stale module state as the current one.
"""
import asyncio
from pathlib import Path

import pytest

from tests.support.native import execute
from tests.support.star_analysis_probe import KINDS, probe_kind

COOKE = str(Path.home() / 'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')


@pytest.mark.zemax
def test_star_analysis_availability_and_generic_creation():
    """Record the live module state; when enabled, probe generic creation and results."""
    async def work(e):
        await e.call('open_lens', dict(path=COOKE))
        before = await e.call('get_surfaces')
        attempts = [await probe_kind(e, kind) for kind in KINDS]
        assert await e.call('get_surfaces') == before
        e.checks.append(dict(attempts=attempts))
        assert len(attempts) == len(KINDS)
    asyncio.run(execute('d012r1', work))
