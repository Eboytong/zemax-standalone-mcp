"""Independent exit-plane and reference-sphere transport from retained rays."""
import json
from pathlib import Path
import numpy as np
import matplotlib.tri as tri
from diffraction_reference import pupil_autocorrelation
from surface_mtf_angular536 import interpolate

ROOT=Path(__file__).resolve().parents[2]

def run():
    geometry=json.loads((ROOT/'verification/development/CV-01/probe608-pupil-geometry/geometry.json').read_text(encoding='utf-8'))
    exit_z=geometry['pupil_tuple'][5]
    source=ROOT/'outputs/runs/surface_mtf512_primary_89cacce054'
    record=json.loads((source/'autocorrelation.json').read_text(encoding='utf-8'))[0]
    entries=json.loads((source/'field3-rays.json').read_text(encoding='utf-8'))
    rays=[e['ray']for e in entries if not e['ray']['error_code']and not e['ray']['vignette_code']]
    chief=next(r for r in rays if r['input']['px']==r['input']['py']==0)
    positions=np.array([r['position']for r in rays]);directions=np.array([r['direction']for r in rays]);phase=np.array([r['opd']for r in rays])
    cp=np.array(chief['position']);cd=np.array(chief['direction']);ey=np.cross(cd,[1.,0.,0.]);ey/=np.linalg.norm(ey)
    origin=cp+(exit_z-cp[2])/cd[2]*cd;radius=float(np.linalg.norm(cp-origin))
    plane=positions+(exit_z-positions[:,2])[:,None]/directions[:,2,None]*directions
    t=((origin-positions)@cd)/(directions@cd)
    normal=positions+t[:,None]*directions
    p=positions-cp;dot=np.sum(p*directions,axis=1)
    distance=-dot-np.sqrt(dot*dot+radius*radius-np.sum(p*p,axis=1))
    sphere=positions+distance[:,None]*directions
    wave=.00055;g=record['result']['grids'][0];results=[]
    for name,points,basis_y in [('exit_z_plane',plane,np.array([0.,1.,0.])),('chief_normal_plane',normal,ey),('reference_sphere',sphere,ey)]:
        uv=np.column_stack((points[:,0]-origin[0],(points-origin)@basis_y))
        triangulation=tri.Triangulation(uv[:,0],uv[:,1]);phase_interp=tri.LinearTriInterpolator(triangulation,phase)
        for n in [256,512]:
            axes=[np.linspace(uv[:,i].min(),uv[:,i].max(),n)for i in [0,1]];xx,yy=np.meshgrid(*axes)
            sampled=phase_interp(xx,yy);pupil=np.exp(2j*np.pi*sampled).filled(0);acf=pupil_autocorrelation(pupil)
            for rname,rvalue in [('chief_radius',radius),('axial_distance',abs(exit_z))]:
                freq=[(np.arange(2*n)-n)*(a[1]-a[0])/(wave*rvalue)for a in axes]
                projections=[('none',1.)]if name=='exit_z_plane'else[('none',1.),('chief_normal_to_image',1/abs(cd[2]))]
                for projection,scale in projections:
                    comparisons=[]
                    for old in record['comparisons']['native_cutoff']['points']:
                        ref=interpolate(*freq,acf,old['fx'],old['fy']*scale)
                        comparisons.append(dict(fx=old['fx'],fy=old['fy'],native=old['native'],reference=ref,error=abs(ref-old['native'])))
                    results.append(dict(mapping=name,size=n,radius_definition=rname,projection=projection,
                        bounds=[[float(a[0]),float(a[-1])]for a in axes],points=comparisons,maximum_error=max(p['error']for p in comparisons)))
    data=dict(hypothesis='Actual exit-pupil intersections and reference-sphere projection supply the missing nonlinear pupil mapping',
        native_execution=False,source=str(source.relative_to(ROOT)),formal_pupil_geometry='verification/development/CV-01/probe608-pupil-geometry/geometry.json',
        chief_position=cp.tolist(),chief_direction=cd.tolist(),exit_z=exit_z,chief_exit_point=origin.tolist(),radius=radius,
        reference='Transport independent image intercept/direction rays to paraxial exit plane, chief-normal plane, reference sphere; interpolate OPD before uniform complex-pupil autocorrelation',
        limitations='Linear triangular interpolation/convex boundary; no amplitude Jacobian transport',absolute_tolerance=.005,results=results)
    (ROOT/'verification/development/CV-01/offline609-pupil-transport.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(geometry={k:data[k]for k in ['exit_z','radius','chief_exit_point']},comparisons=[{k:r[k]for k in ['mapping','size','radius_definition','projection','maximum_error']}for r in results]),indent=2))

if __name__=='__main__':run()
