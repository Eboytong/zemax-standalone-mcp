"""Inspect native non-square full-field coefficient grids and settings identity."""
import asyncio
import json
from pathlib import Path

import pytest

from support.native import execute
from support.zernike_reference import pupil_points,fit_standard15


@pytest.mark.zemax
def test_full_field_aberration_non_square_outlet():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for aberration in ['Defocus','PrimaryAstigmatism','PrimaryComa','SpecifiedTerm']:
            request=dict(kind='full_field_aberration',field=1,wavelength=1,
                         x_field_width=4,y_field_width=2,x_field_sampling=7,y_field_sampling=5,
                         pupil_sampling='S_64x64',maximum_term=15,aberration_type=aberration)
            if aberration=='SpecifiedTerm':request['aberration_number']=5
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['state']=='succeeded' and task['close_attempted']
            assert result['grids'] or result['series'] or result['rows']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        references=[]
        for fx,fy in [(0,0),(4,2),(-4,-2)]:
            await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=fx,y=fy)])))
            for kind in ['zernike_standard','zernike_fringe']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(
                    kind=kind,field=1,wavelength=1,sampling='S_64x64',maximum_terms=15))))
                references.append(dict(x=fx,y=fy,kind=kind,result=result))
                (e.folder/'zernike-reference.json').write_text(json.dumps(references,ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=4,y=2)])))
        fits=[]
        (e.folder/'opd-reference.json').write_text(json.dumps(dict(
            sample=96,fit='Explicit orthonormal Standard Zernike1-15 least squares on uniform unit-disk OPD rays',
            coefficient_atol_waves=1e-4,coefficient_rtol=.01,scope='Diagnostic comparison before production result annotation'),indent=2),encoding='utf-8')
        for fx,fy in [(0,0),(4,2),(4,-2)]:
            x,y=pupil_points(96)
            rays=[dict(hx=fx/(20**.5),hy=fy/(20**.5),px=float(px),py=float(py),wavelength=1) for px,py in zip(x,y)]
            result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
            valid=[r for r in result['rows']if r['error_code']==0 and r.get('opd') is not None]
            assert len(valid)==len(rays)
            coefficients=fit_standard15(x,y,[r['opd']for r in valid]).tolist()
            fits.append(dict(x=fx,y=fy,coefficients=coefficients))
            (e.folder/'opd-fit.json').write_text(json.dumps(fits,indent=2),encoding='utf-8')
            for record in records:
                q=record['request'];g=record['result']['grids'][0]
                ix=round((fx-g['min_x'])/g['dx']);iy=round((fy-g['min_y'])/g['dy'])
                expected=(coefficients[3] if q['aberration_type']=='Defocus' else
                          (coefficients[4]**2+coefficients[5]**2)**.5 if q['aberration_type']=='PrimaryAstigmatism' else
                          (coefficients[6]**2+coefficients[7]**2)**.5 if q['aberration_type']=='PrimaryComa' else coefficients[4])
                e.check(f"{q['aberration_type']} independent OPD at {fx},{fy}",g['values'][iy][ix],expected,atol=1e-4,rtol=.01)
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=4,y=2)])))
        variants=[]
        for shape,display in [('Rectangular','Relative'),('Rectangular','Average'),('Elliptical','Absolute')]:
            q=records[-1]['request']|dict(field_shape=shape,display=display)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            variants.append(dict(request=q,result=result))
            (e.folder/'display-variants.json').write_text(json.dumps(variants,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('full_field288',work))
