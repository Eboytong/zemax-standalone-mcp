"""Explicit finite Ince mode list, waist and propagated relative complex field."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from tests.support.ince_reference import field,coefficients

MODES=[(0,0,0),(1,1,0),(1,1,1),(2,0,0),(2,2,0),(2,2,1),(4,0,0),(4,2,0),(4,2,1),(4,4,0),(4,4,1)]


@pytest.mark.zemax
@pytest.mark.parametrize('p,m,odd',MODES)
@pytest.mark.parametrize('f0',[.05,.1])
def test_finite_ince_propagated_field_native(p,m,odd,f0):
    async def work(e):
        import numpy as np
        await e.model();records=[];waist=.1;zR=math.pi*waist*waist/.00055
        for ratio in (0,.5,1):
            z=ratio*zR
            await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=z,replace_solves=True)]))
            data=await e.finish(await e.call('run_pop',dict(request=dict(beam_type='DLL',beam_file='Ince-Gaussian-64.dll',
                beam_parameters={0:waist,4:f0,5:odd,6:p,7:m},x_sampling='S_256x256',y_sampling='S_256x256',x_width=1,y_width=1))))
            g=data['grids'][0];x=g['min_x']+np.arange(g['nx'])*g['dx'];y=g['min_y']+np.arange(g['ny'])*g['dy']
            reference=field(x[None,:],y[:,None],p,m,bool(odd),waist,f0,z)
            intensity=abs(reference)**2;intensity/=intensity.sum()*g['dx']*g['dy']
            actual=np.asarray(g['values'],dtype=float)
            error=float(np.max(abs(actual-intensity))/intensity.max())
            item=dict(rayleigh_lengths=ratio,z_mm=z,normalized_intensity_error=error,actual_metrics=data['metrics'],complex_samples=[])
            records.append(item)
            beam=next(a['path']for a in data['artifacts']if a['kind']=='beam')
            for px,py in ((.05,.05),(-.05,.05),(.05,-.05),(.1,.05),(.05,.1),(.075,.025)):
                ix=round((px-g['min_x'])/g['dx']);iy=round((py-g['min_y'])/g['dy'])
                row=(await e.call('get_beam_file',dict(request=dict(path=beam,start=iy*g['nx']+ix,count=1,include_coordinates=True))))['rows'][0]
                q=complex(field(row['x'],row['y'],p,m,bool(odd),waist,f0,z))
                item['complex_samples'].append(dict(x_mm=row['x'],y_mm=row['y'],expected_real=q.real,expected_imag=q.imag,
                    actual_real=row['ex_real'],actual_imag=row['ex_imag']))
            samples=item['complex_samples'];anchor=max(samples,key=lambda r:abs(complex(r['expected_real'],r['expected_imag'])))
            factor=complex(anchor['actual_real'],anchor['actual_imag'])/complex(anchor['expected_real'],anchor['expected_imag'])
            errors=[]
            for s in samples:
                q=complex(s['actual_real'],s['actual_imag'])/factor
                expected=complex(s['expected_real'],s['expected_imag'])
                errors.append(abs(q-expected)/max(abs(complex(anchor['expected_real'],anchor['expected_imag'])),1e-30))
            item['max_relative_complex_sample_error']=max(errors)
            item['passed']=error<=.005 and max(errors)<=.005 and abs(data['metrics']['integrated_power']-1)<=.005
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
        (e.folder/'ince-propagation-reference.json').write_text(json.dumps(dict(p=p,m=m,odd=odd,f0_mm=f0,w0_mm=waist,
            equation="Y''+epsilon sin(2eta)Y'+(a-p epsilon cos(2eta))Y=0; finite Fourier eigenproblem",
            phase='native conjugate propagation; only one spatially constant complex factor removed per plane',rows=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),records
    asyncio.run(execute(f'finite_ince_p{p}m{m}o{odd}f{f0}',work))
