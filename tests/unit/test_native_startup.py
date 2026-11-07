"""Stage attribution and ownership during startup, without loading the local CLR."""
import json
import sys
from types import SimpleNamespace as N
import pytest
from zemax_mcp.native import NativeSession
from zemax_mcp.errors import ZemaxError


def setup_native(tmp_path,monkeypatch,*,failure=None,close_error=None,observer=None):
    install=tmp_path/'install';install.mkdir()
    for name in ['ZOSAPI_NetHelper.dll','ZOSAPI_Interfaces.dll','ZOSAPI.dll']:(install/name).write_bytes(b'')
    events=[];closes=[];references=[]
    def stage(name,value=None):
        if failure==name:raise RuntimeError('controlled '+name)
        return value
    def close():
        closes.append(True)
        if isinstance(close_error,Exception):raise close_error
        return close_error
    app=N(IsValidLicenseForAPI=failure!='invalid_license',PrimarySystem=None if failure=='no_system'else N(),CloseApplication=close)
    def create():return stage('application_create',None if failure=='no_application'else app)
    monkeypatch.setattr('zemax_mcp.native.restore_user_environment',lambda:stage('environment'))
    monkeypatch.setitem(sys.modules,'pythonnet',N(load=lambda runtime:stage('clr_load')))
    monkeypatch.setitem(sys.modules,'System',N(Console=N(Error=object(),SetOut=lambda stream:None)))
    def add_reference(path):
        references.append(path)
        stage('nethelper_assembly'if path.endswith('NetHelper.dll')else 'api_assemblies')
    monkeypatch.setitem(sys.modules,'clr',N(AddReference=add_reference))
    monkeypatch.setitem(sys.modules,'ZOSAPI_NetHelper',N(ZOSAPI_Initializer=N(Initialize=lambda path:stage('zos_initialize',failure!='initialize_false'))))
    monkeypatch.setitem(sys.modules,'ZOSAPI',N(ZOSAPI_Connection=lambda:stage('connection_create',N(CreateNewApplication=create))))
    native=NativeSession(stage_observer=observer or events.append)
    return native,install,app,events,closes,references


def test_startup_stage_sequence_reuse_and_close(tmp_path,monkeypatch,capsys):
    s,install,app,events,closes,_=setup_native(tmp_path,monkeypatch)
    assert s.connect(install)is app
    completed=[x['stage']for x in events if x['event']=='completed']
    assert completed==['install_check','environment','clr_load','nethelper_assembly','zos_initialize',
        'api_assemblies','connection_create','application_create','license_check','primary_system']
    assert all(x['duration_seconds']>=0 for x in events if x['event']=='completed')
    assert s.connect(install)is app and len(events)==20
    s.disconnect();s.disconnect()
    assert len(closes)==1 and s.application is None and s.connection is None
    assert events[-1]['stage']=='application_close'and events[-1]['event']=='completed'
    assert capsys.readouterr().out==''


@pytest.mark.parametrize('failure,stage,code',[
    ('environment','environment','NATIVE_ERROR'),('clr_load','clr_load','NATIVE_ERROR'),
    ('nethelper_assembly','nethelper_assembly','NATIVE_ERROR'),('zos_initialize','zos_initialize','NATIVE_ERROR'),
    ('initialize_false','zos_initialize','INITIALIZATION_FAILED'),('api_assemblies','api_assemblies','NATIVE_ERROR'),
    ('connection_create','connection_create','NATIVE_ERROR'),('application_create','application_create','NATIVE_ERROR'),
    ('no_application','application_create','CONNECTION_FAILED'),('invalid_license','license_check','INVALID_LICENSE'),
    ('no_system','primary_system','SYSTEM_NOT_AVAILABLE'),
])
def test_startup_failure_source_and_ownership(tmp_path,monkeypatch,failure,stage,code):
    s,install,_,events,closes,_=setup_native(tmp_path,monkeypatch,failure=failure)
    with pytest.raises(ZemaxError)as caught:s.connect(install)
    assert caught.value.code==code and caught.value.details['startup_stage']==stage
    assert any(e['stage']==stage and e['event']=='failed'for e in caught.value.details['startup_events'])
    assert len(closes)==int(failure in ['invalid_license','no_system'])
    assert s.application is None and s.connection is None
    json.dumps(caught.value.as_dict())


@pytest.mark.parametrize('close_error',[False,RuntimeError('controlled close failure')])
def test_validation_and_close_failures_preserved(tmp_path,monkeypatch,close_error):
    s,install,app,events,closes,_=setup_native(tmp_path,monkeypatch,failure='invalid_license',close_error=close_error)
    with pytest.raises(ZemaxError)as caught:s.connect(install)
    assert caught.value.code=='INVALID_LICENSE'
    assert caught.value.details['startup_stage']=='license_check'
    assert 'cleanup_error'in caught.value.details
    assert s.application is app and len(closes)==1
    with pytest.raises(ZemaxError,match='仍待确认关闭'):s.connect(install)
    with pytest.raises(ZemaxError)as access:s.system
    assert access.value.code=='NOT_CONNECTED'
    json.dumps(caught.value.as_dict())


def test_loaded_assembly_directory_survives_failed_initialization(tmp_path,monkeypatch):
    s,install,_,_,_,_=setup_native(tmp_path,monkeypatch,failure='initialize_false')
    with pytest.raises(ZemaxError):s.connect(install)
    assert s.loaded_dir==install.resolve()
    with pytest.raises(ZemaxError)as caught:s.connect(tmp_path/'other')
    assert caught.value.code=='RESTART_REQUIRED'


def test_observer_failure_does_not_replace_native_outcome(tmp_path,monkeypatch):
    def bad(event):raise OSError('controlled diagnostic write failure')
    s,install,app,_,_,_=setup_native(tmp_path,monkeypatch,observer=bad)
    assert s.connect(install)is app and len(s.observer_warnings)==20
    s.disconnect()
    assert len(s.observer_warnings)==22


def test_missing_install_reports_stage(tmp_path):
    s=NativeSession()
    with pytest.raises(ZemaxError)as caught:s.connect(tmp_path)
    assert caught.value.code=='INSTALL_NOT_FOUND'
    assert caught.value.details['startup_stage']=='install_check'


def test_backend_startup_cleanup_failure_remains_queryable(tmp_path,monkeypatch):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    s,install,app,_,_,_=setup_native(tmp_path,monkeypatch,failure='invalid_license',close_error=False)
    b=Backend(Config(install,tmp_path/'output'),native=s)
    failed=b.dispatch('connect',{})
    assert not failed['ok']and failed['error']['code']=='INVALID_LICENSE'
    assert failed['context']['requires_reconnect']
    status=b.dispatch('get_status',{})
    assert status['ok']and not status['data']['connected']
    assert status['data']['native_startup']['events'][-1]['stage']=='application_close'
    blocked=b.dispatch('connect',{})
    assert blocked['error']['code']=='RECONNECT_REQUIRED'


def test_failed_disconnect_can_retry_without_accessing_unready_system(tmp_path,monkeypatch):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    s,install,app,_,_,_=setup_native(tmp_path,monkeypatch,close_error=False)
    s.connect(install)
    b=Backend(Config(install,tmp_path/'output'),native=s)
    b.work_path=tmp_path/'model.zos'
    checkpoints=[]
    b._checkpoint=lambda label:checkpoints.append(label)
    with pytest.raises(ZemaxError):b.disconnect(None)
    assert b.requires_reconnect and not s.connection_ready
    app.CloseApplication=lambda:None
    result=b.disconnect(None)
    assert not result['connected']and s.application is None
    assert checkpoints==['disconnect']
