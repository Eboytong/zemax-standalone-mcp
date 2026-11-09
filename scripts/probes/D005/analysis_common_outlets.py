"""Bounded official IA_.ToFile and parent-settings contracts in Standalone."""
import json
import os
from pathlib import Path
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter,poll_task,write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.image_viewers import ANALYSIS_IDS


def run(destination,include_settings=False):
    folder=Path(destination).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(calls=[],cases=[],cleanup_failures=[],
        hypothesis='official common analysis methods may expose input settings or file output absent from topic-specific settings')
    call=adapter(backend,record['calls'])
    try:
        call('connect')
        call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['context']=backend.context()
        def baseline():
            return dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),
                merit=call('get_merit_function'),configurations=call('get_configurations'))
        before=baseline()
        cases=[('standard_spot','StandardSpot')]+[(kind,native) for kind,(native,_) in ANALYSIS_IDS.items()]
        for kind,native_name in cases:
            entry=dict(kind=kind,native_name=native_name,parent_settings=[],exports=[]);record['cases'].append(entry)
            tool=None;started=False
            try:
                tool=backend.system.Analyses.New_Analysis_SettingsFirst(getattr(backend.native.api.Analysis.AnalysisIDM,native_name))
                settings=unwrap(tool.GetSettings())
                entry['settings_type']=str(settings.GetType().FullName)
                entry['has_analysis_specific_settings']=bool(tool.HasAnalysisSpecificSettings)
                for parent_name,parent in ([] if include_settings else [('analysis',tool),('settings',settings)]):
                    outcome=dict(parent=parent_name);entry['parent_settings'].append(outcome)
                    try:
                        data=backend.native.application.CreateSettingsFromParent(parent)
                        outcome['available']=data is not None
                        if data is not None:
                            outcome['count']=int(data.NumberOfSettings)
                            outcome['keys']=[str(v) for v in data.GetKeys()]
                    except Exception as exc:outcome['error']=dict(type=type(exc).__name__,message=str(exc))
                def collect(task):
                    result=unwrap(task['native'].GetResults())
                    for suffix in (('.settings.txt',) if include_settings else ('.txt','.png','.zda')):
                        path=folder/(kind+suffix)
                        outcome=dict(path=str(path),showSettings=include_settings,verify=False);entry['exports'].append(outcome)
                        try:
                            task['native'].ToFile(str(path),include_settings,False)
                            outcome['returned']=True
                        except Exception as exc:outcome['error']=dict(type=type(exc).__name__,message=str(exc))
                        outcome['exists']=path.exists()
                        if path.is_file():
                            outcome['bytes']=path.stat().st_size
                            with path.open('rb') as stream:outcome['prefix_hex']=stream.read(32).hex()
                    return dict(rows=[dict(native_valid=bool(result.IsValid),grid_count=int(result.NumberOfDataGrids),
                        scatter_count=int(result.NumberOfDataScatterPoints),series_count=int(result.NumberOfDataSeries))],
                        structured_data_available=True,artifacts=[])
                task=backend._start_task('analysis_common_diagnostic',tool,dict(kind=kind),analysis=True,collector=collect,budget_seconds=60)
                started=True;entry['task']=poll_task(call,task,record,timeout_s=75)
            except Exception as exc:entry['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None and not started:
                    owner=dict(native=tool);entry['setup_close']=backend._close_task_native(owner)
                    if owner.get('cleanup_warnings'):record['cleanup_failures']+=owner['cleanup_warnings']
                write_json(folder/'probe.json',record)
            if backend.active or record['cleanup_failures']:raise RuntimeError('native owner did not close')
        after=baseline();record['model_preserved']={key:before[key]==after[key] for key in before}
    except Exception as exc:record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        try:record['disconnect']=call('disconnect')
        except Exception as exc:record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(error=record.get('error'),cases=[dict(kind=c['kind'],settings=c['parent_settings'],exports=c['exports'],
        state=c.get('task',{}).get('state')) for c in record['cases']],preserved=record.get('model_preserved'),cleanup=record['cleanup_failures']),ensure_ascii=False))
    return record


if __name__=='__main__':
    result=run(sys.argv[1],include_settings='--include-settings' in sys.argv[2:])
    if result.get('error') or result['cleanup_failures']:sys.exit(1)
