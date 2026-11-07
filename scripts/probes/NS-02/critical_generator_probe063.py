import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Use the installed generator to establish an authoritative CRS baseline."""
import json
from pathlib import Path
import shutil
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap
from zemax_mcp.analyses import scalar_settings

ROOT=PROJECT_ROOT
folder=ROOT/'verification/development/NS-02/critical063'
folder.mkdir(parents=True,exist_ok=True)
config=Config.from_env();b=Backend(Config(config.install_dir,folder/'runs'))
record={'calls':[],'analyses':[]}
def call(name,args):
    response=b.dispatch(name,args);record['calls'].append(dict(tool=name,response=response))
    assert response['ok'],response
    return response['data']
try:
    call('connect',{})
    call('new_system',{})
    call('insert_surfaces',dict(at=1))
    call('update_system_settings',dict(aperture_type='FloatByStopSize',wavelengths=[dict(wavelength_um=.55)],ray_aiming=dict(mode='Real')))
    call('update_surfaces',dict(changes=[dict(surface=1,semi_diameter=5,thickness=10,replace_solves=True)]))
    tool=b.system.Tools.OpenCriticalRaysetGenerator()
    try:
        tool.RayPattern=b.native.enum(b.native.api.Tools.RayPatternOption,'ChiefAndMarginals')
        tool.UseAllFields=False;tool.UseAllWavelengths=False
        tool.EffectiveInputDistance=1
        tool.SaveCriticalRaysFilename=str(folder/'generated.CRS')
        tool.RunAndWaitForCompletion()
        record['generator']=dict(succeeded=bool(tool.Succeeded),error=str(tool.ErrorMessage),settings=scalar_settings(tool))
    finally:record['generator_closed']=b._close_task_native({'native':tool})
    if (folder/'generated.CRS').is_file():
        call('new_system',dict(mode='NonSequential'))
        call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.55)]))
        staged=Path(str(b.system.SystemFile)).parent/'generated.CRS'
        shutil.copyfile(folder/'generated.CRS',staged);b.system.UpdateFileLists()
        for filename in [str(staged),staged.name,staged.stem]:
            a=b.system.Analyses.New_CriticalRayTracer()
            data=dict(filename=filename);record['analyses'].append(data)
            try:
                s=unwrap(a.GetSettings());s.Filename=filename
                a.ApplyAndWaitForCompletion();r=unwrap(a.GetResults())
                data.update(valid=bool(r.IsValid),type=str(r.GetType().FullName),settings=scalar_settings(s),
                            text_export=bool(r.GetTextFile(str(folder/('result'+str(len(record['analyses']))+'.txt')))),
                            dedicated_present=r.CriticalRayData is not None,messages=[str(r.GetMessageAt(i).Text)for i in range(r.NumberOfMessages)])
            finally:data['closed']=b._close_task_native({'native':a})
except Exception as exc:record['error']=str(exc)
finally:
    record['disconnect']=b.dispatch('disconnect',{})
    (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
