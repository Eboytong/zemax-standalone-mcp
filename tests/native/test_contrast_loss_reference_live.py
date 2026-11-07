"""Moore-Elliott two-ray OPD reference and native phase identity discovery."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('frequency',[0,50])
def test_contrast_loss_independent_ray_reference(frequency):
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(loss_atol=.005,phase_atol_degrees=1e-5,
            definition='loss=0.5*(1-cos(2*pi*(OPDplus-OPDminus))); phase=360*central OPD',
            shear_candidates='delta=2*frequency*wavelength_mm*working_f_number; paraxial and real first-order candidates'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,
            material='MIRROR',thickness=-100.02,semi_diameter=5,is_stop=True,replace_solves=True)]))
        summary=await e.call('get_system_summary')
        request=dict(kind='contrast_loss',sampling='S_11x11',frequency=frequency,normalize=False,show_opd=True)
        result=await e.finish(await e.call('run_analysis',dict(request=request)))
        (e.folder/'native.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        records=[]
        for candidate in ['paraxial_working_f_number','real_working_f_number']:
            half_shear=.05 if frequency==0 else frequency*.00055*summary['first_order'][candidate]
            for direction,phase_index,loss_index in [('Tangential',0,1),('Sagittal',2,3)]:
                grid=result['grids'][loss_index]
                points=[(x,y) for y,row in enumerate(grid['values']) for x,v in enumerate(row) if v is not None]
                rays=[]
                for x,y in points:
                    px=(x-5)/5;py=(y-5)/5
                    for offset in [0,1,-1]:
                        rays.append(dict(hx=0,hy=0,wavelength=1,
                            px=px+(offset*half_shear if direction=='Sagittal' else 0),
                            py=py+(offset*half_shear if direction=='Tangential' else 0)))
                traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
                rows=traced['rows'];assert all(r['error_code']==0 and r['opd'] is not None for r in rows)
                comparisons=[]
                for i,(x,y) in enumerate(points):
                    central,plus,minus=[rows[3*i+j]['opd'] for j in range(3)]
                    comparisons.append(dict(x=x,y=y,phase_error=result['grids'][phase_index]['values'][y][x]-360*central,
                        loss_error=grid['values'][y][x]-.5*(1-math.cos(2*math.pi*(plus-minus)))))
                records.append(dict(candidate=candidate,direction=direction,half_shear=half_shear,comparisons=comparisons))
                (e.folder/'comparisons.json').write_text(json.dumps(dict(summary=summary,records=records),ensure_ascii=False,indent=2),encoding='utf-8')
                if candidate=='real_working_f_number':
                    e.check(direction+' phase degrees',max(abs(c['phase_error']) for c in comparisons),0,atol=1e-5,rtol=0)
                    e.check(direction+' Moore-Elliott contrast loss',max(abs(c['loss_error']) for c in comparisons),0,atol=.005,rtol=0)
                    for y,row in enumerate(grid['values']):
                        for x,value in enumerate(row):
                            px=(x-5)/5;py=(y-5)/5
                            inside=all((px+(s*half_shear if direction=='Sagittal' else 0))**2+
                                       (py+(s*half_shear if direction=='Tangential' else 0))**2<=1 for s in [-1,1])
                            assert (value is not None)==inside,(direction,x,y,value)
    asyncio.run(execute('contrast_loss312_reference',work))
