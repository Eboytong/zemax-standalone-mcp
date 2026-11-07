"""Independent complex-pupil autocorrelation from batch-ray OPD and intensity."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from tests.support.native import execute
from tests.support.diffraction_reference import pupil_autocorrelation
from zemax_mcp.pupil import real_f_numbers
from tests.native.test_surface_mtf_psf_reference_live import bilinear


@pytest.mark.zemax
def test_fft_surface_mtf_cooke_pupil_autocorrelation_diagnostic():
    _run_pupil_diagnostic(1, [1,3], 'surface_mtf509_pupil')


@pytest.mark.zemax
def test_fft_surface_mtf_cooke_primary_pupil_diagnostic():
    _run_pupil_diagnostic(2, [3], 'surface_mtf512_primary')


@pytest.mark.zemax
def test_fft_surface_mtf_apparent_pupil_autocorrelation_diagnostic():
    _run_pupil_diagnostic(2, [3], 'surface_mtf531_apparent', apparent=True)


@pytest.mark.zemax
def test_fft_surface_mtf_stretched_pupil_diagnostic():
    _run_pupil_diagnostic(2,[1,3],'surface_mtf566_stretched',stretched=True)


def _run_pupil_diagnostic(wavelength, fields, run_name, apparent=False,stretched=False):
    async def work(e):
        conditions=dict(reference='Zero-padded autocorrelation of independently traced OPD/intensity pupil',
            model='Official Cooke40 degree field',pupil_size=256,fields=fields,wavelength=wavelength,
            coordinates='(index-N/2)*pupil_stretch/(N/2-1); points strictly inside unit disk',
            hypotheses=['paraxial working F-number','real working F-number','native cutoff scale'],
            apparent_pupil_mapping=apparent,
            pupil_stretch=float(np.sqrt(256/32))if stretched else 1.,
            stretching_source='FFT pupil stretch sqrt(N/32); test whether coherent-line sampling explanation transfers to surface MTF',
            absolute_tolerance=.005,relative_tolerance=0)
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        summary=await e.call('get_system_summary');records=[];size=256;half=size//2
        stretch=np.sqrt(size/32)if stretched else 1.
        axis=(np.arange(size)-half)*stretch/(half-1)
        for field in fields:
            scales=[1.,1.];f_numbers=None
            if apparent:
                seed=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=[
                    dict(hx=0,hy=0 if field==1 else 1,px=px,py=py,wavelength=wavelength)
                    for px,py in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]]))))
                f_numbers=real_f_numbers(seed['rows'])
                scales=[f/min(f_numbers)for f in f_numbers]
            coords=[(j,i)for j in range(size)for i in range(size)
                if (axis[i]*scales[0])**2+(axis[j]*scales[1])**2<1]
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fft_surface_mtf',
                field=field,wavelength=wavelength,sampling='S_256x256',use_polarization=False))))
            grid=result['grids'][0];pupil=np.zeros((size,size),dtype=complex);trace_rows=[]
            for start in range(0,len(coords),8000):
                chunk=coords[start:start+8000]
                rays=[dict(hx=0,hy=0 if field==1 else 1,px=float(axis[i]*scales[0]),py=float(axis[j]*scales[1]),wavelength=wavelength)
                      for j,i in chunk]
                traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
                for (j,i),row in zip(chunk,traced['rows'],strict=True):
                    if not row['error_code'] and not row['vignette_code'] and row.get('opd') is not None:
                        pupil[j,i]=np.sqrt(row['intensity'])*np.exp(2j*np.pi*row['opd'])
                    trace_rows.append(dict(iy=j,ix=i,ray=row))
            power=float(np.sum(abs(pupil)**2));assert power>0
            acf=pupil_autocorrelation(pupil)
            wave=settings['wavelengths'][wavelength-1]['wavelength_um']*.001
            hypotheses={name:stretch/(wave*summary['first_order'][key])/(size-2)
                for name,key in [('paraxial','paraxial_working_f_number'),('real','real_working_f_number')]}
            hypotheses['native_cutoff']=stretch*grid['dx']*(size-1)/(size-2)
            if f_numbers:hypotheses['minimum_meridional_f_number']=stretch/(wave*min(f_numbers))/(size-2)
            comparisons={}
            for name,spacing in hypotheses.items():
                frequencies=(np.arange(2*size)-size)*spacing;points=[]
                for fx,fy in [(0,0),(10,0),(30,0),(50,0),(0,10),(0,30),(0,50),(20,30),(-20,30),(20,-30)]:
                    ix=round((fx-grid['min_x'])/grid['dx']);iy=round((fy-grid['min_y'])/grid['dy'])
                    fx=grid['min_x']+ix*grid['dx'];fy=grid['min_y']+iy*grid['dy']
                    actual=grid['values'][iy][ix];expected=bilinear(frequencies,frequencies,acf,fx,fy)
                    points.append(dict(fx=fx,fy=fy,native=actual,reference=expected,error=abs(actual-expected)))
                comparisons[name]=dict(frequency_spacing=spacing,points=points,maximum_error=max(p['error'] for p in points))
            records.append(dict(field=field,result=result,pupil_power=power,valid_samples=int(np.count_nonzero(pupil)),
                                comparisons=comparisons,summary=summary,entrance_mapping_scales=scales,
                                meridional_f_numbers=f_numbers))
            (e.folder/f'field{field}-rays.json').write_text(json.dumps(trace_rows,ensure_ascii=False),encoding='utf-8')
            (e.folder/'autocorrelation.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['close_attempted'] and not task.get('cleanup_warnings')
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute(run_name,work))
