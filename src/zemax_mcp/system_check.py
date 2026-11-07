"""Native system diagnostics with lossless report-line pagination."""
from pathlib import Path
from typing import Literal
from .schema import Request
from .errors import ZemaxError


class SystemCheck(Request):
    kind: Literal['system_check']


class SystemDataReport(Request):
    kind: Literal['system_data']


def report_rows(result, kind='system_check'):
    artifacts = result.get('artifacts', [])
    path = next((a['path'] for a in artifacts if a['kind'] == 'native_text'), None)
    if path is None:
        raise ZemaxError('NO_RESULT_DATA', '原生报告未返回原生文本。',
                         artifacts=artifacts, native_messages=result.get('native_messages', []))
    try:
        lines = Path(path).read_text(encoding='utf-16').splitlines()
    except (OSError, UnicodeError) as exc:
        raise ZemaxError('INVALID_RESULT_DATA', '原生报告文本读取失败。',
                         native_error=str(exc), artifacts=artifacts,
                         native_messages=result.get('native_messages', [])) from exc
    if not any(line.strip() for line in lines):
        raise ZemaxError('NO_RESULT_DATA', '原生报告返回空文本。',
                         artifacts=artifacts, native_messages=result.get('native_messages', []))
    result.update(analysis_kind=kind,
                  rows=[dict(line=i, text=line) for i, line in enumerate(lines, 1)],
                  structured_data_available=True,
                  row_definition='one-based native report lines; original text retained',
                  diagnostic_scope='native report configuration scope',
                  diagnostic_semantics='task success indicates report generation; findings remain in native text')
    if kind == 'system_data':
        result.pop('diagnostic_scope')
        result.pop('diagnostic_semantics')
        result['report_scope'] = 'native system/detail data; original labels and displayed precision'
    return result


def run_system_check(backend, q):
    from .imaging import new_analysis
    from .analyses import scalar_settings
    backend._require_work()
    tool = new_analysis(backend, 'SystemCheck' if q.kind == 'system_check' else 'SystemData')
    if tool is None:
        raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE', '原生原生报告工厂未创建分析。')
    try:
        actual = scalar_settings(tool.GetSettings())
        if actual.get('unavailable_fields'):
            raise ZemaxError('SETTING_UNAVAILABLE', '原生报告基础设置回读失败。',
                             unavailable_fields=actual['unavailable_fields'])
        settings = dict(kind=q.kind, requested=q.model_dump(), native=actual,
                        settings_source='AS_Default/base IAS_; no business settings')
    except Exception as exc:
        holder = dict(native=tool)
        if not backend._close_task_native(holder):
            failure = exc if isinstance(exc, ZemaxError) else ZemaxError('NATIVE_ERROR', str(exc))
            failure.details['cleanup_warnings'] = holder.get('cleanup_warnings', [])
            if failure is not exc:
                raise failure from exc
        raise
    return backend._start_task(q.kind, tool, settings, analysis=True,
        collector=lambda task: report_rows(backend._collect_general_analysis(task), q.kind))
