"""Offline driver checks for the HPC preferences success flow.

These run the SAME shared flow (``tests.support.hpc.check_preferences_success``) used by
``tests/native/test_hpc_live.py`` against the REAL ``tests.support.native.Evidence.call``
normalization (success -> data dict; failure -> {'ok': False, 'error': ...}), using a stub
MCP client. No OpticStudio, no native session. The shared flow lives in tests/support so
this unit test does NOT import the native test module.

Purpose: prove with executable evidence that
  * a real non-null success response exercises all six fields + source and disconnects;
  * an ``is_configured=false`` / ``node_count=0`` response is a VALID success (configured
    query can complete with no nodes);
  * a null/unavailable response takes the skip branch;
  * a success response missing any required field (including ``is_configured``) FAILS
    (does not skip).
"""
import asyncio
from pathlib import Path

import pytest

from tests.support.native import Evidence
from tests.support.hpc import check_preferences_success


class _Resp:
    def __init__(self, structured): self.structured_content = structured


class _Client:
    """Stub MCP client: returns canned structured_content, records call order."""
    def __init__(self, responses): self.responses = responses; self.seen = []
    async def call_tool(self, name, args=None):
        self.seen.append(name)
        return _Resp(self.responses[name])


def _status():
    return {'ok': True, 'data': {'connected': True, 'requires_reconnect': False,
                                 'task_index': {}, 'running_tasks': []}}


def _disconnect_ok():
    return {'ok': True, 'data': {'connected': False, 'last_session': {'session_id': 's'}}}


def _success(**override):
    data = dict(is_configured=True, node_count=2, max_node_count=8, instance_type='Small',
                threads_per_task=4, shutdown_time_ticks=123, source='GetHPCSettingsFromPrefs',
                ownership='IHPCSettings has no Close method; no SystemTool opened by this query',
                readiness='native configured flag only', selection={'mode': 'preferences'})
    data.update(override)
    return {'ok': True, 'data': data}


def _success_missing(key):
    payload = _success()['data']
    payload.pop(key)
    return {'ok': True, 'data': payload}


def _unavailable():
    return {'ok': False, 'error': {'code': 'HPC_SETTINGS_UNAVAILABLE',
                                   'details': {'native_method': 'GetHPCSettingsFromPrefs',
                                               'partial_changes_possible': False}}}


def test_driver_success_runs_all_fields_and_disconnect(tmp_path):
    client = _Client({'get_status': _status(), 'get_hpc_settings': _success(),
                      'disconnect': _disconnect_ok()})
    ev = Evidence(client, Path(tmp_path))
    outcome, actual = asyncio.run(check_preferences_success(ev))
    assert outcome == 'success'
    assert actual['source'] == 'GetHPCSettingsFromPrefs'
    assert actual['shutdown_time_ticks'] == 123 and actual['max_node_count'] == 8
    assert 'disconnect' in client.seen
    # Receipt: the real Evidence.call captured the normalized disconnect response.
    receipts = [c for c in ev.calls if c['tool'] == 'disconnect']
    assert receipts and receipts[-1]['response']['ok'] is True
    assert receipts[-1]['response']['data']['connected'] is False


def test_driver_is_configured_false_zero_nodes_is_valid_success(tmp_path):
    """A configured=false / node_count=0 response is a valid query result (not a failure)."""
    client = _Client({'get_status': _status(),
                      'get_hpc_settings': _success(is_configured=False, node_count=0),
                      'disconnect': _disconnect_ok()})
    ev = Evidence(client, Path(tmp_path))
    outcome, actual = asyncio.run(check_preferences_success(ev))
    assert outcome == 'success'
    assert actual['is_configured'] is False and actual['node_count'] == 0
    assert 'disconnect' in client.seen


def test_driver_null_skips_and_records_disconnect(tmp_path):
    client = _Client({'get_status': _status(), 'get_hpc_settings': _unavailable(),
                      'disconnect': _disconnect_ok()})
    ev = Evidence(client, Path(tmp_path))
    outcome, reason = asyncio.run(check_preferences_success(ev))
    assert outcome == 'skipped' and 'no IHPCSettings' in reason
    assert 'disconnect' in client.seen


@pytest.mark.parametrize('missing', ['is_configured', 'node_count', 'max_node_count',
                                     'threads_per_task', 'shutdown_time_ticks',
                                     'instance_type', 'source', 'ownership'])
def test_driver_missing_field_fails_on_success(tmp_path, missing):
    client = _Client({'get_status': _status(), 'get_hpc_settings': _success_missing(missing),
                      'disconnect': _disconnect_ok()})
    ev = Evidence(client, Path(tmp_path))
    with pytest.raises((KeyError, AssertionError)):
        asyncio.run(check_preferences_success(ev))
    assert 'disconnect' not in client.seen  # failed before any disconnect / skip
