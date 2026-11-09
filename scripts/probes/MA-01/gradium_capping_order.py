"""Test whether native Gradium entry capping depends on parameter write order."""
from pathlib import Path
import json
import os
import sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts/probes/PO-01')]
from probe_common import adapter,poll_task,paged_result,write_json
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean


def plans(capping):
    return [dict(name='offset_then_cap',updates=[{1:.01,2:-.2,8:capping}]),
        dict(name='cap_then_offset',updates=[{1:.01,8:capping,2:-.2}]),
        dict(name='separate_cap_first',updates=[{8:capping},{2:-.2}]),
        dict(name='retouch_offset',updates=[{2:-.2,8:capping},{2:0.},{2:-.2}])]


def run(folder, bypass=False):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    calls=[];call=adapter(backend,calls)
    record=dict(item='MA-01.GradiumProfile',source_version='0.1.62 working tree',
        hypothesis='left-entry capping may depend on offset/capping update order',
        profile='G14SFN',wavelength_um=.58756,offset=-.2,capping=2,thickness=.4,
        calls=calls,cases=[],cleanup_failures=[])
    snapshot=None
    try:
        call('connect');call('new_system')
        record['context']=backend.context()
        baseline=call('get_system_settings');before=call('get_surfaces',dict(start=0,count=100))
        source,work=backend.source_path,backend.work_path
        snapshot=backend._checkpoint('gradium_capping_order')
        call('insert_surfaces',dict(at=1,count=2))
        call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.58756)],primary_wavelength=1)))
        call('update_surfaces',dict(changes=[dict(surface=1,material='',radius='Infinity',thickness=1,
            semi_diameter=1,replace_solves=True),dict(surface=3,material='',radius='Infinity',thickness=1,
            semi_diameter=1,replace_solves=True)]))
        for plan in ([plans(2)[1]] if bypass else plans(2)):
            call('update_surfaces',dict(changes=[dict(surface=2,surface_type='Gradium',material='G14SFN',
                thickness=.4,radius='Infinity',semi_diameter=1,parameters={1:.01,2:1.,8:0},replace_solves=True)]))
            entry=dict(plan=plan,stages=[],traces=[]);record['cases'].append(entry)
            for parameters in plan['updates']:
                call('update_surfaces',dict(changes=[dict(surface=2,parameters=parameters,replace_solves=True)]))
                entry['stages'].append(dict(parameters_in_write_order=list(parameters.items()),
                    actual=call('get_surfaces',dict(start=2,count=1,parameter_count=8))))
            entry['update_status']=str(backend.system.UpdateStatus())
            from System import Array,Double
            buffer=Array[Double]([0.])
            entry['get_index_return']=int(backend.system.LDE.GetIndex(2,1,buffer))
            entry['vertex_index']=clean(float(buffer[0]))
            entry['actual_final']=call('get_surfaces',dict(start=2,count=1,parameter_count=8))
            traces=[(1,2,0.),(1,3,0.)]
            if bypass:traces += [(2,3,0.),(2,3,.21)]
            for start,target,z in traces:
                request=dict(input_mode='Direct',start_surface=start,target_surface=target,
                    rays=[dict(x=0.,y=0.,z=z,l=0.,m=0.,n=1.,wavelength=1)])
                task=poll_task(call,call('run_batch_ray_trace',dict(request=request)),record)
                if task['state']!='succeeded':raise RuntimeError(dict(task=task))
                result=paged_result(call,task['task_id'],record)
                entry['traces'].append(dict(start_surface=start,target_surface=target,start_z=z,task=task,result=result))
    except Exception as exc:
        record['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        if snapshot is not None:
            try:
                holder={};backend._restore_model(holder,snapshot,source,work)
                record['restoration']=holder.get('restoration')
                record['settings_restored']=call('get_system_settings')==baseline
                record['surfaces_restored']=call('get_surfaces',dict(start=0,count=100))==before
            except Exception as exc:record['cleanup_failures'].append(dict(step='restore',error=repr(exc)))
        try:record['disconnect']=call('disconnect')
        except Exception as exc:record['cleanup_failures'].append(dict(step='disconnect',error=repr(exc)))
        write_json(folder/'probe.json',record)
    print(json.dumps(dict(error=record.get('error'),cases=[dict(plan=e['plan']['name'],
        vertex_index=e.get('vertex_index'),rays=[dict(start=t['start_surface'],target=t['target_surface'],start_z=t['start_z'],rows=t['result'].get('rows'))
            for t in e['traces']])for e in record['cases']],settings_restored=record.get('settings_restored'),
        surfaces_restored=record.get('surfaces_restored'),cleanup_failures=record['cleanup_failures']),ensure_ascii=False))
    return record

if __name__=='__main__':
    result=run(sys.argv[1],bypass='--bypass' in sys.argv[2:])
    if result.get('error') or result['cleanup_failures']:sys.exit(1)
