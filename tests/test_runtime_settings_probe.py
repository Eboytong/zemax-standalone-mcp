import csv
from types import SimpleNamespace as N
import pytest
from support import runtime_settings_probe as probe


@pytest.mark.parametrize('state',['blocked','pending'])
@pytest.mark.parametrize('fail_settings,close_ok',[(False,True),(True,True),(False,False)])
def test_runtime_probe_closes_analysis_and_disconnects(tmp_path,monkeypatch,fail_settings,close_ok,state):
    docs=tmp_path/'docs';docs.mkdir()
    with (docs/'development-backlog.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['work_package','execution_state','item_id','native_enum'])
        writer.writeheader();writer.writerow(dict(work_package='PO-01',execution_state=state,item_id='PO-01.Transmission',native_enum='Transmission'))
    events=[]
    typ=N(FullName='Test.AS_Default',GetInterfaces=lambda:[],GetMethods=lambda:[],GetProperties=lambda:[])
    def settings():
        if fail_settings:raise RuntimeError('settings failure')
        return N(GetType=lambda:typ)
    def dispatch(name,args):events.append(name);return dict(ok=True)
    def close(owner):events.append('analysis_close');return close_ok
    backend=N(dispatch=dispatch,_close_task_native=close,
        native=N(enum=lambda t,name:name,api=N(Analysis=N(AnalysisIDM=object()))),
        system=N(Analyses=N(New_Analysis_SettingsFirst=lambda _:N(GetSettings=settings))))
    monkeypatch.setattr(probe,'ROOT',tmp_path)
    monkeypatch.setattr(probe,'Backend',lambda _:backend)
    result=probe.run('PO-01',tmp_path/'evidence')
    assert result['closed'] and result['items'][0]['closed']==close_ok
    assert events==['connect','new_system','analysis_close','disconnect']
    assert bool(result['items'][0].get('error'))==fail_settings
    assert result['settings_writes']==result['calculations']==0


def test_runtime_probe_null_factory_in_explicit_mode(tmp_path,monkeypatch):
    docs=tmp_path/'docs';docs.mkdir()
    with (docs/'development-backlog.csv').open('w',encoding='utf-8',newline='')as stream:
        writer=csv.DictWriter(stream,fieldnames=['work_package','execution_state','item_id','native_enum'])
        writer.writeheader();writer.writerow(dict(work_package='NS-04',execution_state='in_progress',item_id='NS-04.Viewer',native_enum='Viewer'))
    events=[]
    def dispatch(name,args):events.append((name,args));return dict(ok=True)
    backend=N(dispatch=dispatch,native=N(enum=lambda _,name:name,api=N(Analysis=N(AnalysisIDM=object()))),system=N(Analyses=N(New_Analysis_SettingsFirst=lambda _:None)))
    monkeypatch.setattr(probe,'ROOT',tmp_path);monkeypatch.setattr(probe,'Backend',lambda _:backend)
    result=probe.run('NS-04',tmp_path/'evidence',mode='Sequential',include_active=True)
    assert result['items'][0]['factory_result']=='null; no owned analysis'
    assert result['system_mode']=='Sequential' and result['closed']
    assert events[1]==('new_system',dict(mode='Sequential'))
