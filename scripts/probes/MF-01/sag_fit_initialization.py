"""Equal sag with different base-radius representations: native BFS initialization control."""
import json
import os
import sys
from pathlib import Path
import numpy as np
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.sag_fit import infer_removed_sphere
from tests.support.sag_rms_reference import fit_paraboloid

def objective(a,edge,curvature,nodes=256):
    x,w=np.polynomial.legendre.leggauss(nodes);r=(x+1)*edge/2;w=w*r;w/=w.sum()
    root=np.sqrt(1-(curvature*r)**2)
    delta=a*r*r-curvature*r*r/(1+root);delta-=np.dot(w,delta)
    derivative=r*r/(root*(1+root))
    return dict(variance=float(np.dot(w,delta*delta)),gradient=float(-2*np.dot(w,delta*derivative)))

def run(destination, sampling=False):
    folder=Path(destination).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    d=dict(cases=[],calls=[],hypothesis='Changing base radius while preserving analytic sag may change numerical BFS initialization',
           tolerances=dict(radius_mm=5e-6,sag_atol=1e-8,sag_rtol=1e-6))
    def save():(folder/'probe.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    def call(name,args=None):
        response=b.dispatch(name,args or {});d['calls'].append(dict(tool=name,arguments=args,response=response))
        if not response['ok']:raise RuntimeError(response)
        return response['data']
    try:
        call('connect');d['context']=b.context()
        code=b.native.api.Editors.MFE.MeritOperandType
        for kind in ('EvenAspheric','ZernikeFringeSag'):
            for radius in ((40.,) if sampling else (40.,80.,'Infinity')):
                call('new_system')
                a=.0126;quadratic=a-(0 if radius=='Infinity' else 1/(2*radius))
                pars={'1':quadratic}
                if kind=='ZernikeFringeSag':pars.update({'13':1,'14':5,'15':0})
                call('update_surfaces',dict(changes=[dict(surface=1,surface_type=kind,radius=radius,conic=-1,
                    parameters=pars,semi_diameter=5,thickness=20,replace_solves=True)]))
                c=dict(kind=kind,base_radius=radius,quadratic=quadratic,samples=[]);d['cases'].append(c)
                before={name:call(name) for name in ('get_surfaces','get_system_settings','get_merit_function')}
                c['actual']=before['get_surfaces']
                for y in np.linspace(0,5,17):
                    ok,sag,_=b.system.LDE.GetSag(1,0.,float(y));expected=a*y*y
                    c['samples'].append(dict(y=float(y),ok=bool(ok),sag=float(sag),reference=float(expected),error=float(abs(sag-expected))))
                assert all(s['ok'] and s['error']<=1e-8+1e-6*abs(s['reference']) for s in c['samples'])
                points=[]
                for y in (0.,1.,2.5,5.):
                    ok,sag,_=b.system.LDE.GetSag(1,0.,y)
                    args=[1,1,0.,y,0.,2.,2.,0.]
                    removed=float(b.system.MFE.GetOperandValue(b.native.enum(code,'SSAG'),*args))
                    points.append((y,float(sag),removed))
                c['native_fit']=infer_removed_sphere(points,atol=1e-10,rtol=1e-9)
                c['dsag']={}
                for data,key in ((9,'radius'),(10,'raw_vertex_offset')):
                    args=[1,0,data,1,0,2,2,0.]
                    c['dsag'][key]=float(b.system.MFE.GetOperandValue(b.native.enum(code,'DSAG'),*args))
                if sampling:
                    c['sampling_controls']=[]
                    for samp in (1,2,3,4,5):
                        args=[1,0,9,samp,0,2,2,0.]
                        fit_radius=float(b.system.MFE.GetOperandValue(b.native.enum(code,'DSAG'),*args))
                        y=5.;args=[1,1,0.,y,0.,2.,2.,0.]
                        removed=float(b.system.MFE.GetOperandValue(b.native.enum(code,'SSAG'),*args))
                        c['sampling_controls'].append(dict(sampling=samp,grid=2**(samp+4)+1,radius=fit_radius,
                            ssag_after=removed,objective=objective(a,5,1/fit_radius)))
                c['reference']=fit_paraboloid(a,5,True)
                c['radius_error']=abs(c['native_fit']['radius']-c['reference']['radius'])
                c['radius_passed']=c['radius_error']<=5e-6
                c['native_objective']=objective(a,5,c['native_fit']['curvature'])
                c['reference_objective']=objective(a,5,c['reference']['curvature'])
                c['preserved']={name:call(name)==before[name] for name in before}
                save()
    except Exception as exc:d['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        b.shutdown();p=folder/'state/close_receipt.json';d['close_receipt']=json.loads(p.read_text(encoding='utf-8')) if p.exists() else None;save()
    print(json.dumps(dict(error=d.get('error'),cases=[{k:c[k] for k in ('kind','base_radius','native_fit','radius_error','radius_passed','native_objective','sampling_controls') if k in c} for c in d['cases']],closed=(d.get('close_receipt') or {}).get('native',{})),ensure_ascii=False))
    return d
if __name__=='__main__':
    if run(sys.argv[1],sampling='--sampling' in sys.argv[2:]).get('error'):sys.exit(1)
