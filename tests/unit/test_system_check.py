import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.system_check import report_rows
from zemax_mcp.errors import ZemaxError


def test_request():
    assert RunAnalysis(request=dict(kind='system_check')).request.kind == 'system_check'
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='system_check', configuration=1))


def test_report(tmp_path):
    p=tmp_path/'report.txt'
    p.write_text('错误列表\n\n2 警告.\n',encoding='utf-16')
    r=report_rows(dict(artifacts=[dict(kind='native_text',path=str(p))]))
    assert r['rows'][2]==dict(line=3,text='2 警告.')
    assert r['rows'][1]['text']==''
    assert r['analysis_kind']=='system_check'


@pytest.mark.parametrize('content',[None,'','   '])
def test_missing_report(tmp_path,content):
    artifacts=[]
    if content is not None:
        p=tmp_path/'r.txt';p.write_text(content,encoding='utf-16')
        artifacts=[dict(kind='native_text',path=str(p))]
    with pytest.raises(ZemaxError)as e:
        report_rows(dict(artifacts=artifacts,native_messages=['original']))
    assert e.value.code=='NO_RESULT_DATA'
    assert e.value.details['native_messages']==['original']


def test_bad_format(tmp_path):
    p=tmp_path/'r.txt';p.write_bytes(b'abc')
    with pytest.raises(ZemaxError)as e:
        report_rows(dict(artifacts=[dict(kind='native_text',path=str(p))]))
    assert e.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('closed',[True,False])
def test_settings_error_closes_without_losing_original(monkeypatch,closed):
    from types import SimpleNamespace as N
    from zemax_mcp.system_check import run_system_check, SystemCheck
    import zemax_mcp.imaging as imaging
    import zemax_mcp.analyses as analyses
    tool=N(GetSettings=lambda:object());calls=[]
    monkeypatch.setattr(imaging,'new_analysis',lambda *_:tool)
    def reject(*_):raise ZemaxError('SETTING_UNAVAILABLE','original')
    monkeypatch.setattr(analyses,'scalar_settings',reject)
    def close(holder):
        calls.append(holder['native']);holder['cleanup_warnings']=['close failed'];return closed
    b=N(_require_work=lambda:None,_close_task_native=close)
    with pytest.raises(ZemaxError)as e:run_system_check(b,SystemCheck(kind='system_check'))
    assert e.value.code=='SETTING_UNAVAILABLE' and str(e.value)=='original'
    assert calls==[tool]
    if not closed:assert e.value.details['cleanup_warnings']==['close failed']


def test_system_data_request_and_report(tmp_path):
    assert RunAnalysis(request=dict(kind='system_data')).request.kind=='system_data'
    p=tmp_path/'r.txt';p.write_text('系统/详细数据\n',encoding='utf-16')
    r=report_rows(dict(artifacts=[dict(kind='native_text',path=str(p))]),'system_data')
    assert r['analysis_kind']=='system_data' and 'diagnostic_semantics' not in r
