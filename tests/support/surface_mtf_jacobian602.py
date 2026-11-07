"""Independent local outgoing-direction Jacobian as a frequency-scale control."""
import json
from pathlib import Path
import numpy as np
from diffraction_reference import pupil_autocorrelation
from surface_mtf_angular536 import interpolate

ROOT=Path(__file__).resolve().parents[2]

def run():
    folder=ROOT/'outputs/runs/surface_mtf566_stretched_e003d11f7f'
    records=[]
    for original in json.loads((folder/'autocorrelation.json').read_text(encoding='utf-8')):
        entries=json.loads((folder/f"field{original['field']}-rays.json").read_text(encoding='utf-8'))
        rays={(e['iy'],e['ix']):e['ray']for e in entries}
        pupil=np.zeros((256,256),complex)
        for (iy,ix),r in rays.items():
            if not r['error_code']and not r['vignette_code']and r.get('opd')is not None:
                pupil[iy,ix]=np.sqrt(r['intensity'])*np.exp(2j*np.pi*r['opd'])
        acf=pupil_autocorrelation(pupil)
        chief=np.array(rays[128,128]['direction']);tangent=np.cross(chief,[1.,0.,0.]);tangent/=np.linalg.norm(tangent)
        wave=original['result']['system_settings']['wavelengths'][1]['wavelength_um']*.001
        comparisons=[]
        for h in [1,2,4]:
            cols=[rays[128,128-h],rays[128,128+h]]
            lines=[rays[128-h,128],rays[128+h,128]]
            dl=(np.array(cols[1]['direction'])-cols[0]['direction'])/(cols[1]['input']['px']-cols[0]['input']['px'])
            dm=(np.array(lines[1]['direction'])-lines[0]['direction'])/(lines[1]['input']['py']-lines[0]['input']['py'])
            for plane,dy in [('image',abs(dm[1])),('chief_normal',abs(dm@tangent))]:
                dx=abs(dl[0]);delta_p=np.sqrt(8)/127
                x=(np.arange(512)-256)*dx*delta_p/wave
                y=(np.arange(512)-256)*dy*delta_p/wave
                points=[]
                for p in original['comparisons']['native_cutoff']['points']:
                    ref=interpolate(x,y,acf,p['fx'],p['fy'])
                    points.append(dict(fx=p['fx'],fy=p['fy'],native=p['native'],reference=ref,error=abs(p['native']-ref)))
                comparisons.append(dict(h=h,plane=plane,derivatives=[dx,dy],frequency_steps=[float(x[257]),float(y[257])],points=points,maximum_error=max(p['error']for p in points)))
        records.append(dict(field=original['field'],comparisons=comparisons))
    output=dict(hypothesis='Central image direction derivatives may set FFT frequency scale rather than marginal-ray F numbers',
        source=str(folder.relative_to(ROOT)),native_execution=False,absolute_tolerance=.005,
        reference='Symmetric central direction differences at1/2/4 retained pupil steps; no MTF-fitted factors',records=records)
    (ROOT/'verification/development/CV-01/offline602-local-jacobian.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    for record in records:print(record['field'],[(c['h'],c['plane'],c['derivatives'],c['maximum_error'])for c in record['comparisons']])

if __name__=='__main__':run()
