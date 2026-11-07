"""Probe formal LightSourceAnalysis settings keys on finite-conjugate baseline."""
import json,sys,time
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(folder):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
 b=Backend(Config(Config.from_env().install_dir,folder/'native'));out={'item_id':'CV-02.LightSourceAnalysis','source_files':[],'keys':[]}
 def save():(folder/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
 def call(name,args=None):
  out['stage']=name;save();r=b.dispatch(name,args or {});out.setdefault('calls',[]).append(dict(tool=name,args=args,response=r));save();assert r['ok'],r;return r['data']
 try:
  call('connect');call('new_system');call('insert_surfaces',dict(at=1));call('update_system_settings',dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)]));call('update_surfaces',dict(changes=[dict(surface=0,thickness=100),dict(surface=1,radius='Infinity',thickness=50,semi_diameter=10,replace_solves=True)]))
  source=Path(Config.from_env().install_dir)/'ZemaxData/Objects/Sources/Source Files/sample.SDF';out['source_file']=str(source);out['source_exists']=source.exists()
  b._require_sequential(focused=True)
  native=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,'LightSourceAnalysis'));settings=native.GetSettings();cfg=folder/'source.CFG';out['settings_type']=str(settings.GetType().FullName);out['save_to']=bool(settings.SaveTo(str(cfg)));out['properties']=[dict(name=p.Name,type=str(p.PropertyType),writable=bool(p.CanWrite))for p in settings.GetType().GetProperties()]
  keys=['Input','InputFile','File','SourceFile','Surface','Wavelength','ShowAs','Field','XPixels','YPixels','XPixelSize','YPixelSize','ContrastEnhancement','Reference','Rotation','Units','Fraction','UsePolarization','DeleteVignetted','SuppressFrame','RemoveVignettingFactors','ApplyFixedApertures']
  for key in keys:
   try:out['keys'].append(dict(key=key,accepted=bool(settings.ModifySettings(str(cfg),key,str(source if key in ['Input','InputFile','File','SourceFile'] else '1')))))
   except Exception as exc:out['keys'].append(dict(key=key,error=str(exc)))
  save();out['load_from']=bool(settings.LoadFrom(str(cfg)));out['is_valid']=bool(settings.IsValid);save()
  try:
   native.Apply();deadline=time.monotonic()+20
   while native.IsRunning() and time.monotonic()<deadline:time.sleep(.05)
   res=native.GetResults();typ=res.GetType();out['result']={'running':bool(native.IsRunning()),'type':str(typ.FullName),'properties':[dict(name=p.Name,type=str(p.PropertyType))for p in typ.GetProperties()],'methods':[str(m)for m in typ.GetMethods()if m.IsPublic and not m.IsSpecialName],'counts':{k:int(getattr(res,k))for k in ['NumberOfMessages','NumberOfDataGrids','NumberOfDataSeries','NumberOfDataScatterPoints'] if hasattr(res,k)},'messages':[str(res.GetMessageAt(i).Text)for i in range(res.NumberOfMessages)],'text':bool(res.GetTextFile(str(folder/'result.txt')))}
  except Exception as exc:out['apply_error']=dict(type=type(exc).__name__,message=str(exc))
  finally:out['closed']=b._close_task_native({'native':native})
 except Exception as exc:out['error']=dict(type=type(exc).__name__,message=str(exc))
 finally:out['disconnect']=b.dispatch('disconnect',{});out['closed_session']=True;save()
 print(json.dumps({k:out.get(k)for k in ['source_exists','settings_type','keys','result','apply_error','error','closed']},ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1])
