import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Identify coherent support geometry separately from independently traced phase."""
import json
from pathlib import Path
import numpy as np

ROOT=PROJECT_ROOT

def run():
    folder=next((ROOT/'outputs/runs').glob('surface_mtf605_coherent_pupil_*'))
    source=ROOT/'.local/fixtures/surface_mtf512_primary_89cacce054'
    record=json.loads((folder/'coherent-pupil.json').read_text(encoding='utf-8'))['records'][1]
    real=record['modes']['Real_Coherent']['grids'][0];imag=record['modes']['Imaginary_Coherent']['grids'][0]
    coherent=np.asarray(real['values'])+1j*np.asarray(imag['values']);mask=abs(coherent)>1e-10
    cy,cx=real['zero_frequency_index']['y'],real['zero_frequency_index']['x']
    y,x=np.indices(mask.shape);x=x-cx;y=y-cy
    a=float(max(abs(x[mask])));inside_x=abs(x)<a
    ratios=np.divide(abs(y),np.sqrt(np.maximum(1-(x/a)**2,0)),out=np.full(x.shape,np.nan),where=inside_x)
    low=float(np.max(ratios[mask&inside_x]));high=float(np.min(ratios[~mask&inside_x]))
    b=(low+high)/2
    candidate=(x/a)**2+(y/b)**2<=1
    entries=json.loads((source/'field3-rays.json').read_text(encoding='utf-8'))
    phase=np.zeros((256,256));valid=np.zeros((256,256),bool)
    for e in entries:
        r=e['ray']
        if not r['error_code']and not r['vignette_code']and r.get('opd')is not None:
            phase[e['iy'],e['ix']]=r['opd'];valid[e['iy'],e['ix']]=True
    results=[]
    for name,sy in [('entrance_clipped',127.),('ellipse_normalized',b)]:
        ux=x/a;uy=y/sy;px=128+127*ux;py=128+127*uy
        ix=np.clip(np.floor(px).astype(int),0,254);iy=np.clip(np.floor(py).astype(int),0,254)
        dx=px-ix;dy=py-iy
        interpolated=(1-dy)*((1-dx)*phase[iy,ix]+dx*phase[iy,ix+1])+dy*((1-dx)*phase[iy+1,ix]+dx*phase[iy+1,ix+1])
        selected=mask&(ux*ux+uy*uy<.95**2)&valid[iy,ix]&valid[iy+1,ix]&valid[iy,ix+1]&valid[iy+1,ix+1]
        for sign in [1,-1]:
            residual=np.angle(coherent*np.exp(-sign*2j*np.pi*interpolated))/(2*np.pi)
            results.append(dict(mapping=name,phase_sign=sign,samples=int(selected.sum()),
                max_wrapped_phase_error=float(abs(residual[selected]).max()),rms_wrapped_phase_error=float(np.sqrt(np.mean(residual[selected]**2)))))
    output=dict(hypothesis='Coherent support separates clipping from coordinate rescaling; phase independently interpolated from retained direct OPD',
        native_execution=False,source=str(folder.relative_to(ROOT)),independent_phase_source=str(source.relative_to(ROOT)),
        ellipse=dict(a=a,b_constraints=[low,high],compatible=low<=high,nominal_b_control=b,mask_mismatch=int(np.count_nonzero(candidate!=mask)),
            scope='Native support rejects a centered ellipse when lower constraint exceeds upper; midpoint is a rejected-geometry control, not a reconstructed pupil. No phase/MTF fit.'),comparisons=results)
    (ROOT/'development/evidence/CV-01/offline606-coherent-support.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,indent=2))

if __name__=='__main__':run()
