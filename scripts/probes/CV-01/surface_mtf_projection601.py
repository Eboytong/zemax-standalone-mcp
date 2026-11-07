import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Fixed chief-plane projection controls from retained independent pupil rays."""
import json
from pathlib import Path
import numpy as np
from tests.support.diffraction_reference import pupil_autocorrelation
from surface_mtf_angular536 import interpolate

ROOT=PROJECT_ROOT

def run():
    records=[]
    for folder_name,stretch in [('surface_mtf531_apparent_b12614714b',1.),
                                ('surface_mtf566_stretched_e003d11f7f',np.sqrt(8))]:
        folder=ROOT/'outputs/runs'/folder_name
        for record in json.loads((folder/'autocorrelation.json').read_text(encoding='utf-8')):
            rays=json.loads((folder/f"field{record['field']}-rays.json").read_text(encoding='utf-8'))
            pupil=np.zeros((256,256),complex)
            chief=next(e['ray']for e in rays if e['ray']['input']['px']==e['ray']['input']['py']==0)
            assert abs(chief['direction'][0])<1e-12
            for e in rays:
                r=e['ray']
                if not r['error_code']and not r['vignette_code']and r.get('opd')is not None:
                    pupil[e['iy'],e['ix']]=np.sqrt(r['intensity'])*np.exp(2j*np.pi*r['opd'])
            acf=pupil_autocorrelation(pupil)
            grid=record['result']['grids'][0]
            cos=abs(chief['direction'][2])
            comparisons=[]
            # Projection is fixed by independently traced chief direction, not fitted.
            for name,scale in [('none',1.),('chief_normal_to_image',1/cos),('inverse_control',cos)]:
                for hypothesis,original in record['comparisons'].items():
                    spacing=original['frequency_spacing']
                    freq=(np.arange(512)-256)*spacing
                    points=[]
                    for old in original['points']:
                        value=interpolate(freq,freq,acf,old['fx'],old['fy']*scale)
                        points.append(dict(fx=old['fx'],fy=old['fy'],native=old['native'],reference=value,error=abs(value-old['native'])))
                    comparisons.append(dict(projection=name,frequency_scale=hypothesis,y_scale=scale,
                        points=points,maximum_error=max(p['error']for p in points)))
            records.append(dict(source=str(folder.relative_to(ROOT)),field=record['field'],
                chief_direction=chief['direction'],pupil_stretch=float(stretch),comparisons=comparisons))
    output=ROOT/'development/evidence/CV-01/offline601-chief-projection.json'
    output.write_text(json.dumps(dict(hypothesis='Apparent/entrance pupil frequency and chief-normal to image-plane projection are distinct operations',
        command='.venv/Scripts/python.exe -X utf8 scripts/probes/CV-01/surface_mtf_projection601.py',
        native_execution=False,absolute_tolerance=.005,records=records),indent=2)+'\n',encoding='utf-8')
    for record in records:
        print(record['source'],record['field'],[(c['projection'],c['frequency_scale'],round(c['maximum_error'],9))for c in record['comparisons']])

if __name__=='__main__':run()
