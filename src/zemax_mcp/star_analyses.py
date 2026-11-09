"""STAR special analyses reached through the generic analysis factory.

The six ``AnalysisIDM`` members are a static fact from
``verification/development/BASE-01/probe/api-interfaces.json``:

    STARAlignCheck=155, STARSysViewer=156, STAR2DDefPlot=157,
    STARPerfChange=158, STARIndexVsTemp=159, STARInspectFEA=160

That dump contains **no** ``IAS_`` settings interface for them. That absence does not
prove the settings outlet is missing: the generic ``CreateNewAnalysis`` path still
returns a settings object, so the surface of that object is probed at run time and
recorded verbatim instead of being assumed either way.

Collection is STAR specific on purpose. ``_collect_general_analysis`` raises
``EXPORT_FAILED`` as soon as ``GetTextFile`` returns false, which would discard native
series, grids and scatter points that are already available. Here the text export outcome
is recorded as a separate fact and every native data collection is captured independently.
Only series, grids and scatter points count as structured data: a BOM-only file, a title
line or an error report is never reported as a valid result.

Module availability is read live from ``IZOSAPI_Application.IsSTARModuleEnabled``. The
2026-11-06 readiness record is historical and is never reported as the current state.
"""
import math
from typing import Literal

from .data import dotnet_array, unwrap
from .errors import ZemaxError
from .schema import Request

STAR_ANALYSES = {
    'star_align_check': 'STARAlignCheck',
    'star_sys_viewer': 'STARSysViewer',
    'star_2d_def_plot': 'STAR2DDefPlot',
    'star_perf_change': 'STARPerfChange',
    'star_index_vs_temp': 'STARIndexVsTemp',
    'star_inspect_fea': 'STARInspectFEA',
}

STAR_ANALYSIS_IDS = {'STARAlignCheck': 155, 'STARSysViewer': 156, 'STAR2DDefPlot': 157,
                     'STARPerfChange': 158, 'STARIndexVsTemp': 159, 'STARInspectFEA': 160}

# Row page size for reading an IMatrixData grid through its official ReadData buffer.
# Paging is only a transport detail: every row is read, and a grid that cannot be read in
# full is rejected instead of being silently truncated.
MATRIX_PAGE_ROWS = 256

# ``ZOSAPI.Analysis.ErrorType`` has exactly one non-failure value, ``Success``. Every other
# member is a concrete failure code, taken from the reflection dump:
#   1 InvalidParameter, 2 InvalidSettings, 3 Failed, 4 AnalysisUnavailableForProgramMode,
#   5 NotYetImplemented, 10000 NoSolverLicenseAvailable, 10001 ToolAlreadyOpen,
#   10002 SequentialOnly, 10003 NonSequentialOnly, 10004 SingleNSCRayTraceSupported,
#   10005 HPCNotAvailable, 10006 FeatureNotSupported, 10007 NotAvailableInLegacy
FATAL_MESSAGE_TYPES = frozenset({
    'InvalidParameter', 'InvalidSettings', 'Failed', 'AnalysisUnavailableForProgramMode',
    'NotYetImplemented', 'NoSolverLicenseAvailable', 'ToolAlreadyOpen', 'SequentialOnly',
    'NonSequentialOnly', 'SingleNSCRayTraceSupported', 'HPCNotAvailable',
    'FeatureNotSupported', 'NotAvailableInLegacy'})


class StarAlignCheck(Request):
    """STAR alignment check analysis (AnalysisIDM.STARAlignCheck = 155)."""
    kind: Literal['star_align_check']


class StarSysViewer(Request):
    """STAR system viewer analysis (AnalysisIDM.STARSysViewer = 156)."""
    kind: Literal['star_sys_viewer']


class Star2DDefPlot(Request):
    """STAR two-dimensional deformation plot (AnalysisIDM.STAR2DDefPlot = 157)."""
    kind: Literal['star_2d_def_plot']


class StarPerfChange(Request):
    """STAR performance change analysis (AnalysisIDM.STARPerfChange = 158)."""
    kind: Literal['star_perf_change']


class StarIndexVsTemp(Request):
    """STAR index versus temperature analysis (AnalysisIDM.STARIndexVsTemp = 159)."""
    kind: Literal['star_index_vs_temp']


class StarInspectFEA(Request):
    """STAR FEA inspection analysis (AnalysisIDM.STARInspectFEA = 160)."""
    kind: Literal['star_inspect_fea']


STAR_REQUESTS = {kind: model for kind, model in (
    ('star_align_check', StarAlignCheck), ('star_sys_viewer', StarSysViewer),
    ('star_2d_def_plot', Star2DDefPlot), ('star_perf_change', StarPerfChange),
    ('star_index_vs_temp', StarIndexVsTemp), ('star_inspect_fea', StarInspectFEA))}


def star_module_enabled(backend):
    """Read module availability live; return ``(value_or_None, source)``."""
    application = getattr(getattr(backend, 'native', None), 'application', None)
    if application is None:
        return None, 'unavailable: no native application object'
    try:
        value = getattr(application, 'IsSTARModuleEnabled')
    except Exception as exc:  # pragma: no cover - defensive
        return None, f'unreadable: {exc}'
    try:
        return bool(value), 'live read of IZOSAPI_Application.IsSTARModuleEnabled'
    except Exception as exc:  # pragma: no cover - defensive
        return None, f'unreadable: {exc}'


def settings_surface(settings_object):
    """Record the public members the returned settings object actually exposes."""
    names = []
    for name in dir(settings_object):
        if name.startswith('_'):
            continue
        try:
            value = getattr(settings_object, name)
        except Exception:
            continue
        if callable(value):
            continue
        names.append(name)
    return sorted(names)


def native_messages(results):
    """Native messages with the official ``ZOSAPI.Analysis.ErrorType`` severity."""
    messages = []
    for index in range(results.NumberOfMessages):
        message = results.GetMessageAt(index)
        code = str(message.ErrorCode)
        messages.append(dict(code=code, text=str(message.Text),
                             severity='fatal' if code in FATAL_MESSAGE_TYPES else 'information'))
    return messages


def fatal_messages(messages):
    """Only codes that are officially failures; a non-Success code alone is not fatal."""
    return [m for m in messages if m['severity'] == 'fatal']


def native_header(results):
    header = results.HeaderData
    if header is None or header.Lines is None:
        return []
    return [str(line) for line in header.Lines]


def text_export(results, backend, task):
    """Attempt the text export and record the outcome; never fatal by itself."""
    path = backend.directory / f"{task['task_id']}_star.txt"
    record = dict(attempted=True, exported=False, path=None, error=None,
                  line_count=None, non_blank_lines=None, encoding='utf-16')
    try:
        exported = bool(results.GetTextFile(str(path)))
    except Exception as exc:  # export is optional evidence, not the result
        record['error'] = str(exc)
        return record
    if not exported:
        record['error'] = 'GetTextFile returned false'
        return record
    record['exported'] = True
    record['path'] = str(path)
    try:
        lines = path.read_text(encoding='utf-16').splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        record['error'] = f'exported but unreadable: {exc}'
        return record
    record['line_count'] = len(lines)
    record['non_blank_lines'] = sum(1 for line in lines if line.strip())
    return record


def grid_values(grid, index):
    """Complete ``Ny x Nx`` values from the official members; never truncated.

    ``IAR_DataGrid.Values`` is ``System.Double[,]`` and is used when present. Otherwise the
    official ``ValueData`` matrix (``ZOSAPI.Common.IMatrixData``, members ``Rows``/``Cols``/
    ``Data``/``GetValueAt``/``ReadData``) is read row by row. A grid that cannot be read in
    full is rejected instead of being returned partially.
    """
    nx, ny = int(grid.Nx), int(grid.Ny)
    if nx <= 0 or ny <= 0:
        raise ZemaxError('INVALID_RESULT_DATA', '数据网格的 Nx/Ny 不是正值。',
                         grid=index, nx=nx, ny=ny)
    values = getattr(grid, 'Values', None)
    if values is not None:
        rows = dotnet_array(values)
        source = 'IAR_DataGrid.Values (System.Double[,])'
    else:
        matrix = getattr(grid, 'ValueData', None)
        if matrix is None:
            raise ZemaxError('INVALID_RESULT_DATA', '数据网格既无 Values 也无 ValueData。',
                             grid=index, nx=nx, ny=ny)
        matrix_rows, matrix_cols = int(matrix.Rows), int(matrix.Cols)
        if matrix_rows != ny or matrix_cols != nx:
            raise ZemaxError('INVALID_RESULT_DATA', 'ValueData 尺寸与 Nx/Ny 不一致。',
                             grid=index, nx=nx, ny=ny,
                             matrix_rows=matrix_rows, matrix_cols=matrix_cols)
        rows = [[float(matrix.GetValueAt(row, column)) for column in range(nx)]
                for row in range(ny)]
        source = 'IAR_DataGrid.ValueData (IMatrixData.Rows/Cols/GetValueAt)'
    if len(rows) != ny or any(len(row) != nx for row in rows):
        raise ZemaxError('INVALID_RESULT_DATA', '数据网格数值尺寸与 Nx/Ny 不一致。',
                         grid=index, nx=nx, ny=ny, rows_returned=len(rows),
                         row_widths=sorted({len(row) for row in rows}))
    return rows, source


def native_series(results):
    """Curves; dimensions and finiteness follow the existing analysis convention."""
    series = []
    for index in range(results.NumberOfDataSeries):
        item = results.GetDataSeries(index)
        if item is None or item.XData is None or item.YData is None:
            raise ZemaxError('NO_RESULT_DATA', '原生分析返回了没有坐标或数值的曲线。',
                             series=index, native_messages=native_messages(results))
        x = dotnet_array(item.XData.Data)
        y = dotnet_array(item.YData.Data)
        if len(x) != len(y) or any(not math.isfinite(v) for v in x):
            raise ZemaxError('INVALID_RESULT_DATA', '曲线尺寸不一致或横轴包含非有限值。',
                             series=index, x_count=len(x), y_count=len(y))
        width = len(y[0]) if y else 0
        if any(len(row) != width for row in y):
            raise ZemaxError('INVALID_RESULT_DATA', '曲线数值列数不一致。',
                             series=index, value_columns=width)
        labels = ([str(label) for label in item.SeriesLabels]
                  if item.SeriesLabels is not None
                  else ['column_' + str(j + 1) for j in range(width)])
        if len(labels) != width:
            raise ZemaxError('INVALID_RESULT_DATA', '曲线数值列数与原生标签不一致。',
                             series=index, labels=labels, value_columns=width)
        series.append(dict(
            series=index, description=str(item.Description), x_label=str(item.XLabel),
            labels=labels, x=x, point_count=len(x), value_columns=width,
            y=[[v if math.isfinite(v) else None for v in row] for row in y],
            invalid_count=sum(not math.isfinite(v) for row in y for v in row),
            labels_source='native' if item.SeriesLabels is not None
            else 'generated column indices; native SeriesLabels is null'))
    return series


def native_grids(results):
    """Grids with their complete native values and the member used to read them."""
    grids = []
    for index in range(results.NumberOfDataGrids):
        grid = results.GetDataGrid(index)
        if grid is None:
            raise ZemaxError('NO_RESULT_DATA', '原生分析返回了空的数据网格。',
                             grid=index, native_messages=native_messages(results))
        rows, source = grid_values(grid, index)
        grids.append(dict(
            grid=index, description=str(grid.Description), x_label=str(grid.XLabel),
            y_label=str(grid.YLabel), value_label=str(grid.ValueLabel),
            nx=int(grid.Nx), ny=int(grid.Ny), dx=float(grid.Dx), dy=float(grid.Dy),
            min_x=float(grid.MinX), min_y=float(grid.MinY),
            values=[[v if math.isfinite(v) else None for v in row] for row in rows],
            rows_returned=len(rows),
            invalid_count=sum(not math.isfinite(v) for row in rows for v in row),
            values_source=source,
            array_order='native row, column (dimension 0, dimension 1)'))
    return grids


def _finite(value):
    """A finite float or ``None``; the same convention used by the image collector."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def native_scatter(results):
    """Scatter points as flat ``rows`` plus a plot-ready ``scatter`` list.

    This mirrors ``imaging.collect_scatter``: ``rows`` keeps every point with its validity
    (invalid coordinates stay as ``None``), while ``scatter[*].points`` carries only the
    finite points an image can draw. The raw detail lives in ``rows``; the same big array is
    not duplicated into a second key.
    """
    rows = []
    scatter = []
    for index in range(results.NumberOfDataScatterPoints):
        block = results.GetDataScatterPoint(index)
        if block is None:
            raise ZemaxError('NO_RESULT_DATA', '原生分析返回了空的散点集合。',
                             block=index, native_messages=native_messages(results))
        count = int(block.NumPoints)
        collection = getattr(block, 'Points', None)
        if collection is not None:
            items = list(collection)
            source = 'IAR_DataScatterPoints.Points (IAR_ScatterPoint[])'
        else:
            items = [block.GetPoint(i) for i in range(count)]
            source = 'IAR_DataScatterPoints.GetPoint(Int32)'
        if len(items) != count:
            raise ZemaxError('INVALID_RESULT_DATA', '散点数量与 NumPoints 不一致。',
                             block=index, num_points=count, points_returned=len(items))
        block_rows = []
        for point_index, item in enumerate(items):
            point = dict(block=index, point=point_index, x=_finite(item.X),
                         y=_finite(item.Y), value=_finite(item.Value))
            point['valid'] = all(point[key] is not None for key in ('x', 'y', 'value'))
            block_rows.append(point)
        valid = [{key: point[key] for key in ('x', 'y', 'value')}
                 for point in block_rows if point['valid']]
        rows.extend(block_rows)
        scatter.append(dict(
            scatter=len(scatter), native_scatter=index, description=str(block.Description),
            x_label=str(block.XLabel), y_label=str(block.YLabel),
            value_label=str(block.ValueLabel), count=count, points=valid,
            invalid_count=count - len(valid), points_source=source))
    return rows, scatter


def collect_star_results(backend, task, kind):
    """Collect text export, messages and every native data collection independently."""
    results = unwrap(task['native'].GetResults())
    if results is None:
        raise ZemaxError('ANALYSIS_FAILED', '没有有效原生分析结果。', analysis=kind)
    messages = native_messages(results)
    header = native_header(results)
    if not results.IsValid:
        raise ZemaxError('ANALYSIS_FAILED', '没有有效原生分析结果。',
                         analysis=kind, native_messages=messages, native_header=header)
    text = text_export(results, backend, task)
    series = native_series(results)
    grids = native_grids(results)
    scatter_rows, scatter = native_scatter(results)
    # An empty collection is not a valid structured result: a series with no points or no
    # value columns, and a scatter block with NumPoints == 0, are recorded but not counted.
    empty = ([dict(kind='series', index=s['series'], reason='no points or no value columns')
              for s in series if s['point_count'] == 0 or s['value_columns'] == 0]
             + [dict(kind='scatter', index=b['native_scatter'], reason='NumPoints == 0')
                for b in scatter if b['count'] == 0])
    series = [s for s in series if s['point_count'] and s['value_columns']]
    scatter = [b for b in scatter if b['count']]
    partial = dict(series=series, grids=grids, scatter=scatter, rows=scatter_rows,
                   text_export=text, empty_collections=empty)
    fatal = fatal_messages(messages)
    if fatal:
        # A fatal native message is never reported as success, even if some data came back.
        raise ZemaxError('ANALYSIS_FAILED', 'STAR 专题分析报告了原生失败消息。',
                         analysis=kind, native_messages=messages, native_header=header,
                         fatal_messages=fatal, text_export=text, partial_result=partial,
                         note=('every ZOSAPI.Analysis.ErrorType value except Success is a '
                               'concrete failure code; any returned data is kept as '
                               'partial_result rather than treated as a result'))
    payload = dict(analysis_kind=kind, native_analysis=STAR_ANALYSES[kind],
                   analysis_id=STAR_ANALYSIS_IDS[STAR_ANALYSES[kind]],
                   native_header=header, native_messages=messages, text_export=text,
                   series=series, grids=grids, scatter=scatter,
                   empty_collections=empty)
    if scatter_rows:
        # Only add the row chain when scatter detail exists, so a series/grid-only result
        # keeps its own existing paging path instead of being routed to an empty row page.
        payload['rows'] = scatter_rows
    payload['structured_data_available'] = bool(series or grids or scatter)
    if payload['structured_data_available']:
        payload['artifacts'] = ([{'kind': 'native_text', 'path': text['path']}]
                                if text['exported'] and text['path'] else [])
        payload['result_source'] = 'native data collections; the text export is optional evidence'
        return payload
    raise ZemaxError('NO_RESULT_DATA', 'STAR 专题分析没有提供有效的曲线、网格或散点。',
                     analysis=kind, native_messages=messages, native_header=header,
                     text_export=text, empty_collections=empty,
                     note=('an exported but empty or title-only text file, an empty series or '
                           'an empty scatter block is not a valid result; only non-empty '
                           'series, grids and scatter points are'))


def run_star_analysis(backend, q):
    """Create the STAR analysis through the generic factory and run it."""
    from .analyses import scalar_settings
    from .imaging import new_analysis

    backend._require_work()
    kind = q.kind
    name = STAR_ANALYSES[kind]
    enabled, source = star_module_enabled(backend)
    availability = dict(enabled=enabled, source=source)
    if enabled is False:
        raise ZemaxError('FEATURE_UNAVAILABLE', '本机 STAR 模块未启用，专题分析不可执行。',
                         analysis=kind, native_analysis=name, availability=availability,
                         note=('the AnalysisIDM member exists, so this is a module-licence '
                               'precondition rather than a missing analysis factory'))
    tool = new_analysis(backend, name)
    if tool is None:
        raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE', '原生 STAR 专题分析工厂未创建分析。',
                         analysis=kind, native_analysis=name, availability=availability)
    try:
        settings_object = tool.GetSettings()  # read once; the probe and the readback share it
        native_settings = scalar_settings(settings_object)
        if native_settings.get('unavailable_fields'):
            raise ZemaxError('SETTING_UNAVAILABLE', '原生 STAR 专题分析设置回读失败。',
                             analysis=kind, native_analysis=name,
                             unavailable_fields=native_settings['unavailable_fields'])
        settings = dict(kind=kind, analysis=kind, native_analysis=name,
                        analysis_id=STAR_ANALYSIS_IDS.get(name), requested=q.model_dump(),
                        native=native_settings,
                        settings_surface=settings_surface(settings_object),
                        settings_support=('probed at run time; no IAS_ interface is documented '
                                          'for this analysis'),
                        availability=availability)
    except Exception as exc:
        holder = dict(native=tool)
        if not backend._close_task_native(holder):
            failure = exc if isinstance(exc, ZemaxError) else ZemaxError('NATIVE_ERROR', str(exc))
            failure.details['cleanup_warnings'] = holder.get('cleanup_warnings', [])
            if failure is not exc:
                raise failure from exc
        raise
    return backend._start_task(kind, tool, settings, analysis=True,
                               collector=lambda task: collect_star_results(backend, task, kind))
