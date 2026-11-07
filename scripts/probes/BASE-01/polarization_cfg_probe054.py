import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Discover documented polarization CFG adoption on an owned native model."""
import json
from pathlib import Path
import sys
ROOT=PROJECT_ROOT
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(calls=[],analyses=[])
    def save(): (folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,**args):
        response=backend.dispatch(name,args);record['calls'].append(dict(tool=name,arguments=args,response=response));save()
        assert response['ok'],response
        return response['data']
    try:
        call('connect');call('new_system');call('insert_surfaces',at=1)
        call('update_system_settings',aperture_value=10,wavelengths=[dict(wavelength_um=.55)])
        call('update_surfaces',changes=[dict(surface=0,thickness=1),dict(surface=1,radius='Infinity',thickness=1,material='N-BK7',semi_diameter=5,replace_solves=True)])
        for jx,jy,phase in [(1,0,0),(0,1,0),(1,1,90)]:
            item=dict(jx=jx,jy=jy,phase_y=phase,closed=False,keys=[]);record['analyses'].append(item);analysis=None
            try:
                ident=backend.native.api.Analysis.AnalysisIDM.PolarizationPupilMap
                analysis=backend.system.Analyses.New_Analysis_SettingsFirst(ident)
                settings=unwrap(analysis.GetSettings());item['runtime_type']=str(settings.GetType().FullName)
                cfg=folder/('pupil_'+str(len(record['analyses']))+'.CFG')
                item['saved']=bool(settings.SaveTo(str(cfg)))
                for key,value in dict(PPM_SAMP=1,PPM_FIELD=1,PPM_WAVE=1,PPM_SURFACE=1,PPM_JX=jx,PPM_JY=jy,PPM_PX=0,PPM_PY=phase,PPM_ADDCONFIG=0,PPM_SUBCONFIGS=0).items():
                    accepted=bool(settings.ModifySettings(str(cfg),key,str(value)));item['keys'].append(dict(key=key,value=value,accepted=accepted));save()
                    assert accepted,(key,value)
                item['loaded']=bool(settings.LoadFrom(str(cfg)));save();assert item['loaded']
                analysis.ApplyAndWaitForCompletion()
                result=unwrap(analysis.GetResults());item['valid']=bool(result.IsValid)
                item['series_count']=int(result.NumberOfDataSeries);item['grid_count']=int(result.NumberOfDataGrids)
                item['header']=[str(v)for v in result.HeaderData.Lines]
                item['messages']=[dict(code=str(result.GetMessageAt(i).ErrorCode),text=str(result.GetMessageAt(i).Text))for i in range(result.NumberOfMessages)]
                text=folder/('pupil_'+str(len(record['analyses']))+'.txt');item['text_exported']=bool(result.GetTextFile(str(text)))
                if text.is_file():item['text']=text.read_text(encoding='utf-16')
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if analysis is not None:item['closed']=backend._close_task_native(dict(native=analysis))
                save()
    finally:
        record['disconnect']=backend.dispatch('disconnect',{});save()
    return record

if __name__=='__main__':
    result=run(sys.argv[1]);print(json.dumps(dict(items=len(result['analyses']),closed=result['disconnect']['ok'])))
