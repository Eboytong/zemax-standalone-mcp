"""Prepared official loader/settings/IDisposable probe; no public tool is claimed yet."""
import json
import pytest
from tests.support.net_callback_fixture import build,TYPE_NAME
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_controlled_net_callback_loader_and_disposal():
    from zemax_mcp.native import NativeSession
    from zemax_mcp.config import Config
    folder=run_dir('net_callback_contract')
    library=build(folder)
    session=NativeSession();callback=None
    record=dict(callback_type=TYPE_NAME,closed=False,callback_disposed=False,checks=[])
    original=None;cleanup=[]
    try:
        app=session.connect(Config.from_env().install_dir)
        record['version']=str(app.OpticStudioVersion)
        from System import IDisposable
        settings=app.CreateSettings()
        settings.SetDoubleValue('input',1.5)
        callback=app.LoadNETCallback(str(library),TYPE_NAME,settings)
        record['loader_returned_null']=callback is None
        assert callback is not None, 'LoadNETCallback returned null for the controlled assembly/type/settings'
        adopted,value=callback.Settings.GetDoubleValue('input',0.0)
        assert adopted and value==1.5
        record['input']=value
        record['is_local']=bool(callback.IsLocal)
        record['exit_code']=int(callback.Execute())
        assert record['exit_code']==0,record
        present,value=callback.Settings.GetDoubleValue('output',0.0)
        passed=bool(present)and abs(value-3.0)<=1e-12+1e-12*3.0
        record['checks'].append(dict(label='callback settings output',actual=value,expected=3.0,atol=1e-12,rtol=1e-12,passed=passed))
        assert passed,record
        client_present,client_value=settings.GetDoubleValue('output',0.0)
        record['original_settings_output']=dict(present=bool(client_present),value=client_value)
    except Exception as exc:
        original=exc;record['original_error']=str(exc)
        raise
    finally:
        if callback is not None:
            try:
                IDisposable(callback).Dispose();record['callback_disposed']=True
            except Exception as exc:cleanup.append(dict(resource='callback',error=str(exc)))
        try:session.disconnect();record['closed']=True
        except Exception as exc:cleanup.append(dict(resource='application',error=str(exc)))
        record['cleanup_errors']=cleanup
        (folder/'callback-contract.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if cleanup and original is None:raise AssertionError(cleanup)
