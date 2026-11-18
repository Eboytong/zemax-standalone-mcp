"""Shared coverage and restoration semantics for persisted and live tasks."""

BATCH_KEYS = {
    'batch_evaluation': 'paths', 'parameter_scan': 'values',
    'configuration_evaluation': 'configurations', 'candidate_evaluation': 'candidate_ids',
    'catalog_evaluation': 'candidates', 'multistart_optimization': 'starts',
    'pareto_optimization': 'starts',
}
TERMINAL = {'succeeded', 'failed', 'cancelled'}


def task_outcome(task, result=None):
    result = result or {}
    state = task.get('state', 'unknown')
    settings = task.get('settings') or {}
    kind = task.get('kind')
    items = settings.get(BATCH_KEYS.get(kind))
    restoration = task.get('restoration') or result.get('restoration') or {}
    restored = restoration.get('restored')
    if restored is False:
        recovery = 'failed'
    elif restored is True:
        recovery = 'pending' if state not in TERMINAL else 'restored'
    elif kind in BATCH_KEYS:
        recovery = 'unknown' if state in TERMINAL else 'pending'
    else:
        recovery = 'not_applicable'
    coverage = dict(state='not_applicable', planned=None, succeeded=None, failed=None,
                    skipped=None, pending=None)
    if isinstance(items, list):
        planned = len(items)
        if kind == 'pareto_optimization':
            planned *= len((settings.get('pareto') or {}).get('weight_grid', []))
        rows = task.get('rows', result.get('rows'))
        if rows is None:
            coverage.update(state='unknown', planned=planned)
        else:
            states = [r.get('state') or 'succeeded' for r in rows]
            succeeded, failed = states.count('succeeded'), states.count('failed')
            remaining = max(0, planned - succeeded - failed)
            coverage.update(state=('pending' if state not in TERMINAL else
                                   'complete' if planned == succeeded else 'incomplete'),
                            planned=planned, succeeded=succeeded, failed=failed,
                            skipped=remaining if state in TERMINAL else states.count('skipped'),
                            pending=0 if state in TERMINAL else max(0, remaining - states.count('skipped')))
    elif task.get('native_trace_complete') is not None:
        coverage['state'] = 'complete' if task['native_trace_complete'] else 'incomplete'
    if state in TERMINAL and coverage['skipped']:
        coverage['skip_reason'] = (result.get('error') or task.get('error') or {}).get('code') or (
            'CANCELLED' if state == 'cancelled' else 'NOT_REACHED')
    return dict(execution_state=state, coverage=coverage,
                resource_release=('failed' if task.get('cleanup_warnings') else
                                  'confirmed' if task.get('close_attempted') else 'not_recorded'),
                restoration=dict(state=recovery, checkpoint=restoration.get('checkpoint'),
                                 error=restoration.get('error')))


def populate_outcome(result):
    task = result.get('task') or {}
    value = task.get('outcome') or result.get('outcome') or task_outcome(task, result)
    result['outcome'] = value
    if 'task' in result:
        result['task']['outcome'] = value
    return result
