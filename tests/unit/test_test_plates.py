from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.test_plates import parse_tpd, parse_native, catalog_resources, run_test_plates


@pytest.mark.parametrize('patch', [dict(catalog_file=''), dict(catalog_file='../x.tpd'),
    dict(catalog_file='C:x.tpd'), dict(catalog_file='x.txt'), dict(method='file'), dict(method='unknown')])
def test_invalid_request(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='test_plate_list') | patch)


def test_tpd_identity_units_and_availability():
    headers, rows = parse_tpd('! Vendor\nA 12.345678 9 -1\nB 13 10 0\nC 14 11 1\n')
    assert headers == ['Vendor']
    assert [(r['plate_id'], r['concave'], r['convex']) for r in rows] == [('A', True, False), ('B', True, True), ('C', False, True)]
    assert rows[0]['radius_mm'] == 12.345678


@pytest.mark.parametrize('text', ['! empty', 'A 1 2', 'A NaN 2 0', 'A 1 inf 0', 'A 0 2 0', 'A 1 2 3', 'A 1 2 0.5'])
def test_bad_resource_data(text):
    with pytest.raises(ZemaxError):
        parse_tpd(text)


def test_native_fixture_against_independent_first_record():
    text = Path('development/evidence/MF-01/probe427-viewers/TestPlateList.txt').read_text(encoding='utf-16')
    name, rows = parse_native(text, ['Applied.tpd', 'Other.tpd'])
    assert name == 'Applied.tpd' and len(rows) > 800
    assert rows[0] == dict(index=0, plate_id='1', radius_mm=2.5, diameter_mm=5.1, concave=True, convex=True, availability_code=0, source_line=rows[0]['source_line'])
    assert next(r for r in rows if r['plate_id'] == '891')['convex'] is False
    assert next(r for r in rows if r['plate_id'] == '864')['concave'] is False


def test_unknown_native_identity_and_empty_report():
    for text in ['', 'Catalog Other.tpd\nA\t1\t2\tX\tX', 'Catalog Applied.tpd\n']:
        with pytest.raises(ZemaxError):
            parse_native(text, ['Applied.tpd'])


@pytest.mark.parametrize('data', ['A\tbad\t2\tX\tX', 'A\tNaN\t2\tX\tX', 'A\t1\t2\tX\tX\nB\t1\t2'])
def test_native_bad_rows_are_not_silently_dropped(data):
    with pytest.raises(ZemaxError):
        parse_native('Catalog Applied.tpd\n' + data, ['Applied.tpd'])


def test_resource_discovery_and_explicit_file_rows(tmp_path):
    directory = tmp_path / 'Testplate'
    directory.mkdir()
    (directory / 'One.TPD').write_text('! Own test input\nunique 2.4 3 -1\n', encoding='utf-8')
    (directory / 'ignore.txt').write_text('ignore')
    application = NS(ZemaxDataDir=str(tmp_path))
    assert catalog_resources(application) == (directory, ['One.TPD'])
    task = dict(rows=[])
    def composite(kind, settings, flow):
        list(flow(task))
        return task
    b = NS(native=NS(application=application), _require_sequential=lambda: None, _require_work=lambda: None,
           _cancel_boundary=lambda t: None, _composite=composite)
    r = run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list', catalog_file='one.tpd', method='file')).request)
    assert r['rows'][0]['plate_id'] == 'unique'
    assert r['payload']['actual_settings']['catalog_file'] == 'One.TPD'
    assert r['summary']['plates'] == 1
    with pytest.raises(ZemaxError) as error:
        run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list', catalog_file='missing.tpd')).request)
    assert error.value.code == 'INVALID_RESOURCE'


def fake_native(tmp_path, *, export=True, closed=True, running=False, malformed=False, cfg_loaded=True):
    directory = tmp_path / 'Testplate'
    directory.mkdir()
    (directory / 'Active.tpd').write_text('A 1 2 0')
    (directory / 'Other.tpd').write_text('B 2 3 1')
    state = dict(close_count=0, cancel=False)
    def text(path):
        if not export:
            return False
        Path(path).write_text('unknown' if malformed else '目录 Active.tpd\nA\t1.0000\t2.0000\tX\tX\n', encoding='utf-16')
        return True
    def load(path):
        state['loaded_path'] = path
        return cfg_loaded
    tool = NS(GetSettings=lambda: NS(GetType=lambda: NS(FullName='AS_Default'), LoadFrom=load),
              Apply=lambda: None, IsRunning=lambda: running,
              GetResults=lambda: NS(GetTextFile=text, NumberOfMessages=0))
    def close(owner):
        state['close_count'] += 1
        owner['cleanup_warnings'] = [] if closed else ['native Close refused']
        return closed
    def cancel(task):
        if state['cancel']:
            raise ZemaxError('CANCEL_TEST', 'cancel injected')
    task = dict(task_id='task', rows=[])
    def composite(kind, settings, flow):
        task['iterator'] = flow(task)
        return task
    b = NS(native=NS(application=NS(ZemaxDataDir=str(tmp_path)), enum=lambda _, value: value,
                     api=NS(Analysis=NS(AnalysisIDM=None))), directory=tmp_path,
           system=NS(Analyses=NS(New_Analysis_SettingsFirst=lambda _: tool)),
           _close_task_native=close, _require_sequential=lambda: None, _require_work=lambda: None,
           _cancel_boundary=cancel, _composite=composite)
    return b, task, state


@pytest.mark.parametrize('method', ['native', 'auto'])
def test_native_catalog_mismatch_is_explicit(tmp_path, method):
    b, task, state = fake_native(tmp_path)
    run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list', method=method, catalog_file='Other.tpd')).request)
    if method == 'native':
        with pytest.raises(ZemaxError) as error:
            list(task['iterator'])
        assert error.value.code == 'SETTING_NOT_SUPPORTED'
        assert error.value.details['actual'] == 'Active.tpd'
    else:
        list(task['iterator'])
        assert task['rows'][0]['plate_id'] == 'B'
        assert task['payload']['fallback_reason']['actual'] == 'Active.tpd'
    assert state['close_count'] == 1


@pytest.mark.parametrize('failure', ['export', 'format', 'cancel'])
def test_native_failure_and_cancellation_close_owned_analysis(tmp_path, failure):
    b, task, state = fake_native(tmp_path, export=failure != 'export', running=failure == 'cancel', malformed=failure == 'format')
    run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list')).request)
    if failure == 'cancel':
        next(task['iterator'])
        state['cancel'] = True
    with pytest.raises(ZemaxError):
        list(task['iterator'])
    assert state['close_count'] == 1 and task['payload']['native_closed'] is True


def test_close_failure_retains_original_export_error(tmp_path):
    b, task, state = fake_native(tmp_path, export=False, closed=False)
    run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list')).request)
    with pytest.raises(ZemaxError) as error:
        list(task['iterator'])
    assert error.value.code == 'NO_RESULT_DATA'
    assert error.value.details['cleanup_warnings'] == ['native Close refused']


@pytest.mark.parametrize('value', ['', 'relative.CFG', 'C:\\bad.txt'])
def test_cfg_path_contract(value):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='test_plate_list', native_settings_file=value))


def test_cfg_file_method_conflict(tmp_path):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='test_plate_list', catalog_file='Active.tpd', method='file',
                                 native_settings_file=str(tmp_path / 'native.CFG')))


@pytest.mark.parametrize('accepted', [True, False])
def test_native_configuration_load_and_close(tmp_path, accepted):
    b, task, state = fake_native(tmp_path, cfg_loaded=accepted)
    cfg = tmp_path / 'native.CFG'
    cfg.write_bytes(b'owned native configuration')
    run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list', method='native',
        catalog_file='Active.tpd', native_settings_file=str(cfg))).request)
    if accepted:
        list(task['iterator'])
        assert task['payload']['native_configuration']['actual_catalog_file'] == 'Active.tpd'
        assert task['payload']['computation_method'] == 'native_TestPlateList_text'
    else:
        with pytest.raises(ZemaxError, match='配置加载') as error:
            list(task['iterator'])
        assert error.value.code == 'CFG_LOAD_FAILED'
    assert state['loaded_path'] == str(cfg)
    assert state['close_count'] == 1


def test_explicit_cfg_mismatch_never_uses_file_fallback(tmp_path):
    b, task, state = fake_native(tmp_path)
    cfg = tmp_path / 'native.CFG'
    cfg.write_bytes(b'owned native configuration')
    run_test_plates(b, RunAnalysis(request=dict(kind='test_plate_list', method='auto',
        catalog_file='Other.tpd', native_settings_file=str(cfg))).request)
    with pytest.raises(ZemaxError) as error:
        list(task['iterator'])
    assert error.value.details['actual'] == 'Active.tpd'
    assert state['close_count'] == 1
    assert 'fallback_reason' not in task['payload']
