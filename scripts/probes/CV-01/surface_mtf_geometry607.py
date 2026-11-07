import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Read formal paraxial pupil geometry for reference-sphere controls."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(scope='Formal LDE.GetPupil; no optical modification',calls=[])
    def save():(folder/'geometry.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['surfaces']=call('get_surfaces');record['settings']=call('get_system_settings');record['merit']=call('get_merit_function')
        from System import Double
        api=b.native.api
        aperture=b.native.enum(api.SystemData.ZemaxApertureType,'EntrancePupilDiameter')
        apodization=b.native.enum(api.Editors.LDE.PupilApodizationType,'None')
        result=b.system.LDE.GetPupil(aperture,*[Double(0)]*5,apodization,Double(0))
        record['pupil_tuple']=[str(result[0]),*[float(v)for v in result[1:6]],str(result[6]),float(result[7])]
        record['pupil_fields']=['aperture_type','aperture_value','entrance_diameter','entrance_position','exit_diameter','exit_position','apodization_type','apodization_factor']
        record['surfaces_after']=call('get_surfaces');record['settings_after']=call('get_system_settings');record['merit_after']=call('get_merit_function')
    except BaseException as exc:
        record['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(pupil_tuple=record['pupil_tuple'],disconnect_ok=record['disconnect']['ok'])))

if __name__=='__main__':run(sys.argv[1])
