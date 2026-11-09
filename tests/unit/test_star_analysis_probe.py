"""Offline coverage for the STAR analysis probe classifier.

A fake Evidence object supplies the public success/failure envelopes so the three
paths are proven without OpticStudio: a legal module-disabled gate, an arbitrary
error that must fail with the full response, and a normal scatter run.
"""
import asyncio
import json

import pytest

from tests.support.star_analysis_probe import KINDS, module_unavailable, probe_kind


class FakeEvidence:
    def __init__(self, response, finished=None):
        self.response = response
        self.finished = finished
        self.calls = []

    async def call(self, name, args=None, okay=True):
        self.calls.append(dict(tool=name, arguments=args, okay=okay))
        return self.response

    async def finish(self, task):
        return self.finished


def run(evidence, kind='star_align_check'):
    return asyncio.run(probe_kind(evidence, kind))


def unavailable(enabled):
    return {"ok": False, "data": None, "error": {
        "code": "FEATURE_UNAVAILABLE",
        "message": "本机 STAR 模块未启用。",
        "details": {"analysis": "star_align_check",
                    "availability": {"enabled": enabled, "source": "live read"}}}}


def test_module_unavailable_is_the_only_expected_gate():
    record = run(FakeEvidence(unavailable(False)))
    assert record['outcome'] == 'module_unavailable'
    assert record['error_code'] == 'FEATURE_UNAVAILABLE'
    assert record['availability']['enabled'] is False
    assert module_unavailable(unavailable(False)['error']) is True


def test_feature_unavailable_without_disabled_flag_fails():
    # Same code but availability enabled is not False: not the module-disabled precondition.
    with pytest.raises(AssertionError) as info:
        run(FakeEvidence(unavailable(True)))
    assert 'unexpected run_analysis failure' in str(info.value)
    assert 'FEATURE_UNAVAILABLE' in str(info.value)


def test_arbitrary_error_fails_and_preserves_full_response():
    response = {"ok": False, "data": None, "error": {
        "code": "ANALYSIS_FAILED", "message": "boom",
        "details": {"analysis": "star_align_check", "availability": {"enabled": True}}}}
    with pytest.raises(AssertionError) as info:
        run(FakeEvidence(response))
    text = str(info.value)
    assert 'unexpected run_analysis failure' in text
    assert 'ANALYSIS_FAILED' in text and 'boom' in text


def test_success_records_new_scatter_key_and_structured_data():
    finished = {"structured_data_available": True, "native_analysis": "STARAlignCheck",
                "analysis_id": 155, "text_export": {"exported": True, "path": "/tmp/x.txt"},
                "series": [{"point_count": 2}], "grids": [],
                "scatter": [{"count": 3, "points": [{"x": 0, "y": 0}]}]}
    record = run(FakeEvidence({"state": "succeeded", "task_id": "t1"}, finished))
    assert record['outcome'] == 'collected'
    assert record['series'] == 1 and record['scatter'] == 1 and record['grids'] == 0
    assert record['structured'] is True and record['text_exported'] is True


def test_success_without_structured_data_fails():
    finished = {"structured_data_available": False, "series": [], "grids": [], "scatter": []}
    with pytest.raises(AssertionError) as info:
        run(FakeEvidence({"state": "succeeded", "task_id": "t2"}, finished))
    assert 'returned no structured data' in str(info.value)


def test_probe_reads_the_failure_envelope_without_raising():
    fake = FakeEvidence(unavailable(False))
    run(fake)
    assert fake.calls and fake.calls[0]['okay'] is False
