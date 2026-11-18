"""Read-only capability preflight shared by discovery and detail."""
from pathlib import Path

INDEX_VERSION = 2
OFFLINE = {'get_status', 'search_capabilities', 'get_capabilities', 'list_task_history',
           'get_request_status', 'get_historical_result', 'get_task_status', 'get_task_result'}
STATUS_ACCESS = OFFLINE | {'cancel_task'}
SEQUENTIAL = {'get_surfaces', 'update_surfaces', 'run_fft_mtf', 'run_spot_analysis',
              'run_batch_ray_trace', 'run_parameter_scan', 'run_batch_evaluation',
              'run_candidate_evaluation', 'run_configuration_evaluation', 'run_multistart_optimization',
              'run_local_optimization', 'run_tolerance_analysis', 'get_star_data', 'run_star_operation'}
NSC = {'get_nsc_objects', 'update_nsc_objects', 'insert_nsc_objects', 'run_nsc_ray_trace',
       'get_detector_data', 'save_detector_data'}
MODEL = {'save_lens_as', 'create_archive', 'run_layout_export'}
LIFECYCLE = {'connect', 'disconnect', 'new_system', 'open_lens', 'load_archive'}
INPUTS = {'open_lens': ('path', 'file'), 'load_archive': ('path', 'file'),
          'export_analysis_image': ('task_id', 'finished_task'),
          'get_task_result': ('task_id', 'finished_task'), 'get_task_status': ('task_id', 'task'),
          'cancel_task': ('task_id', 'task')}
OUTPUTS = {'open_lens': ['working_model'], 'new_system': ['working_model'], 'load_archive': ['task', 'working_model'],
           'save_lens_as': ['lens'], 'create_archive': ['task', 'archive'],
           'update_surfaces': ['model_revision'], 'update_nsc_objects': ['model_revision'],
           'get_surfaces': ['rows'], 'get_task_result': ['result'], 'get_task_status': ['task_status'],
           'run_layout_export': ['task', 'native_image'], 'run_fft_mtf': ['task', 'series', 'series_csv'],
           'run_spot_analysis': ['task', 'metrics', 'native_text'], 'run_nsc_ray_trace': ['task', 'trace_result'],
           'get_detector_data': ['detector_data'], 'export_analysis_image': ['image']}


def contract(tool, kind=None):
    requirements = []
    if tool not in OFFLINE and tool != 'disconnect':
        requirements.append(dict(kind='session_recovery'))
    if tool not in STATUS_ACCESS:
        requirements.append(dict(kind='idle'))
    if tool in (LIFECYCLE - {'connect', 'disconnect'}) | SEQUENTIAL | NSC | MODEL:
        requirements.append(dict(kind='connection'))
    if tool in MODEL | {'run_parameter_scan', 'run_candidate_evaluation', 'run_local_optimization'}:
        requirements.append(dict(kind='working_model'))
    if tool in SEQUENTIAL | NSC:
        requirements.append(dict(kind='model_mode', value='Sequential' if tool in SEQUENTIAL else 'NonSequential'))
    if tool in {'get_star_data', 'run_star_operation'} or (kind or '').startswith('star_'):
        requirements.append(dict(kind='license_feature', value='star'))
    if tool in INPUTS:
        field, resource = INPUTS[tool]
        requirements.append(dict(kind=resource, field=field))
    profiled = tool in OFFLINE | LIFECYCLE | SEQUENTIAL | NSC | MODEL | set(INPUTS)
    outputs = OUTPUTS.get(tool, ['task'] if kind or tool.startswith('run_') else [])
    return dict(requirements=requirements, produces=outputs, preflight_profiled=profiled)


def _next(tool, arguments=None):
    return dict(tool='execute_capability', arguments=dict(capability_id='tool:'+tool, arguments=arguments or {}))


def readiness(spec, runtime, arguments=None):
    arguments = arguments or {}
    fields = arguments.get('request', arguments)
    if not isinstance(fields, dict):
        fields = {}
    unavailable, unknown = [], []

    def note(target, check, code, followup=None, **details):
        item = dict(requirement=check, code=code, **details)
        if followup:
            item['next_request'] = followup
        target.append(item)

    for check in spec['requirements']:
        kind = check['kind']
        if kind == 'session_recovery' and runtime['requires_reconnect']:
            note(unavailable, check, 'RECONNECT_REQUIRED', _next('get_status'))
        elif kind == 'idle' and runtime.get('active_task_id'):
            note(unavailable, check, 'SYSTEM_BUSY', _next('get_task_status', {'task_id': runtime['active_task_id']}))
        elif kind == 'connection' and not runtime['connected']:
            note(unavailable, check, 'NOT_CONNECTED', _next('connect'))
        elif kind == 'working_model' and runtime['connected'] and not runtime.get('working_model'):
            note(unavailable, check, 'NO_WORKING_MODEL', _next('new_system', {'mode': runtime.get('mode') or 'Sequential'}))
        elif kind == 'model_mode' and runtime['connected']:
            mode = runtime.get('mode')
            if not mode:
                note(unknown, check, 'MODEL_MODE_UNOBSERVED', _next('get_status'))
            elif mode != check['value']:
                note(unavailable, check, 'MODE_MISMATCH', actual=mode)
        elif kind == 'license_feature':
            enabled = runtime.get('features', {}).get(check['value'])
            if enabled is None:
                note(unknown, check, 'LICENSE_UNOBSERVED', _next('get_status'))
            elif not enabled:
                note(unavailable, check, 'FEATURE_UNAVAILABLE', _next('get_status'))
        elif kind in {'file', 'task', 'finished_task'}:
            value = fields.get(check['field'])
            if value is None:
                note(unknown, check, 'ARGUMENT_REQUIRED')
            elif kind == 'file':
                try:
                    exists = isinstance(value, str) and Path(value).is_absolute() and Path(value).is_file()
                except (OSError, ValueError):
                    exists = False
                if not exists:
                    note(unavailable, check, 'INVALID_INPUT_FILE')
            else:
                state = runtime.get('tasks', {}).get(value) if isinstance(value, str) else None
                followup = _next('get_task_status', {'task_id': value})
                if not state:
                    note(unavailable, check, 'TASK_NOT_FOUND', _next('list_task_history', {'request': {}}))
                elif kind == 'finished_task' and state not in {'succeeded', 'failed', 'cancelled'}:
                    note(unavailable, check, 'TASK_NOT_FINISHED', followup)
    if not spec['preflight_profiled']:
        note(unknown, {}, 'PREFLIGHT_NOT_PROFILED')
    return dict(state='blocked' if unavailable else 'unknown' if unknown else 'ready',
                blockers=unavailable, unchecked=unknown)
