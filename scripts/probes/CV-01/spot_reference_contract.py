"""Native StandardSpot composition contract for matrix fallback feasibility."""
from pathlib import Path
import os
import sys
import json

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter,poll_task,paged_result,write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.analyses import scalar_settings
from zemax_mcp.detectors import checked_setting
from zemax_mcp.analysis_models import RunAnalysis

COUNTS=['NumberOfDataSeries','NumberOfDataSeriesRgb','NumberOfDataGrids','NumberOfDataGridsRgb',
    'NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb','NumberOfRayData','NumberOfMessages']
GETTERS=['Get_X_For','Get_Y_For','Get_Z_For','Get_L_For','Get_M_For','Get_N_For',
    'GetDetector_X_For','GetDetector_Y_For','GetDetector_Z_For','GetGeoSpotSizeFor','GetRMSSpotSizeFor',
    'GetRMSSpot_X_For','GetRMSSpot_Y_For','GetReferenceCoordinate_X_For','GetReferenceCoordinate_Y_For']


def cases():
    result=[dict(name=ref+'-wave'+str(wave),reference=ref,wavelength=wave) for ref in ('Centroid','ChiefRay','Middle','Vertex') for wave in (0,1,2)]
    result += [dict(name='ignore-color',reference='Centroid',wavelength=0,ignore_lateral_color=True),
        dict(name='ignore-color-wave1',reference='Centroid',wavelength=1,ignore_lateral_color=True),
        dict(name='direction-cosines',reference='Centroid',wavelength=0,direction_cosines=True),
        dict(name='configuration2',reference='Centroid',wavelength=0,configuration=2),
        dict(name='dithered',reference='Centroid',wavelength=0,pattern='Dithered'),
        dict(name='polarized',reference='Centroid',wavelength=0,use_polarization=True)]
    return result


def configuration_cases():
    return [dict(name=f'active{active}-selected{selected}',reference='Centroid',wavelength=0,
        active_configuration=active,configuration=selected) for active in (1,2) for selected in (1,2)]


def run(folder,configuration_only=False):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    calls=[];call=adapter(backend,calls)
    record=dict(items=['CV-01.MatrixSpot','CV-01.ConfigurationMatrixSpot'],source_version='0.1.62 working tree',
        hypothesis='StandardSpot slots and references may supply complete matrix facets',calls=calls,cases=[],cleanup_failures=[])
    snapshot=None
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['context']=backend.context();source,work=backend.source_path,backend.work_path
        baseline=dict(settings=call('get_system_settings'),surfaces=call('get_surfaces'),merit=call('get_merit_function'),configurations=call('get_configurations'))
        snapshot=backend._checkpoint('spot_reference_contract')
        call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.48,weight=1),dict(wavelength_um=.65,weight=3)],primary_wavelength=1)))
        thickness=next(s for s in baseline['surfaces']['surfaces'] if s['surface']==6)['cells']['thickness']['value']
        call('update_configurations',dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={1:6},
            cells=[dict(configuration=1,value=thickness),dict(configuration=2,value=thickness+.2)])]))
        record['controlled_settings']=call('get_system_settings');record['controlled_configurations']=call('get_configurations')
        for case in (configuration_cases() if configuration_only else cases()):
            entry=dict(case=case);record['cases'].append(entry);native=None;started=False
            try:
                if 'active_configuration' in case:
                    call('set_configuration',dict(configuration=case['active_configuration']))
                    entry['model_settings_before']=call('get_system_settings')
                    entry['image_distance_before']=call('get_surfaces',dict(start=6,count=1))
                request=RunAnalysis(request=dict(kind='matrix_spot',reference=case['reference'],pattern=case.get('pattern','Hexapolar'),
                    ignore_lateral_color=case.get('ignore_lateral_color',False),direction_cosines=case.get('direction_cosines',False),
                    use_polarization=case.get('use_polarization',False))).request
                entry['typed_matrix_settings']=request.model_dump()
                native=backend.system.Analyses.New_Analysis_SettingsFirst(backend.native.enum(backend.native.api.Analysis.AnalysisIDM,'StandardSpot'))
                settings=unwrap(native.GetSettings());settings.Field.SetFieldNumber(3);settings.Wavelength.SetWavelengthNumber(case['wavelength']);settings.Surface.UseImageSurface()
                values=dict(Pattern=request.pattern,ReferTo=request.reference,RayDensity=request.ray_density,UsePolarization=request.use_polarization,
                    DirectionCosines=request.direction_cosines,ScatterRays=False,IgnoreLateralColor=request.ignore_lateral_color,
                    DeltaFocus=0.,Configuration=case.get('configuration',1))
                for key,value in values.items():checked_setting(backend.native,settings,key,value)
                entry['actual_settings']=scalar_settings(settings)
                def collect(task):
                    result=unwrap(task['native'].GetResults());counts={key:int(getattr(result,key)) for key in COUNTS}
                    path=folder/(case['name']+'.txt');text_ok=bool(result.GetTextFile(str(path)))
                    spot=unwrap(result.SpotData);slots=[]
                    if spot is not None:
                        for wavelength in range(1,int(spot.NumberOfWavelengths)+1):
                            slots.append(dict(field=3,slot=wavelength,values={key:float(getattr(spot,key)(3,wavelength)) for key in GETTERS}))
                    return dict(rows=[dict(counts=counts,text_exported=text_ok,spot_available=spot is not None,
                        number_of_fields=int(spot.NumberOfFields) if spot is not None else None,
                        number_of_wavelengths=int(spot.NumberOfWavelengths) if spot is not None else None,slots=slots)],
                        structured_data_available=True,artifacts=[])
                task=backend._start_task('spot_reference_diagnostic',native,entry['actual_settings'],analysis=True,collector=collect,budget_seconds=60)
                started=True;entry['task']=poll_task(call,task,record,timeout_s=70)
                if entry['task']['state']=='succeeded':entry['result']=paged_result(call,task['task_id'],record)
            except Exception as exc:entry['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if native is not None and not started:
                    owner=dict(native=native);entry['setup_close']=backend._close_task_native(owner)
                    if owner.get('cleanup_warnings'):record['cleanup_failures']+=owner['cleanup_warnings']
                write_json(folder/'probe.json',record)
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
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(error=record.get('error'),cases=[dict(name=e['case']['name'],state=e.get('task',{}).get('state'),error=e.get('error'),
        result=e.get('result',{}).get('rows')) for e in record['cases']],restored=record.get('restored'),cleanup=record['cleanup_failures']),ensure_ascii=False))
    return record


if __name__=='__main__':
    record=run(sys.argv[1],configuration_only='--configuration-only' in sys.argv[2:])
    if record.get('error') or record['cleanup_failures'] or any(e.get('error') or e.get('task',{}).get('state')!='succeeded' for e in record['cases']):sys.exit(1)
