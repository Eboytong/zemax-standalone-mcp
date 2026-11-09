"""Bounded installed image-analysis contracts and documented CFG adoption probe."""
import json
import os
import sys
import time
from pathlib import Path

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap, clean, dotnet_array
from zemax_mcp.image_viewers import ANALYSIS_IDS, MODIFY_SETTINGS, PARSERS, parse_report

VARIANTS={
 'extended_diffraction_image':dict(EXD_FILESIZE=.1,EXD_DISPLAYSIZE=.2,EXD_FIELD=2,EXD_WAVE=1),
 'partially_coherent_image':dict(PCI_FILESIZE=.2,PCI_FIELD=2,PCI_WAVE=1,PCI_RESAMPLE=1,PCI_RSNX=9,PCI_RSNY=7,PCI_RSDCX=0,PCI_RSDCY=0,PCI_RSDLX=.02,PCI_RSDLY=.03),
 'geometric_bitmap_image':dict(GBM_FIELDSIZE=1,GBM_RAYS=1,GBM_XPIX=17,GBM_YPIX=11,
                               GBM_XSIZ=.02,GBM_YSIZ=.03,GBM_SURFACE=0,GBM_ROTATION=0),
}


def read_completed_result(task):
    result=task.get('result')
    if result is None and task.get('result_path'):
        result=json.loads(Path(task['result_path']).read_text(encoding='utf-8'))
    if not isinstance(result,dict):
        raise ValueError('completed task has no result object or readable result artifact')
    return result


def run(output, only=None, finite=False, source_model=None):
 folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
 os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
 backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
 record=dict(purpose='runtime settings, default outlets and documented CFG readback',
             source_root=str(ROOT),calls=[],analyses=[],error=None)
 def save():
  (folder/'probe.json').write_text(json.dumps(clean(record),ensure_ascii=False,indent=2),encoding='utf-8')
 def call(name,args=None):
  response=backend.dispatch(name,args or {})
  record['calls'].append(dict(tool=name,arguments=args,response=response));save()
  if not response['ok']:raise RuntimeError(response)
  return response['data']
 def collect(task):
  result=unwrap(task['native'].GetResults())
  data=dict(result_type=str(result.GetType().FullName),valid=bool(result.IsValid),counts={})
  for prop in result.GetType().GetProperties():
   if str(prop.Name).startswith(('NumberOf','Num')) and prop.GetIndexParameters().Length==0:
    try:data['counts'][str(prop.Name)]=int(prop.GetValue(result,None))
    except Exception as exc:data['counts'][str(prop.Name)]=dict(error=str(exc))
  data['grids']=[]
  for i in range(int(result.NumberOfDataGrids)):
   g=result.GetDataGrid(i);values=dotnet_array(g.Values)
   data['grids'].append(dict(nx=int(g.Nx),ny=int(g.Ny),dx=float(g.Dx),dy=float(g.Dy),min_x=float(g.MinX),min_y=float(g.MinY),
      value_shape=[len(values),len(values[0])],values=values))
  data['series']=[]
  for i in range(int(result.NumberOfDataSeries)):
   series=unwrap(result.GetDataSeries(i))
   data['series'].append(dict(description=str(series.Description),x_label=str(series.XLabel),y_label=str(series.YLabel),
      labels=[str(v) for v in series.SeriesLabels] if series.SeriesLabels is not None else [],
      x=dotnet_array(series.XData.Data),y=dotnet_array(series.YData.Data)))
  data['messages']=[dict(code=str(result.GetMessageAt(i).ErrorCode),text=str(result.GetMessageAt(i).Text))
                    for i in range(int(result.NumberOfMessages))]
  path=folder/(task['task_id']+'.txt')
  data['text_export']=bool(result.GetTextFile(str(path)))
  data['text_path']=str(path)
  if data['text_export']:
   text=path.read_text(encoding='utf-16')
   data['text_header']=text.splitlines()[:20]
   if task['settings']['kind'] in PARSERS:
    try:
     parsed=parse_report(task['settings']['kind'],text)
     grid=parsed.pop('grid',[])
     if grid:
      values=[v for row in grid for v in row]
      parsed['grid_summary']=dict(rows=len(grid),columns=len(grid[0]),minimum=min(values),maximum=max(values))
     data['parsed']=parsed
    except Exception as exc:data['parse_error']=repr(exc)
  return data
 try:
  call('connect')
  call('open_lens',dict(path=str(source_model or Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
  if finite:
   call('new_system')
   call('update_system_settings',dict(field_type='ObjectHeight',aperture_value=2,
        fields=[dict(x=0,y=0)],wavelengths=[dict(wavelength_um=.55)]))
   call('update_surfaces',dict(changes=[dict(surface=0,thickness=200,replace_solves=True),
        dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,
             semi_diameter=1,is_stop=True,replace_solves=True)]))
   record['controlled_input']='finite conjugate; 200mm object, f=100mm ideal surface, 200mm image'
  record['before_settings']=call('get_system_settings')
  structure_command='get_nsc_objects' if record['before_settings']['mode']=='NonSequential' else 'get_surfaces'
  record['structure_command']=structure_command
  record['before_surfaces']=call(structure_command)
  for kind,(native_name,_) in ANALYSIS_IDS.items():
   if only and kind!=only:continue
   for changed in ([False,True] if kind in VARIANTS else [False]):
    entry=dict(kind=kind,variant='documented_cfg' if changed else 'default')
    record['analyses'].append(entry);tool=None;started=False
    try:
     code=getattr(backend.native.api.Analysis.AnalysisIDM,native_name)
     tool=backend.system.Analyses.New_Analysis_SettingsFirst(code)
     settings=unwrap(tool.GetSettings())
     entry['settings_type']=str(settings.GetType().FullName)
     entry['members']=[str(p.Name) for p in settings.GetType().GetProperties()]
     entry['methods']=sorted(set(str(m.Name) for m in settings.GetType().GetMethods()))
     if changed:
      cfg=folder/(kind+'.CFG');entry['cfg_path']=str(cfg)
      entry['save_return']=bool(settings.SaveTo(str(cfg)))
      entry['cfg_operations']=[]
      for key,value in VARIANTS[kind].items():
       assert key in MODIFY_SETTINGS[kind],key
       accepted=bool(settings.ModifySettings(str(cfg),key,str(value)))
       entry['cfg_operations'].append(dict(key=key,value=value,accepted=accepted))
       if not accepted:raise RuntimeError('documented key rejected: '+key)
      entry['load_return']=bool(settings.LoadFrom(str(cfg)))
      if not entry['load_return']:raise RuntimeError('CFG LoadFrom rejected')
     task=backend._start_task('analysis',tool,dict(kind=kind,variant=entry['variant']),
                              analysis=True,collector=collect,budget_seconds=60)
     started=True;entry['task_id']=task['task_id']
     deadline=time.monotonic()+75
     while backend.tasks[task['task_id']]['state'] not in ('succeeded','failed','cancelled'):
      if time.monotonic()>deadline:raise TimeoutError('analysis did not reach terminal state')
      backend.tick();time.sleep(.03)
     entry['task']=backend._task_view(backend.tasks[task['task_id']])
     entry['result']=read_completed_result(backend.tasks[task['task_id']])
    except Exception as exc:entry['error']=repr(exc)
    finally:
     if tool is not None and not started:
      entry['closed_after_setup_error']=bool(backend._close_task_native(dict(native=tool)))
     save()
    if backend.active:raise RuntimeError('active analysis remains; stopping serial queue')
  record['settings_preserved']=call('get_system_settings')==record['before_settings']
  record['surfaces_preserved']=call(structure_command)==record['before_surfaces']
 except Exception as exc:record['error']=repr(exc)
 finally:
  backend.shutdown()
  receipt=folder/'state/close_receipt.json'
  record['close_receipt']=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
  save()
 print(json.dumps(dict(output=str(folder),analyses=[dict(kind=x['kind'],variant=x['variant'],
       settings=x.get('settings_type'),error=x.get('error'),state=x.get('task',{}).get('state')) for x in record['analyses']],
       error=record['error'],closed=record.get('close_receipt',{}).get('native',{}).get('closed')),ensure_ascii=False))


if __name__=='__main__':run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None,'--finite' in sys.argv[3:])
