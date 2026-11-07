"""Native optical prescription comparison with paged report lines."""
from pathlib import Path
from typing import Literal
from .schema import Request, PositiveIndex
from .errors import ZemaxError


class FileComparator(Request):
    kind: Literal['file_comparator']
    file1: str
    file2: str
    file1_configuration: PositiveIndex | None = None
    file2_configuration: PositiveIndex | None = None
    include_general_data: bool = True
    include_surface_data: bool = True
    include_surface_detail: bool = True
    include_edge_thickness: bool = True
    include_multi_config_data: bool = True
    include_solves_variables: bool = True
    include_index_tce_data: bool = True
    include_global_vertex: bool = True
    include_coc_point: bool = True
    include_element_volume: bool = True
    include_f_numbers: bool = True
    include_cardinal_points: bool = True
    include_pop_settings: bool = True
    include_files_used: bool = True
    include_merit_function: bool = True
    show_differences_only: bool = True


FLAGS = dict(include_general_data='IncludeGeneralData', include_surface_data='IncludeSurfaceData',
    include_surface_detail='IncludeSurfaceDetail', include_edge_thickness='IncludeEdgeThickness',
    include_multi_config_data='IncludeMultiConfigData', include_solves_variables='IncludeSolvesVariables',
    include_index_tce_data='IncludeIndexTCEData', include_global_vertex='IncludeGlobalVertex',
    include_coc_point='IncludeCOCPoint', include_element_volume='IncludeElementVolume',
    include_f_numbers='IncludeFNumbers', include_cardinal_points='IncludeCardinalPoints',
    include_pop_settings='IncludePOPSettings', include_files_used='IncludeFilesUsed',
    include_merit_function='IncludeMeritFunction', show_differences_only='ShowDifferencesOnly')


def configure(q, paths, write):
    values = {}
    for i, path in enumerate(paths, 1):
        config = getattr(q, f'file{i}_configuration')
        values[f'File{i}Name'] = str(path)
        values[f'File{i}SpecifyConfig'] = config is not None
        if config is not None:
            values[f'File{i}Config'] = config
    values.update({native: getattr(q, key) for key, native in FLAGS.items()})
    for name, value in values.items():
        write(name, value)
    return values


def report_rows(result):
    path = next(a['path'] for a in result['artifacts'] if a['kind'] == 'native_text')
    text = Path(path).read_text(encoding='utf-16')
    if not text.strip():
        raise ZemaxError('NO_RESULT_DATA', '文件比较未返回文本。', artifacts=result['artifacts'], native_messages=result.get('native_messages', []))
    result.update(analysis_kind='file_comparator', rows=[dict(line=i, text=line) for i, line in enumerate(text.splitlines(), 1)],
        structured_data_available=True, row_definition='native report line, one-based; original text retained',
        comparison_source='native optical prescription FileComparatorSettings')
    return result


def validate_configurations(backend, q, paths):
    """The native comparator silently accepts out-of-range configuration numbers."""
    selections = [(i, path, getattr(q, f'file{i}_configuration')) for i, path in enumerate(paths, 1)]
    selections = [item for item in selections if item[2] is not None]
    if not selections:
        return []
    copy = backend.system.CopySystem()
    if copy is None:
        raise ZemaxError('COPY_FAILED', '文件比较无法创建配置检查副本。')
    original = None
    counts = []
    try:
        for index, path, config in selections:
            if not copy.LoadFile(str(path), False):
                raise ZemaxError('LOAD_FAILED', '文件比较输入无法载入检查副本。', file=index, path=str(path))
            count = int(copy.MCE.NumberOfConfigurations)
            counts.append(dict(file=index, configuration_count=count, selected_configuration=config))
            if config > count:
                raise ZemaxError('INDEX_OUT_OF_RANGE', '文件比较配置编号越界。', file=index, requested=config, configuration_count=count)
        return counts
    except Exception as exc:
        original = exc
        raise
    finally:
        try:
            if copy.Close(False) is False:
                raise ZemaxError('RESOURCE_CLOSE_FAILED', '文件比较配置检查副本关闭失败。')
        except Exception as close:
            backend.requires_reconnect = True
            if isinstance(original, ZemaxError):
                original.details['cleanup_error'] = str(close)
            elif original is None:
                raise ZemaxError('RESOURCE_CLOSE_FAILED', '文件比较配置检查副本关闭失败。', native_error=str(close)) from close


def run_comparator(backend, q):
    from .files import input_path
    from .data import unwrap
    from .analyses import scalar_settings
    from .imaging import new_analysis, checked, check
    backend._require_work()
    paths = [input_path(q.file1, {'.zos', '.zmx'}), input_path(q.file2, {'.zos', '.zmx'})]
    configuration_checks = validate_configurations(backend, q, paths)
    tool = new_analysis(backend, 'FileComparatorSettings')
    if tool is None:
        raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE', '原生文件比较工厂未创建分析。')
    try:
        s = unwrap(tool.GetSettings())
        values = configure(q, paths, lambda name, value: checked(backend.native, s, name, value))
        for name, value in values.items():
            check(backend.native, s, name, value)
        actual = scalar_settings(s)
        if actual.get('unavailable_fields'):
            raise ZemaxError('SETTING_UNAVAILABLE', '文件比较设置回读失败。', details=actual['unavailable_fields'])
        settings = dict(kind=q.kind, requested=q.model_dump(), native=actual, configuration_checks=configuration_checks)
    except Exception as exc:
        holder = {'native': tool}
        if not backend._close_task_native(holder):
            failure = exc if isinstance(exc, ZemaxError) else ZemaxError('NATIVE_ERROR', str(exc), type=type(exc).__name__)
            failure.details['cleanup_warnings'] = holder.get('cleanup_warnings', [])
            if failure is not exc:
                raise failure from exc
        raise
    return backend._start_task(q.kind, tool, settings, analysis=True,
        collector=lambda task: report_rows(backend._collect_general_analysis(task)))
