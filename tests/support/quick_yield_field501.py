"""Resolve native QuickYield user-field indexing against explicit RMS fields."""
import json
import sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap, dotnet_array
from zemax_mcp.imaging import new_analysis
from zemax_mcp.analyses import scalar_settings


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));out={'fields':[]}
    def call(name,args=None):
        r=b.dispatch(name,args or {});out.setdefault('calls',[]).append(dict(tool=name,args=args,response=r))
        assert r['ok'],r
        return r['data']
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        call('update_tolerances',dict(mode='replace',operands=[dict(type='TTHI',param1=1,param2=0,minimum=0,maximum=0)]))
        out['system']=call('get_system_settings')
        for field in [0,1,2,3]:
            tool=new_analysis(b,'QuickYield');record=dict(native_field=field);out['fields'].append(record)
            try:
                s=unwrap(tool.GetSettings());f=unwrap(s.QYField)
                if 'field_interface' not in out:
                    typ=f.GetType();out['field_interface']=dict(type=str(typ.FullName),properties=[str(p) for p in typ.GetProperties()],methods=[str(m) for m in typ.GetMethods() if m.IsPublic and not m.IsSpecialName])
                s.Configuration=1;s.NumMonteCarlo=1000;s.PupilSampling=10
                b.native.set_enum(s,'Precision','VeryHigh');b.native.set_enum(s,'CompensatorStrategy','Ignore')
                s.Wavelength.SetWavelengthNumber(1)
                response=f.SetFieldUser(field)
                record['selection_message']=None if response is None else str(response)
                record['readback']=int(f.GetFieldUser());record['settings']=scalar_settings(s)
                tool.ApplyAndWaitForCompletion();r=unwrap(tool.GetResults())
                record['valid']=bool(r.IsValid);record['series']=[]
                for i in range(r.NumberOfDataSeries):
                    curve=r.GetDataSeries(i)
                    record['series'].append(dict(x=dotnet_array(curve.XData.Data),y=dotnet_array(curve.YData.Data)))
                record['text']=bool(r.GetTextFile(str(folder/f'field{field}.txt')))
            except Exception as exc:record['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:record['close']=b._close_task_native({'native':tool})
    finally:
        out['disconnect']=b.dispatch('disconnect',{})
        (folder/'probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(fields=[dict(native=r['native_field'],readback=r.get('readback'),value=r.get('series',[{}])[0].get('x',[None])[0] if r.get('series') else None,error=r.get('error'),close=r['close']) for r in out['fields']],disconnect=out['disconnect']['ok'])))


if __name__=='__main__':run(sys.argv[1])
