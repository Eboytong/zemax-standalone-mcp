import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Compare formal LDE.GetIndex against GRD polynomial and native GRIN display."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.speos import OwnedCopyTool


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='Native GRIN display uses a numerically approximate index evaluation; formal GetIndex at the Gradium vertex may independently preserve the GRD reference index',points=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record.setdefault('calls',[]).append(dict(tool=name,arguments=args,response=r));save()
        assert r['ok'],r
        return r['data']
    owned=None
    try:
        call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)]))
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Gradium',material='G14SFN',thickness=1,
            semi_diameter=1,parameters={1:.01,2:1},replace_solves=True)]))
        record['baseline']=call('get_surfaces');record['settings']=call('get_system_settings')
        from System import Array,Double
        copy=b.system.CopySystem();owned=OwnedCopyTool(copy)
        row=copy.LDE.GetSurfaceAt(1)
        lines=(Path.home()/'Documents/Zemax/Glasscat/PROFILE.GRD').read_text().splitlines()
        c=[float(v)for v in lines[1:13]]
        for z in [0,.25,.5,.75,1.]:
            b._cell(row,'parameter_2').DoubleValue=1+z
            indices=Array[Double]([0.,0.])
            native_return=int(copy.LDE.GetIndex(1,2,indices))
            expected=sum(a*((z+1)/5.8)**i for i,a in enumerate(c))
            record['points'].append(dict(z=z,delta_z=float(b._cell(row,'parameter_2').DoubleValue),
                reference_index=float(b._cell(row,'parameter_3').DoubleValue),native_return=native_return,
                indices=list(indices),expected=expected,error=abs(float(indices[0])-expected)))
            save()
        record['surfaces_after']=call('get_surfaces');record['settings_after']=call('get_system_settings')
    except BaseException as exc:record['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        if owned is not None:
            try:b._release_owned(owned);record['copy_closed']=True
            except Exception as exc:record['copy_close_error']=str(exc)
        record['disconnect']=b.dispatch('disconnect',{});save()


if __name__=='__main__':run(sys.argv[1])
