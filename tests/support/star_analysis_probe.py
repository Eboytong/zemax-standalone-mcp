"""Offline-testable probe logic for the D012 STAR special-analysis native job.

Deliberately free of the MCP client so a unit test can drive it with a fake Evidence
object. The native job and the unit test share exactly this code, so the failure
classification is proven offline rather than only on a machine with a live license.
"""
import json

KINDS = ['star_inspect_fea', 'star_align_check', 'star_2d_def_plot',
         'star_index_vs_temp', 'star_perf_change', 'star_sys_viewer']

MODULE_UNAVAILABLE = 'FEATURE_UNAVAILABLE'


def _dumped(value):
    """Full, stable rendering of a response so a failure keeps the whole envelope."""
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def module_unavailable(error):
    """True only for the explicit module-disabled gate, never for an arbitrary error."""
    if not isinstance(error, dict):
        return False
    if error.get('code') != MODULE_UNAVAILABLE:
        return False
    details = error.get('details') or {}
    availability = details.get('availability') or {}
    return availability.get('enabled') is False


async def probe_kind(evidence, kind):
    """Run one STAR analysis kind and classify the outcome.

    The failure envelope is read with ``okay=False`` so a genuine runtime/result/code
    error is preserved and re-raised as a test failure instead of being silently recorded
    as a "rejected" attempt. Only the explicit ``FEATURE_UNAVAILABLE`` with
    ``details.availability.enabled is False`` is treated as the expected module-disabled
    precondition. A successful run must report ``structured_data_available``.
    """
    response = await evidence.call('run_analysis', dict(request=dict(kind=kind)), okay=False)
    if isinstance(response, dict) and response.get('ok') is False:
        error = response.get('error')
        if module_unavailable(error):
            details = error.get('details') or {}
            return dict(kind=kind, outcome='module_unavailable',
                        error_code=error.get('code'),
                        availability=details.get('availability'))
        raise AssertionError(
            'unexpected run_analysis failure for %s: %s' % (kind, _dumped(response)))
    payload = await evidence.finish(response)
    if payload.get('structured_data_available') is not True:
        raise AssertionError(
            'run_analysis for %s returned no structured data: %s' % (kind, _dumped(payload)))
    text_export = payload.get('text_export') or {}
    return dict(kind=kind, outcome='collected',
                native_analysis=payload.get('native_analysis'),
                analysis_id=payload.get('analysis_id'),
                text_exported=bool(text_export.get('exported')),
                series=len(payload.get('series') or []),
                grids=len(payload.get('grids') or []),
                scatter=len(payload.get('scatter') or []),
                structured=payload['structured_data_available'])
