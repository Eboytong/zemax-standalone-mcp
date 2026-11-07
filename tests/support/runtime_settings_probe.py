"""Serial SettingsFirst discovery; no analysis calculations or settings writes."""
import argparse
import csv
import json
from pathlib import Path
import sys
import re

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap


def run(package,folder,save_cfg=False,mode=None,include_active=False,items=None):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    rows=[r for r in csv.DictReader((ROOT/'docs/development-backlog.csv').open(encoding='utf-8-sig'))
          if r['work_package']==package and (r['native_enum'] in items if items else r['execution_state'] in ({'blocked','pending','in_progress'} if include_active else {'blocked','pending'}))]
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(package=package,settings_writes=0,calculations=0,closed=False,items=[])
    def save():
        (folder/'settings.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        connected=backend.dispatch('connect',{})
        record['connect']=connected
        assert connected['ok'],connected
        selected_mode=mode or ('NonSequential' if package.startswith('NS-') else 'Sequential')
        record['system_mode']=selected_mode
        created=backend.dispatch('new_system',dict(mode=selected_mode))
        assert created['ok'],created
        for row in rows:
            item=dict(item_id=row['item_id'],native_enum=row['native_enum'],closed=False)
            record['items'].append(item);save();tool=None
            try:
                enum=backend.native.enum(backend.native.api.Analysis.AnalysisIDM,row['native_enum'])
                tool=backend.system.Analyses.New_Analysis_SettingsFirst(enum)
                if tool is None:
                    item['factory_result']='null; no owned analysis'
                    continue
                settings=unwrap(tool.GetSettings());typ=settings.GetType()
                item['runtime_settings_type']=str(typ.FullName)
                item['interfaces']=[str(t.FullName) for t in typ.GetInterfaces()]
                item['methods']=sorted(set(str(m) for m in typ.GetMethods()))
                item['inherited_interface_methods']=sorted(set(str(m) for interface in typ.GetInterfaces() for m in interface.GetMethods()))
                item['properties']=[dict(name=str(p.Name),type=str(p.PropertyType.FullName),
                    readable=bool(p.CanRead),writable=bool(p.CanWrite)) for p in typ.GetProperties()]
                item['enums']={str(p.Name):backend.native.property_enum_names(settings,str(p.Name))
                    for p in typ.GetProperties() if p.PropertyType.IsEnum}
                if save_cfg:
                    path=folder/(row['native_enum']+'.CFG')
                    saved=bool(settings.SaveTo(str(path)))
                    item['cfg_export']=dict(api='IAS_.SaveTo',returned=saved,path=str(path),exists=path.is_file())
                    if path.is_file():
                        payload=path.read_bytes()
                        item['cfg_export'].update(bytes=len(payload),contains_null_bytes=b'\0' in payload,
                            ascii_tokens=[v.decode('ascii') for v in re.findall(rb'[A-Za-z][A-Za-z0-9_]{3,}',payload)[:40]])
            except Exception as exc:
                item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:
                    owner=dict(native=tool)
                    item['closed']=backend._close_task_native(owner)
                    item['cleanup_warnings']=owner.get('cleanup_warnings',[])
                save()
            if tool is not None and not item['closed']:break
    finally:
        response=backend.dispatch('disconnect',{})
        record['disconnect']=response;record['closed']=bool(response['ok']);save()
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--save-cfg',action='store_true')
    parser.add_argument('--mode',choices=['Sequential','NonSequential'])
    parser.add_argument('--include-active',action='store_true')
    parser.add_argument('--items',nargs='+',help='Explicit native analysis names, irrespective of current state')
    args=parser.parse_args()
    result=run(args.package,args.output,args.save_cfg,args.mode,args.include_active,args.items)
    print(json.dumps(dict(items=len(result['items']),closed=result['closed'])))
