from pathlib import Path
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.comparator import FileComparator, configure, report_rows, FLAGS
from zemax_mcp.errors import ZemaxError


def request(**extra):
    return FileComparator(kind='file_comparator', file1='a.zos', file2='b.zmx', **extra)


def test_config_defaults_and_order():
    writes=[]
    values=configure(request(file1_configuration=2,include_general_data=False),[Path('a'),Path('b')],lambda n,v:writes.append((n,v)))
    assert values['File1SpecifyConfig'] and values['File1Config']==2
    assert not values['File2SpecifyConfig'] and 'File2Config' not in values
    assert writes.index(('File1SpecifyConfig',True))<writes.index(('File1Config',2))
    assert values['IncludeGeneralData'] is False
    assert len(FLAGS)==16


@pytest.mark.parametrize('extra',[dict(file1_configuration=0),dict(file2_configuration=-1),dict(file1_configuration=1.5),dict(unknown=True)])
def test_invalid_requests(extra):
    with pytest.raises(ValidationError):request(**extra)


def test_schema_and_union():
    q=RunAnalysis(request=request().model_dump())
    assert q.request.kind=='file_comparator'
    assert 'file_comparator' in RunAnalysis.model_json_schema()['properties']['request']['discriminator']['mapping']


def test_native_lines(tmp_path):
    path=tmp_path/'comparison.txt';path.write_text('标题\n\n50.0 60.0\n',encoding='utf-16')
    result=report_rows(dict(artifacts=[dict(kind='native_text',path=str(path))]))
    assert result['rows']==[dict(line=1,text='标题'),dict(line=2,text=''),dict(line=3,text='50.0 60.0')]


def test_empty_report_preserves_diagnostics(tmp_path):
    path=tmp_path/'empty.txt';path.write_text('',encoding='utf-16')
    with pytest.raises(ZemaxError) as exc:report_rows(dict(artifacts=[dict(kind='native_text',path=str(path))],native_messages=['original']))
    assert exc.value.code=='NO_RESULT_DATA' and exc.value.details['native_messages']==['original']


def test_rejected_setting_stops_configuration():
    writes=[]
    def reject(n,v):
        writes.append(n)
        if n=='File1SpecifyConfig':raise ZemaxError('SETTING_REJECTED','original')
    with pytest.raises(ZemaxError):configure(request(file1_configuration=2),['a','b'],reject)
    assert writes==['File1Name','File1SpecifyConfig']


@pytest.mark.parametrize('closed',[True,False])
def test_setting_failure_closes_and_retains_error(monkeypatch,tmp_path,closed):
    from types import SimpleNamespace
    from zemax_mcp.comparator import run_comparator
    import zemax_mcp.imaging as imaging
    import zemax_mcp.data as data
    paths=[tmp_path/'a.zos',tmp_path/'b.zos']
    for path in paths:path.touch()
    tool=SimpleNamespace(GetSettings=lambda:object())
    calls=[]
    backend=SimpleNamespace(native=None,_require_work=lambda:None)
    def close(holder):
        calls.append(holder['native'])
        holder['cleanup_warnings']=['close failed'] if not closed else []
        return closed
    backend._close_task_native=close
    monkeypatch.setattr(imaging,'new_analysis',lambda *_:tool)
    monkeypatch.setattr(data,'unwrap',lambda value:value)
    def reject(*_):raise ZemaxError('SETTING_REJECTED','original',setting='File1Name')
    monkeypatch.setattr(imaging,'checked',reject)
    with pytest.raises(ZemaxError) as exc:
        run_comparator(backend,FileComparator(kind='file_comparator',file1=str(paths[0]),file2=str(paths[1])))
    assert exc.value.code=='SETTING_REJECTED' and str(exc.value)=='original'
    assert calls==[tool]
    if not closed:assert exc.value.details['cleanup_warnings']==['close failed']


def test_missing_resource_fails_before_factory(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from zemax_mcp.comparator import run_comparator
    import zemax_mcp.imaging as imaging
    def unexpected(*_):pytest.fail('factory should not run')
    monkeypatch.setattr(imaging,'new_analysis',unexpected)
    with pytest.raises(ZemaxError)as exc:
        run_comparator(SimpleNamespace(_require_work=lambda:None),FileComparator(kind='file_comparator',file1=str(tmp_path/'a.zos'),file2=str(tmp_path/'b.zos')))
    assert exc.value.code=='INVALID_INPUT_FILE'


@pytest.mark.parametrize('config,count,load,closed,code',[(2,2,True,True,None),(3,2,True,True,'INDEX_OUT_OF_RANGE'),(1,2,False,True,'LOAD_FAILED'),(3,2,True,False,'INDEX_OUT_OF_RANGE'),(1,2,True,False,'RESOURCE_CLOSE_FAILED')])
def test_configuration_copy_preflight(config,count,load,closed,code):
    from types import SimpleNamespace as N
    from zemax_mcp.comparator import validate_configurations
    calls=[]
    copy=N(MCE=N(NumberOfConfigurations=count),LoadFile=lambda *args:load,Close=lambda save:calls.append(save)or closed)
    backend=N(system=N(CopySystem=lambda:copy),requires_reconnect=False)
    if code:
        with pytest.raises(ZemaxError)as exc:validate_configurations(backend,request(file1_configuration=config),['a','b'])
        assert exc.value.code==code
        if not closed and code=='INDEX_OUT_OF_RANGE':assert 'cleanup_error' in exc.value.details
    else:
        assert validate_configurations(backend,request(file1_configuration=config),['a','b'])==[dict(file=1,configuration_count=2,selected_configuration=2)]
    assert calls==[False]
    assert backend.requires_reconnect is (not closed)

