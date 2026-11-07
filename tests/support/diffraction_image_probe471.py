"""Probe documented EDI/PCIA CFG keys against an owned image input."""
import json,sys,time,uuid
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap

def run(folder):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
 b=Backend(Config(Config.from_env().install_dir,folder/'native'));out={'items':[]}
 def save():(folder/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
 def call(name,args=None):
  out['stage']=name;save();r=b.dispatch(name,args or {});out.setdefault('calls',[]).append(dict(tool=name,args=args,response=r));save();assert r['ok'],r;return r['data']
 target=None
 try:
  call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
  resources=call('get_system_resources',dict(kind='image_simulation_files'));target=Path(resources['directory'])/('mcp_probe_'+uuid.uuid4().hex+'.IMA');target.write_text('7\n0000000\n0090000\n0090000\n0000000\n0003000\n0000000\n0000000\n',encoding='ascii')
  groups={
   'ExtendedDiffractionImageAnalysis':[('File',target.name),('FileSize','1'),('Oversampling','1'),('ZeroPadding','1'),('OTFSampling','64'),('ShowAs','GreyScale'),('DataType','IncoherentImage'),('Wavelength','1'),('Field','1'),('UsePolarization','0'),('DiffractionLimited','0'),('ResampleImage','0'),('SkipNormalization','0')],
   'PartiallyCoherentImageAnalysis':[('File',target.name),('FileSize','1'),('Oversampling','1'),('ZeroPadding','1'),('OTFSampling','64'),('ShowAs','GreyScale'),('DataType','IncoherentImage'),('Wavelength','1'),('Field','1'),('UsePolarization','0'),('DiffractionLimited','0'),('ResampleImage','0'),('SkipNormalization','0'),('Gamma','0'),('Alpha','1'),('Fraction','1')]
  }
  for topic,settings_list in groups.items():
   item={'topic':topic};out['items'].append(item);tool=b.system.Analyses.New_Analysis_SettingsFirst(b.native.enum(b.native.api.Analysis.AnalysisIDM,topic));s=unwrap(tool.GetSettings());cfg=folder/(topic+'.CFG');item['settings_type']=str(s.GetType().FullName);item['initial_save']=bool(s.SaveTo(str(cfg)));item['unknown_key_accepted']=bool(s.ModifySettings(str(cfg),'DefinitelyNotAValidSettingMCP','123'))
   item['modify']=[dict(key=k,accepted=bool(s.ModifySettings(str(cfg),k,v)))for k,v in settings_list]
   item['load']=bool(s.LoadFrom(str(cfg)));item['settings_after_load']=dict(type=str(s.GetType().FullName),valid=bool(getattr(s,'IsValid',False)))
   item['key_values']=[dict(key=k,value=v)for k,v in settings_list]
   try:
    tool.Apply();deadline=time.monotonic()+20
    while tool.IsRunning() and time.monotonic()<deadline:time.sleep(.05)
    res=unwrap(tool.GetResults());item['result_type']=str(res.GetType().FullName);item['counts']={k:int(getattr(res,k))for k in ['NumberOfMessages','NumberOfDataGrids','NumberOfDataGridsRgb','NumberOfDataSeries','NumberOfDataScatterPoints']if hasattr(res,k)};item['messages']=[str(res.GetMessageAt(i).Text)for i in range(res.NumberOfMessages)]
    item['text_exported']=bool(res.GetTextFile(str(folder/(topic+'.txt'))));item['grids']=[]
    for n in range(int(getattr(res,'NumberOfDataGrids',0))):
     g=unwrap(res.GetDataGrid(n));item['grids'].append(dict(type=str(g.GetType().FullName),properties=[dict(name=z.Name,type=str(z.PropertyType))for z in g.GetType().GetProperties()],nx=int(g.Nx),ny=int(g.Ny),description=str(g.Description),x_label=str(g.XLabel),y_label=str(g.YLabel),value_label=str(g.ValueLabel),dx=float(g.Dx),dy=float(g.Dy),min_x=float(g.MinX),min_y=float(g.MinY),sample=[float(g.Values[0,0]),float(g.Values[int(g.Ny)//2,int(g.Nx)//2]),float(g.Values[int(g.Ny)-1,int(g.Nx)-1])]))
   except Exception as exc:item['apply_error']=dict(type=type(exc).__name__,message=str(exc))
   item['closed']=b._close_task_native({'native':tool});save()
 except Exception as exc:out['error']=dict(type=type(exc).__name__,message=str(exc));save()
 finally:
  if target:target.unlink(missing_ok=True)
  out['disconnect']=b.dispatch('disconnect',{});out['stage']='closed';save()
 print(json.dumps([{k:v for k,v in x.items()if k not in ('modify',)}for x in out['items']],ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1])
