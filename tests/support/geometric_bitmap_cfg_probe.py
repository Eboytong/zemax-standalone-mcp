"""Documented GBM keys against both local geometric image factories."""
import json
import shutil
import sys
import uuid
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(analyses=[],manual='verification/development/BASE-01/manual349-modifysettings.txt');source=None
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=backend.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect')
        call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        resources=call('get_system_resources',dict(kind='geometric_image_files'))
        source=Path(resources['directory'])/('G'+uuid.uuid4().hex[:8]+'.IMA')
        shutil.copyfile(ROOT/'tests/resources/imaging023/point.IMA',source)
        for index,native_name in enumerate(['GeometricImageAnalysis','GeometricBitmapImageAnalysis']):
            item=dict(native_id=native_name,phases=[]);record['analyses'].append(item);tool=None
            try:
                tool=backend.system.Analyses.New_Analysis_SettingsFirst(backend.native.enum(backend.native.api.Analysis.AnalysisIDM,native_name))
                settings=unwrap(tool.GetSettings());item['runtime_type']=str(settings.GetType().FullName)
                for phase in ['before_apply','after_apply']:
                    entry=dict(phase=phase,keys=[]);item['phases'].append(entry)
                    if phase=='after_apply':tool.ApplyAndWaitForCompletion()
                    cfg=folder/(native_name+'_'+phase+'.CFG');entry['saved']=bool(settings.SaveTo(str(cfg)))
                    output=folder/(str(index)+'_'+phase+'.bmp')
                    for key,value in dict(GBM_FIELDSIZE=1,GBM_RAYS=10,GBM_XPIX=33,GBM_YPIX=33,
                                          GBM_XSIZ=.01,GBM_YSIZ=.01,GBM_INPUT=source.name,
                                          GBM_OUTPUT=str(output),GBM_SURFACE=6,GBM_ROTATION=0).items():
                        try:entry['keys'].append(dict(key=key,value=value,accepted=bool(settings.ModifySettings(str(cfg),key,str(value)))))
                        except Exception as exc:entry['keys'].append(dict(key=key,error=dict(type=type(exc).__name__,message=str(exc))))
                    entry['loaded']=bool(settings.LoadFrom(str(cfg)));save()
                    tool.ApplyAndWaitForCompletion()
                    result=unwrap(tool.GetResults());entry['valid']=bool(result.IsValid)
                    entry['counts']={name:int(getattr(result,name)) for name in ['NumberOfDataSeries','NumberOfDataGrids','NumberOfDataGridsRgb','NumberOfDataScatterPoints','NumberOfMessages']}
                    entry['messages']=[str(result.GetMessageAt(i).Text) for i in range(result.NumberOfMessages)]
                    text=folder/(native_name+'_'+phase+'.txt');entry['text_exported']=bool(result.GetTextFile(str(text)))
                    if text.is_file():entry['text']=text.read_text(encoding='utf-16')[:3000]
                    entry['output_exists']=output.is_file()
                    if output.is_file():
                        with Image.open(output) as bitmap:entry['bitmap']=dict(size=list(bitmap.size),mode=bitmap.mode)
                    save()
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:item['closed']=backend._close_task_native(dict(native=tool))
                save()
    finally:
        record['disconnect']=backend.dispatch('disconnect',{});save()
        if source is not None:source.unlink(missing_ok=True)
    print(json.dumps(dict(analyses=record['analyses'],closed=record['disconnect']['ok']),ensure_ascii=False))


if __name__=='__main__':run(sys.argv[1])
