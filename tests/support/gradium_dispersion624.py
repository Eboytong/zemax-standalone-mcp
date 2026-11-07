"""Separate GRD profile evaluation from the shared native SGRIN dispersion path."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output,profile='G14SFN'):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(profile=profile,hypothesis='GRADIUM GetIndex discrepancy originates after exact RefN profile evaluation; compare constant Gradient5 with/without the same GSF family',cases=[],calls=[])
    def save():(folder/'dispersion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)]))
        from System import Array,Double
        lines=(Path.home()/'Documents/Zemax/Glasscat/PROFILE.GRD').read_text().splitlines()
        start=next(i for i,line in enumerate(lines)if line.split()and line.split()[0]==profile)
        coefficients=[float(v)for v in lines[start+1:start+13]]
        for z in [0.,.25,.5,.75,1.]:
            expected=sum(c*((z+1)/5.8)**i for i,c in enumerate(coefficients))
            case=dict(z=z,expected=expected,variants=[]);record['cases'].append(case);save()
            for surface,material in [('Gradium',profile),('Gradient5','GSF'),('Gradient5','')]:
                parameters={1:.01,2:1+z}if surface=='Gradium'else{1:.01,2:expected,**{i:0. for i in range(3,9)}}
                call('update_surfaces',dict(changes=[dict(surface=1,surface_type=surface,material=material,radius=0,thickness=1,semi_diameter=1,parameters=parameters,replace_solves=True)]))
                before=call('get_surfaces');settings=call('get_system_settings');merit=call('get_merit_function')
                indices=Array[Double]([0.,0.]);native_return=int(b.system.LDE.GetIndex(1,2,indices))
                item=dict(surface_type=surface,material=material,native_return=native_return,indices=list(indices),reference_wave_error=float(indices[0])-expected)
                case['variants'].append(item);save()
                item['preserved']=call('get_surfaces')==before and call('get_system_settings')==settings and call('get_merit_function')==merit
                assert item['preserved'];save()
    except BaseException as exc:record['error']=dict(type=type(exc).__name__,message=str(exc));save();raise
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps([dict(z=c['z'],variants=[dict(surface=v['surface_type'],material=v['material'],error=v['reference_wave_error'])for v in c['variants']])for c in record['cases']]))

if __name__=='__main__':run(sys.argv[1],sys.argv[2]if len(sys.argv)>2 else'G14SFN')
