"""Bounded native spot-factory comparison; empty outlets are diagnostic only."""
from pathlib import Path
import json
import os
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter,poll_task,paged_result,write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.analyses import scalar_settings
from zemax_mcp.detectors import checked_setting

COUNTS=['NumberOfDataSeries','NumberOfDataSeriesRgb','NumberOfDataGrids','NumberOfDataGridsRgb',
    'NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb','NumberOfRayData','NumberOfMessages']


def summarize(record):
    cases=record.get('cases',[])
    expected={(analysis,factory) for analysis in ('StandardSpot','MatrixSpot','ConfigurationMatrixSpot')
        for factory in ('New_Analysis','New_Analysis_SettingsFirst')}
    actual={(case['analysis_id'],case['factory']) for case in cases}
    execution_complete=(actual==expected and len(cases)==6 and not record.get('error')
        and not record.get('cleanup_failures') and record.get('disconnect',{}).get('connected') is False
        and all(record.get('restored',{}).get(key) is True for key in ('settings','surfaces','merit','configurations'))
        and all(not case.get('error') and case.get('task',{}).get('state')=='succeeded'
            and case['task'].get('close_attempted') is True and not case['task'].get('cleanup_warnings') for case in cases))
    return dict(scope='factory/outlet diagnostic only; feature completion remains open',execution_complete=bool(execution_complete),
        cases=[dict(analysis_id=case['analysis_id'],factory=case['factory'],actual_settings=case.get('actual_settings'),
            task_state=case.get('task',{}).get('state'),close_attempted=case.get('task',{}).get('close_attempted'),
            rows=case.get('result',{}).get('rows'),error=case.get('error')) for case in cases],restored=record.get('restored'))


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    calls=[];call=adapter(backend,calls)
    record=dict(item_ids=['CV-01.MatrixSpot','CV-01.ConfigurationMatrixSpot'],
        source_version='0.1.62 working tree',hypothesis='SettingsFirst factory may expose spot results missing from New_Analysis',
        calls=calls,cases=[],cleanup_failures=[])
    snapshot=None
    def save():write_json(folder/'probe.json',record)
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['context']=backend.context();source,work=backend.source_path,backend.work_path
        baseline=dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),merit=call('get_merit_function'),configurations=call('get_configurations'))
        snapshot=backend._checkpoint('spot_factory_outlets')
        call('update_configurations',dict(actions=[dict(action='add',copy_current=True)]))
        record['configurations']=call('get_configurations')
        for analysis_id in ('StandardSpot','MatrixSpot','ConfigurationMatrixSpot'):
            for factory_name in ('New_Analysis','New_Analysis_SettingsFirst'):
                entry=dict(analysis_id=analysis_id,factory=factory_name);record['cases'].append(entry);native=None;started=False
                try:
                    factory=getattr(backend.system.Analyses,factory_name)
                    native=factory(backend.native.enum(backend.native.api.Analysis.AnalysisIDM,analysis_id))
                    settings=unwrap(native.GetSettings())
                    settings.Field.SetFieldNumber(0);settings.Wavelength.SetWavelengthNumber(0)
                    settings.Surface.UseImageSurface()
                    values=dict(Pattern='Hexapolar',ReferTo='Centroid',RayDensity=6,UsePolarization=False,
                        DirectionCosines=False,ScatterRays=False,IgnoreLateralColor=False,DeltaFocus=0.)
                    if analysis_id!='ConfigurationMatrixSpot':values['Configuration']=1
                    for key,value in values.items():checked_setting(backend.native,settings,key,value)
                    entry['actual_settings']=scalar_settings(settings)
                    def collect(task):
                        result=unwrap(task['native'].GetResults());counts={name:int(getattr(result,name)) for name in COUNTS}
                        text=folder/(analysis_id+'-'+factory_name+'.txt')
                        exported=bool(result.GetTextFile(str(text)))
                        spot=unwrap(result.SpotData);metrics=[]
                        if spot is not None:
                            for field in range(1,int(spot.NumberOfFields)+1):
                                metrics.append(dict(field=field,native_wavelength_slot=1,rms=float(spot.GetRMSSpotSizeFor(field,1)),
                                    geo=float(spot.GetGeoSpotSizeFor(field,1)),reference_x=float(spot.GetReferenceCoordinate_X_For(field,1)),
                                    reference_y=float(spot.GetReferenceCoordinate_Y_For(field,1))))
                        row=dict(counts=counts,text_exported=exported,spot_data_available=spot is not None,metrics=metrics,
                            text_bytes=text.stat().st_size if text.is_file() else 0)
                        return dict(rows=[row],structured_data_available=True,artifacts=[])
                    task=backend._start_task('spot_factory_diagnostic',native,entry['actual_settings'],analysis=True,collector=collect,budget_seconds=60)
                    started=True;entry['task']=poll_task(call,task,record,timeout_s=70)
                    if entry['task']['state']=='succeeded':entry['result']=paged_result(call,task['task_id'],record)
                except Exception as exc:entry['error']=dict(type=type(exc).__name__,message=str(exc))
                finally:
                    if native is not None and not started:
                        owner=dict(native=native);entry['setup_close_confirmed']=backend._close_task_native(owner)
                        if owner.get('cleanup_warnings'):record['cleanup_failures']+=owner['cleanup_warnings']
                    save()
        record['after_queries']=dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),merit=call('get_merit_function'),configurations=call('get_configurations'))
    except Exception as exc:record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        if snapshot is not None:
            try:
                holder={};backend._restore_model(holder,snapshot,source,work);record['restoration']=holder.get('restoration')
                actual=dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),merit=call('get_merit_function'),configurations=call('get_configurations'))
                record['restored']={key:actual[key]==baseline[key] for key in baseline}
            except Exception as exc:record['cleanup_failures'].append(dict(step='restore',error=repr(exc)))
        try:record['disconnect']=call('disconnect')
        except Exception as exc:record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        save()
    summary=summarize(record);write_json(folder/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
    return record


if __name__=='__main__':
    if sys.argv[1]=='--evaluate':
        source=Path(sys.argv[2]);result=json.loads(source.read_text(encoding='utf-8'))
        summary=summarize(result);write_json(source.parent/'summary.json',summary)
        print(json.dumps(dict(execution_complete=summary['execution_complete'],scope=summary['scope'])))
    else:result=run(sys.argv[1])
    if not summarize(result)['execution_complete']:sys.exit(1)
