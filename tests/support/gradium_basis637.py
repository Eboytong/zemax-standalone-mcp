"""Isolate the documented Gradium polynomial using task-owned monomial resources."""
import json,sys,uuid
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output,maximum_z=1.,amplitude=.1):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(hypothesis='A task-owned monomial basis separates native profile polynomial evaluation from the supplied high-order stock coefficients',cases=[],calls=[])
    resource=None
    def save():(folder/'basis.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});record['calls'].append(dict(tool=name,arguments=args,response=r));save();assert r['ok'],r;return r['data']
    try:
        call('connect');call('new_system');call('insert_surfaces',dict(at=1))
        call('update_system_settings',dict(wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)]))
        blocks=[]
        for degree in range(12):
            coefficients=[0.]*12;coefficients[0]=1.5
            if degree:coefficients[degree]=amplitude
            blocks += [f'MCPG{degree:02d} GSF {maximum_z:.17g}']+[format(c,'.17g')for c in coefficients]
        content='\n'.join(blocks)+'\n'
        (folder/'monomials.GRD').write_text(content,encoding='ascii')
        resource=Path(str(b.native.application.ZemaxDataDir))/'Glasscat'/('MCP_GRADIUM637_'+uuid.uuid4().hex[:10]+'.GRD')
        record['resource']=str(resource);record['maximum_z']=maximum_z;record['amplitude']=amplitude
        record['input_formula']='n_ref=1.5+amplitude*(z/zmax)^degree,degree1..11;degree0constant1.5'
        resource.write_text(content,encoding='ascii');save()
        call('update_system_settings',dict(files=dict(gradium_profile=resource.name)))
        record['actual_settings']=call('get_system_settings')
        from System import Array,Double
        for degree in range(12):
            name=f'MCPG{degree:02d}'
            call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Gradium',material=name,radius=0,thickness=.001,
                semi_diameter=.1,parameters={1:.0001,2:0,8:3},replace_solves=True)]))
            case=dict(degree=degree,material=name,points=[]);record['cases'].append(case);save()
            for fraction in [.1,.25,.5,.75,.9]:
                coordinate=fraction*maximum_z
                call('update_surfaces',dict(changes=[dict(surface=1,parameters={2:coordinate},replace_solves=True)]))
                row=b.system.LDE.GetSurfaceAt(1);indices=Array[Double]([0.,0.]);native_return=int(b.system.LDE.GetIndex(1,2,indices))
                expected=1.5+(amplitude*fraction**degree if degree else 0.)
                case['points'].append(dict(coordinate=coordinate,normalized_coordinate=fraction,actual_offset=float(b._cell(row,'parameter_2').DoubleValue),
                    reference_display=float(b._cell(row,'parameter_3').DoubleValue),native_return=native_return,indices=list(indices),
                    expected=expected,error=float(indices[0])-expected))
                save()
            case['surfaces']=call('get_surfaces');save()
    except BaseException as exc:record['error']=dict(type=type(exc).__name__,message=str(exc));save();raise
    finally:
        record['disconnect']=b.dispatch('disconnect',{});save()
        if resource is not None and resource.is_file():resource.unlink();record['owned_resource_removed']=True;save()
    print(json.dumps([dict(degree=c['degree'],maximum_error=max(abs(p['error'])for p in c['points']))for c in record['cases']]))

if __name__=='__main__':run(sys.argv[1],float(sys.argv[2])if len(sys.argv)>2 else 1.,float(sys.argv[3])if len(sys.argv)>3 else .1)
