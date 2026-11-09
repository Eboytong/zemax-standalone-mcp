"""STAR special analyses: registration, availability, collection and failure layers.

The AnalysisIDM members are a static fact; a missing ``IAS_`` interface is not treated as
proof that no settings outlet exists. Availability is always read live, never from the
historical 2026-11-06 readiness record.

Collection is exercised independently of the generic analysis collector. Every native
member used here is taken from the reflection dump
(``verification/development/BASE-01/probe/api-interfaces.json``):

* ``IAR_DataGrid.Values`` is ``System.Double[,]``; ``ValueData`` is
  ``ZOSAPI.Common.IMatrixData`` with ``Rows``/``Cols``/``Data``/``GetValueAt``/``ReadData``.
* ``IAR_DataScatterPoints`` has ``NumPoints``, ``Points : IAR_ScatterPoint[]`` and
  ``GetPoint(Int32)``; ``IAR_ScatterPoint`` has ``X``/``Y``/``Value``.
* ``IMessage.ErrorCode`` is ``ZOSAPI.Analysis.ErrorType``.
"""
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from pydantic import TypeAdapter, ValidationError

from zemax_mcp.analyses import ANALYSES
from zemax_mcp.analysis_models import AnalysisRequest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.star_analyses import (
    FATAL_MESSAGE_TYPES,
    STAR_ANALYSES,
    STAR_ANALYSIS_IDS,
    STAR_REQUESTS,
    collect_star_results,
    fatal_messages,
    grid_values,
    run_star_analysis,
    settings_surface,
    star_module_enabled,
)

DUMP = Path(__file__).resolve().parents[2] / 'verification/development/BASE-01/probe/api-interfaces.json'


def dump_document():
    if not DUMP.is_file():
        pytest.skip('native reflection dump not present in this checkout')
    return json.loads(DUMP.read_text(encoding='utf-8'))


class Arr:
    """Minimal .NET-like array surface used by ``data.dotnet_array``."""

    def __init__(self, rows, rank):
        self._rows = rows
        self.Rank = rank

    def __iter__(self):
        if self.Rank == 1:
            return iter([float(v) for v in self._rows])
        return iter(self._rows)

    def __getitem__(self, key):
        row, column = key
        return self._rows[row][column]

    def GetLength(self, dimension):
        return len(self._rows[0]) if dimension == 1 else len(self._rows)


# --- registration and contract ---------------------------------------------

def test_analysis_ids_match_the_static_enum():
    members = dump_document()['enums']['ZOSAPI.Analysis.AnalysisIDM']
    for name, value in STAR_ANALYSIS_IDS.items():
        assert members.get(name) == value, name


def test_collection_members_match_the_dump():
    """The members used by the collector must exist in the official reflection."""
    interfaces = dump_document()['interfaces']
    grid_props = {p['name']: p['type'] for p in interfaces['ZOSAPI.Analysis.Data.IAR_DataGrid']['properties']}
    assert grid_props['Values'] == 'System.Double[,]'
    assert grid_props['ValueData'] == 'ZOSAPI.Common.IMatrixData'
    assert {'Nx', 'Ny', 'Dx', 'Dy', 'MinX', 'MinY'} <= set(grid_props)
    matrix_props = {p['name'] for p in interfaces['ZOSAPI.Common.IMatrixData']['properties']}
    assert {'Rows', 'Cols', 'Data'} <= matrix_props
    matrix_methods = ' '.join(interfaces['ZOSAPI.Common.IMatrixData']['methods'])
    assert 'GetValueAt' in matrix_methods and 'ReadData' in matrix_methods
    scatter_props = {p['name']: p['type'] for p in interfaces['ZOSAPI.Analysis.Data.IAR_DataScatterPoints']['properties']}
    assert scatter_props['NumPoints'] == 'System.UInt32'
    assert scatter_props['Points'] == 'ZOSAPI.Analysis.Data.IAR_ScatterPoint[]'
    point_props = {p['name'] for p in interfaces['ZOSAPI.Analysis.Data.IAR_ScatterPoint']['properties']}
    assert point_props == {'X', 'Y', 'Value'}
    assert 'GetPoint(Int32)' in ' '.join(interfaces['ZOSAPI.Analysis.Data.IAR_DataScatterPoints']['methods'])


def test_message_severity_uses_the_official_enum():
    error_type = dump_document()['enums']['ZOSAPI.Analysis.ErrorType']
    assert set(FATAL_MESSAGE_TYPES) <= set(error_type)
    assert 'Success' not in FATAL_MESSAGE_TYPES
    assert 'ZOSAPI.Analysis.ErrorType' in dump_document()['interfaces']['ZOSAPI.Analysis.IMessage']['properties'][0]['type']


def test_every_kind_is_registered_for_capability_discovery():
    """Capability listing must not miss the STAR kinds."""
    assert set(STAR_ANALYSES) <= set(ANALYSES)
    for kind, name in STAR_ANALYSES.items():
        assert ANALYSES[kind] == name
        assert STAR_REQUESTS[kind](kind=kind).kind == kind


def test_each_kind_is_its_own_request_model():
    adapter = TypeAdapter(AnalysisRequest)
    for kind in STAR_ANALYSES:
        assert adapter.validate_python({'kind': kind}).kind == kind


@pytest.mark.parametrize('kind', sorted(STAR_ANALYSES))
def test_request_is_identity_only(kind):
    adapter = TypeAdapter(AnalysisRequest)
    for payload in ({'kind': kind, 'surface': 1}, {'kind': kind, 'analysis': kind},
                    {'kind': kind, 'settings': {}}, {'kind': kind, 'section': 'x'}):
        with pytest.raises(ValidationError):
            adapter.validate_python(payload)


def test_unknown_kind_is_not_a_star_kind():
    with pytest.raises(ValidationError):
        TypeAdapter(AnalysisRequest).validate_python({'kind': 'star_analysis', 'analysis': 'star_inspect_fea'})


# --- availability -----------------------------------------------------------

def test_availability_is_read_live():
    backend = NS(native=NS(application=NS(IsSTARModuleEnabled=True)))
    assert star_module_enabled(backend) == (True, 'live read of IZOSAPI_Application.IsSTARModuleEnabled')
    backend = NS(native=NS(application=NS(IsSTARModuleEnabled=False)))
    assert star_module_enabled(backend)[0] is False


def test_availability_is_unknown_without_an_application():
    value, source = star_module_enabled(NS(native=NS()))
    assert value is None and source.startswith('unavailable')


def test_settings_surface_records_public_members_only():
    settings = NS(IsValid=True, Parent=None, SomeProperty=3, Method=lambda: None)
    surface = settings_surface(settings)
    assert 'IsValid' in surface and 'SomeProperty' in surface
    assert all(not name.startswith('_') for name in surface)


# --- run path ---------------------------------------------------------------

def _results(*, valid=True, series=0, grids=0, scatter=0, messages=(), text=True,
             ny=2, nx=3, values=True, series_x=None, series_y=None, num_points=2):
    """Build a fake native analysis result using only reflected member names.

    Grid and scatter objects are created once and returned by the indexed getters so a
    test can adjust the same instance the collector will read.
    """
    message_objects = [NS(ErrorCode=code, Text=text_value) for code, text_value in messages]

    def get_series(index):
        x_rows = series_x if series_x is not None else [1.0, 2.0]
        y_rows = series_y if series_y is not None else [[3.0], [4.0]]
        return NS(Description=f'curve {index}', XLabel='x', SeriesLabels=None,
                  XData=NS(Data=Arr(x_rows, 1)), YData=NS(Data=Arr(y_rows, 2)))

    def matrix_values(row, column):
        return float(row + column)

    def make_grid(index):
        grid = NS(Description=f'grid {index}', XLabel='x', YLabel='y', ValueLabel='v',
                  Nx=nx, Ny=ny, Dx=0.5, Dy=0.5, MinX=0.0, MinY=0.0)
        if values:
            grid.Values = Arr([[matrix_values(r, c) for c in range(nx)] for r in range(ny)], 2)
        else:
            grid.Values = None
            grid.ValueData = NS(Rows=ny, Cols=nx, GetValueAt=matrix_values,
                                Data=Arr([[matrix_values(r, c) for c in range(nx)] for r in range(ny)], 2))
        return grid

    def make_scatter(index):
        points = [NS(X=float(i), Y=1.0, Value=2.0) for i in range(num_points)]
        return NS(Description='points', NumPoints=num_points, XLabel='x', YLabel='y',
                  ValueLabel='v', Points=points,
                  GetPoint=lambda i: points[i])

    grid_objects = [make_grid(index) for index in range(grids)]
    scatter_objects = [make_scatter(index) for index in range(scatter)]

    def get_text_file(path):
        if not text:
            return False
        Path(path).write_text('', encoding='utf-16')  # BOM only
        return True

    return NS(IsValid=valid, HeaderData=NS(Lines=['line']), NumberOfMessages=len(message_objects),
              GetMessageAt=lambda i: message_objects[i], NumberOfDataSeries=series,
              GetDataSeries=get_series, NumberOfDataGrids=grids,
              GetDataGrid=lambda i: grid_objects[i], NumberOfDataScatterPoints=scatter,
              GetDataScatterPoint=lambda i: scatter_objects[i], GetTextFile=get_text_file)


def _backend(*, enabled=True, close_ok=True):
    calls = dict(closed=[], started=[], settings_calls=[])
    application = NS(IsSTARModuleEnabled=enabled)
    tool = NS(GetSettings=lambda: (calls['settings_calls'].append(1), NS(IsValid=True, Parent=None))[1])
    calls['tool'] = tool

    def close(holder):
        calls['closed'].append(holder['native'])
        holder['cleanup_warnings'] = ['close failed']
        return close_ok

    def start(kind, native, settings, **kwargs):
        calls['started'].append(dict(kind=kind, native=native, settings=settings, **kwargs))
        return dict(kind=kind, task_id='t1')

    backend = NS(native=NS(application=application), _require_work=lambda: None,
                 _close_task_native=close, _start_task=start, directory=Path('.'))
    backend._collect_general_analysis = lambda task: pytest.fail('generic collector must not be used')
    return backend, calls, tool


def test_disabled_module_is_a_licence_precondition_not_a_missing_factory(monkeypatch):
    import zemax_mcp.imaging as imaging
    backend, calls, _ = _backend(enabled=False)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: pytest.fail('factory must not be called'))
    with pytest.raises(ZemaxError) as info:
        run_star_analysis(backend, STAR_REQUESTS['star_inspect_fea'](kind='star_inspect_fea'))
    assert info.value.code == 'FEATURE_UNAVAILABLE'
    assert info.value.details['native_analysis'] == 'STARInspectFEA'
    assert info.value.details['availability']['enabled'] is False
    assert 'member exists' in info.value.details['note']
    assert calls['started'] == []


def test_enabled_module_creates_through_the_generic_factory(monkeypatch):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    backend, calls, tool = _backend(enabled=True)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool)
    monkeypatch.setattr(analyses, 'scalar_settings', lambda *_: dict(IsValid=True))
    task = run_star_analysis(backend, STAR_REQUESTS['star_sys_viewer'](kind='star_sys_viewer'))
    assert task['kind'] == 'star_sys_viewer'
    started = calls['started'][0]
    assert started['analysis'] is True
    assert started['settings']['native_analysis'] == 'STARSysViewer'
    assert started['settings']['analysis_id'] == 156
    assert 'no IAS_ interface' in started['settings']['settings_support']
    assert calls['settings_calls'] == [1]  # GetSettings read exactly once


def test_settings_unavailable_fields_are_rejected_and_closed(monkeypatch):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    backend, calls, tool = _backend(enabled=True)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool)
    monkeypatch.setattr(analyses, 'scalar_settings', lambda *_: dict(unavailable_fields=['IsValid']))
    with pytest.raises(ZemaxError) as info:
        run_star_analysis(backend, STAR_REQUESTS['star_align_check'](kind='star_align_check'))
    assert info.value.code == 'SETTING_UNAVAILABLE'
    assert info.value.details['unavailable_fields'] == ['IsValid']
    assert calls['closed'] == [tool]
    assert calls['started'] == []


def test_missing_factory_is_reported(monkeypatch):
    import zemax_mcp.imaging as imaging
    backend, calls, _ = _backend(enabled=True)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: None)
    with pytest.raises(ZemaxError) as info:
        run_star_analysis(backend, STAR_REQUESTS['star_2d_def_plot'](kind='star_2d_def_plot'))
    assert info.value.code == 'NATIVE_INTERFACE_UNAVAILABLE'
    assert info.value.details['native_analysis'] == 'STAR2DDefPlot'
    assert calls['started'] == []


def test_settings_readback_failure_closes_without_losing_the_error(monkeypatch):
    import zemax_mcp.analyses as analyses
    import zemax_mcp.imaging as imaging
    backend, calls, tool = _backend(enabled=True, close_ok=False)
    monkeypatch.setattr(imaging, 'new_analysis', lambda *_: tool)

    def reject(*_):
        raise ZemaxError('SETTING_UNAVAILABLE', 'original')

    monkeypatch.setattr(analyses, 'scalar_settings', reject)
    with pytest.raises(ZemaxError) as info:
        run_star_analysis(backend, STAR_REQUESTS['star_perf_change'](kind='star_perf_change'))
    assert info.value.code == 'SETTING_UNAVAILABLE' and str(info.value) == 'original'
    assert calls['closed'] == [tool]
    assert info.value.details['cleanup_warnings'] == ['close failed']


# --- collection -------------------------------------------------------------

def _task(results):
    return dict(task_id='t1', native=NS(GetResults=lambda: results), settings={})


def test_text_export_false_keeps_native_series(tmp_path):
    """The generic collector would raise EXPORT_FAILED here and lose the curve."""
    backend = NS(directory=tmp_path)
    payload = collect_star_results(backend, _task(_results(series=1, text=False)), 'star_inspect_fea')
    assert payload['text_export']['exported'] is False
    assert payload['text_export']['error'] == 'GetTextFile returned false'
    assert len(payload['series']) == 1
    assert payload['structured_data_available'] is True
    assert payload['artifacts'] == []  # no fake text path is advertised
    assert payload['series'][0]['y'] == [[3.0], [4.0]]
    assert 'rows' not in payload  # a series-only result keeps the generic paging path


def test_bom_only_text_without_data_is_no_result(tmp_path):
    backend = NS(directory=tmp_path)
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(_results(text=True)), 'star_sys_viewer')
    assert info.value.code == 'NO_RESULT_DATA'
    assert info.value.details['text_export']['exported'] is True
    assert info.value.details['text_export']['non_blank_lines'] == 0
    assert 'title-only' in info.value.details['note']


def test_fatal_message_without_data_keeps_the_original_messages(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(text=False, messages=[('Failed', 'STAR module not enabled')])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_align_check')
    assert info.value.code == 'ANALYSIS_FAILED'
    assert info.value.details['native_messages'][0]['text'] == 'STAR module not enabled'
    assert info.value.details['fatal_messages'][0]['code'] == 'Failed'


def test_every_non_success_error_type_is_fatal():
    """Only Success is non-fatal; all 13 other official codes are concrete failures."""
    error_type = dump_document()['enums']['ZOSAPI.Analysis.ErrorType']
    non_success = set(error_type) - {'Success'}
    assert non_success == set(FATAL_MESSAGE_TYPES)
    for code in non_success:
        messages = [{'code': code, 'text': 'm', 'severity': 'fatal'}]
        assert len(fatal_messages(messages)) == 1, code
    assert fatal_messages([{'code': 'Success', 'text': 'ok', 'severity': 'information'}]) == []


def test_fatal_message_with_structured_data_is_not_success(tmp_path):
    """A fatal message keeps the data as partial_result but never returns success."""
    backend = NS(directory=tmp_path)
    results = _results(grids=1, text=False, messages=[('HPCNotAvailable', 'no HPC')])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_2d_def_plot')
    assert info.value.code == 'ANALYSIS_FAILED'
    assert info.value.details['fatal_messages'][0]['code'] == 'HPCNotAvailable'
    partial = info.value.details['partial_result']
    assert len(partial['grids']) == 1 and partial['grids'][0]['rows_returned'] == 2
    assert partial['series'] == [] and partial['scatter'] == []


def test_empty_series_is_not_a_structured_result(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(series=1, text=False, series_x=[], series_y=[])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_inspect_fea')
    assert info.value.code == 'NO_RESULT_DATA'
    assert info.value.details['empty_collections'][0]['kind'] == 'series'


def test_zero_column_series_is_not_a_structured_result(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(series=1, text=False, series_x=[1.0, 2.0], series_y=[[], []])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_inspect_fea')
    assert info.value.code == 'NO_RESULT_DATA'
    assert info.value.details['empty_collections'][0]['reason'] == 'no points or no value columns'


def test_zero_point_scatter_block_is_not_a_structured_result(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(scatter=1, text=False, num_points=0)
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_perf_change')
    assert info.value.code == 'NO_RESULT_DATA'
    assert info.value.details['empty_collections'][0] == {
        'kind': 'scatter', 'index': 0, 'reason': 'NumPoints == 0'}


def test_empty_collection_does_not_mask_a_valid_one(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(series=1, grids=1, text=False, series_x=[], series_y=[])
    payload = collect_star_results(backend, _task(results), 'star_inspect_fea')
    assert payload['structured_data_available'] is True
    assert payload['series'] == [] and len(payload['grids']) == 1
    assert payload['empty_collections'][0]['kind'] == 'series'


def test_non_fatal_message_does_not_make_an_empty_result_an_error(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(text=False, messages=[('Success', 'ok'), ('UnknownFutureCode', 'note')])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_index_vs_temp')
    assert info.value.code == 'NO_RESULT_DATA'
    assert [m['severity'] for m in info.value.details['native_messages']] == ['information', 'information']


def test_invalid_native_result_is_reported_with_messages(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(valid=False, messages=[('Failed', 'failed')])
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_index_vs_temp')
    assert info.value.code == 'ANALYSIS_FAILED'
    assert info.value.details['native_messages'][0]['code'] == 'Failed'


def test_grids_keep_the_complete_ny_by_nx_values(tmp_path):
    backend = NS(directory=tmp_path)
    payload = collect_star_results(backend, _task(_results(grids=1, text=False, ny=5, nx=4)), 'star_2d_def_plot')
    grid = payload['grids'][0]
    assert grid['nx'] == 4 and grid['ny'] == 5
    assert len(grid['values']) == 5 and all(len(row) == 4 for row in grid['values'])
    assert grid['rows_returned'] == 5
    assert 'truncated' not in grid and 'row_limit' not in grid
    assert grid['values_source'].startswith('IAR_DataGrid.Values')
    assert payload['structured_data_available'] is True


def test_grid_values_fall_back_to_the_value_data_matrix(tmp_path):
    backend = NS(directory=tmp_path)
    payload = collect_star_results(backend, _task(_results(grids=1, text=False, values=False)), 'star_2d_def_plot')
    grid = payload['grids'][0]
    assert grid['values'] == [[0.0, 1.0, 2.0], [1.0, 2.0, 3.0]]
    assert grid['values_source'].startswith('IAR_DataGrid.ValueData')


def test_grid_without_any_values_is_invalid(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(grids=1, text=False, values=False)
    grid = results.GetDataGrid(0)
    grid.ValueData = None
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_2d_def_plot')
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert '既无 Values 也无 ValueData' in str(info.value)


def test_grid_value_data_size_mismatch_is_invalid():
    grid = NS(Nx=3, Ny=2, Values=None, ValueData=NS(Rows=2, Cols=5, GetValueAt=lambda r, c: 0.0))
    with pytest.raises(ZemaxError) as info:
        grid_values(grid, 0)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['matrix_cols'] == 5


def test_grid_shape_mismatch_is_invalid():
    grid = NS(Nx=3, Ny=3, Values=Arr([[0.0, 1.0, 2.0], [1.0, 2.0, 3.0]], 2))
    with pytest.raises(ZemaxError) as info:
        grid_values(grid, 0)
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['rows_returned'] == 2


def test_scatter_uses_the_official_collection(tmp_path):
    backend = NS(directory=tmp_path)
    payload = collect_star_results(backend, _task(_results(scatter=1, text=False)), 'star_perf_change')
    block = payload['scatter'][0]
    assert block['count'] == 2
    assert block['points_source'].startswith('IAR_DataScatterPoints.Points')
    assert block['points'][1]['x'] == 1.0
    assert [row['x'] for row in payload['rows']] == [0.0, 1.0]
    assert 'scatter_points' not in payload
    assert payload['structured_data_available'] is True


def test_scatter_falls_back_to_get_point_and_rejects_count_mismatch(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(scatter=1, text=False)
    block = results.GetDataScatterPoint(0)
    block.Points = None
    payload = collect_star_results(backend, _task(results), 'star_perf_change')
    assert payload['scatter'][0]['points_source'] == 'IAR_DataScatterPoints.GetPoint(Int32)'

    # Put the collection back but claim one more point than it holds.
    block.Points = [NS(X=0.0, Y=1.0, Value=2.0), NS(X=1.0, Y=1.0, Value=2.0)]
    block.NumPoints = 3
    with pytest.raises(ZemaxError) as info:
        collect_star_results(backend, _task(results), 'star_perf_change')
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert info.value.details['num_points'] == 3
    assert info.value.details['points_returned'] == 2


def test_scatter_non_finite_values_stay_in_rows_but_not_in_points(tmp_path):
    backend = NS(directory=tmp_path)
    results = _results(scatter=1, text=False)
    block = results.GetDataScatterPoint(0)
    block.Points = [NS(X=float('nan'), Y=1.0, Value=2.0), NS(X=0.0, Y=1.0, Value=2.0)]
    payload = collect_star_results(backend, _task(results), 'star_perf_change')
    collected = payload['scatter'][0]
    # The image list keeps only the finite point; the raw row keeps the invalid one.
    assert [p['x'] for p in collected['points']] == [0.0]
    assert collected['invalid_count'] == 1
    assert payload['rows'][0] == {'block': 0, 'point': 0, 'x': None, 'y': 1.0,
                                 'value': 2.0, 'valid': False}
    assert payload['rows'][1]['valid'] is True
    assert payload['structured_data_available'] is True


def test_collection_does_not_depend_on_the_generic_collector(tmp_path):
    """A hard failure in the generic collector must not be reachable from here."""
    backend = NS(directory=tmp_path)
    backend._collect_general_analysis = lambda task: pytest.fail('generic collector used')
    payload = collect_star_results(backend, _task(_results(series=1)), 'star_inspect_fea')
    assert payload['structured_data_available'] is True


# --- real Backend paging and real image export ------------------------------
# These drive the shared result contract, not a fake collector: the payload is produced by
# collect_star_results and consumed by Backend._page_task_result / plotting.export_image.

def _payload(tmp_path, **kwargs):
    backend = NS(directory=tmp_path)
    return collect_star_results(backend, _task(_results(text=False, **kwargs)), 'star_perf_change')


def test_backend_pages_scatter_rows_and_hides_points(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.models import TaskResult

    payload = _payload(tmp_path, scatter=1, num_points=5)
    page = Backend._page_task_result(
        None, payload, TaskResult(task_id='t1', start=0, count=2))
    # The big point array is stripped from scatter and the page comes from rows.
    assert 'points' not in page['scatter'][0]
    assert page['scatter'][0]['point_count'] == 5
    assert page['scatter_data_in_artifacts'] is True
    assert [row['point'] for row in page['rows']] == [0, 1]
    assert page['total'] == 5 and page['next_start'] == 2

    last = Backend._page_task_result(
        None, payload, TaskResult(task_id='t1', start=4, count=2))
    assert [row['point'] for row in last['rows']] == [4]
    assert last['next_start'] is None


def test_backend_reads_a_non_square_grid_region(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.models import TaskResult

    payload = _payload(tmp_path, grids=1, ny=3, nx=5)
    page = Backend._page_task_result(
        None, payload,
        TaskResult(task_id='t1', grid=0, x_start=1, y_start=1, width=2, height=2))
    grid = page['grid']
    assert grid['x_start'] == 1 and grid['y_start'] == 1
    assert grid['values'] == [[2.0, 3.0], [3.0, 4.0]]  # (row+col) over y 1..3, x 1..3
    assert grid['next_x'] == 3 and grid['next_y'] is None
    assert 'grids' not in page  # a grid region page returns the single grid only


def test_export_image_draws_scatter_with_only_finite_points(tmp_path):
    from zemax_mcp.plotting import export_image

    payload = _payload(tmp_path, scatter=1)
    output = tmp_path / 'scatter.png'
    request = NS(source='data_plot', item=0, width=320, height=240)
    value = export_image(payload, request, output)
    assert output.is_file() and output.stat().st_size > 0
    assert value['plotting_settings']['data_kind'] == 'scatter'
    assert value['artifacts'][0]['kind'] == 'plot'

    # A block whose only point is invalid has nothing finite to plot.
    backend = NS(directory=tmp_path)
    results = _results(scatter=1, text=False, num_points=1)
    results.GetDataScatterPoint(0).Points = [NS(X=float('nan'), Y=1.0, Value=2.0)]
    with_invalid = collect_star_results(backend, _task(results), 'star_perf_change')
    with pytest.raises(ZemaxError) as info:
        export_image(with_invalid, request, tmp_path / 'empty.png')
    assert info.value.code == 'NO_PLOTTABLE_DATA'
