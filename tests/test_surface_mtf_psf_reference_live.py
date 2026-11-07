"""Independent discrete Fourier reference from native image irradiance grids."""
import asyncio
import json
import math
from pathlib import Path

import numpy as np
import pytest

from support.native import execute


def psf_otf(grid):
    values=np.asarray(grid['values'],dtype=float)
    assert values.shape==(grid['ny'],grid['nx'])
    assert np.all(np.isfinite(values)) and values.min()>=0 and values.sum()>0
    spectrum=np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(values)))
    magnitude=np.abs(spectrum)/values.sum()
    # Native PSF coordinates are in micrometers; MTF axes in cycles/mm.
    x=np.fft.fftshift(np.fft.fftfreq(grid['nx'],d=grid['dx']*.001))
    y=np.fft.fftshift(np.fft.fftfreq(grid['ny'],d=grid['dy']*.001))
    return x,y,magnitude


def bilinear(x,y,values,fx,fy):
    assert x[0]<=fx<=x[-1] and y[0]<=fy<=y[-1]
    i=min(int(np.searchsorted(x,fx,side='right'))-1,len(x)-2)
    j=min(int(np.searchsorted(y,fy,side='right'))-1,len(y)-2)
    a=(fx-x[i])/(x[i+1]-x[i]);b=(fy-y[j])/(y[j+1]-y[j])
    return float((1-b)*((1-a)*values[j,i]+a*values[j,i+1])+
                 b*((1-a)*values[j+1,i]+a*values[j+1,i+1]))


def test_fourier_reference_rectangular_anisotropic_gaussian():
    nx,ny=128,96
    dx,dy=2.,1.
    x=(np.arange(nx)-nx//2)*dx
    y=(np.arange(ny)-ny//2)*dy
    values=np.exp(-.5*((x[None,:]/10)**2+(y[:,None]/6)**2))
    fx,fy,otf=psf_otf(dict(nx=nx,ny=ny,dx=dx,dy=dy,values=values.tolist()))
    assert otf.shape==(ny,nx)
    for j,i in [(48,64),(48,65),(49,64),(50,66)]:
        expected=math.exp(-2*math.pi**2*((.010*fx[i])**2+(.006*fy[j])**2))
        assert bilinear(fx,fy,otf,float(fx[i]),float(fy[j]))==pytest.approx(expected,abs=1e-12)


def test_fourier_reference_shifted_impulse_and_interpolation():
    values=np.zeros((7,10));values[1,8]=2.5
    x,y,otf=psf_otf(dict(nx=10,ny=7,dx=2,dy=3,values=values.tolist()))
    assert np.max(np.abs(otf-1))<1e-14
    plane=2*x[None,:]+3*y[:,None]
    assert bilinear(x,y,plane,7.25,-8.5)==pytest.approx(2*7.25+3*(-8.5))


@pytest.mark.zemax
@pytest.mark.parametrize('family',['fft','huygens'])
def test_surface_mtf_vs_independent_psf_fourier(family):
    async def work(e):
        (e.folder/'reference.json').write_text(json.dumps(dict(
            item_id='CV-01.'+('FftSurfaceMtf' if family=='fft' else 'HuygensSurfaceMtf'),
            source='Native PSF irradiance transformed by numpy discrete Fourier sum; DC normalized',
            model='Official Cooke 40 degree field sample',fields=[1,3],wavelength=1,
            pupil_sampling=256,image_sampling=512,image_delta_um=0 if family=='fft' else 1,
            comparison='Bilinear physical-frequency interpolation; positive/negative axial and off-axis frequencies',
            absolute_tolerance=.005,relative_tolerance=0),indent=2),encoding='utf-8')
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        failures=[];records=[]
        for field in [1,3]:
            chief=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(
                rays=[dict(hx=0,hy=0 if field==1 else 1,px=0,py=0,wavelength=1)]))))
            direction=chief['rows'][0]['direction']
            assert chief['rows'][0]['error_code']==0 and abs(direction[0])<1e-10
            common=dict(field=field,wavelength=1,sampling='S_256x256',use_polarization=False)
            q=dict(kind=family+'_surface_mtf',**common)
            if family=='huygens':q.update(image_sampling='S_512x512',image_delta=1)
            surface=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
            psf=await e.finish(await e.call('run_analysis',dict(request=dict(
                kind=family+'_psf',**common,image_sampling='S_512x512',image_delta=0 if family=='fft' else 1,normalize=True))),timeout_seconds=180)
            g=surface['grids'][0];p=psf['grids'][0]
            x,y,otf=psf_otf(p)
            points=[]
            for fx,fy in [(0,0),(10,0),(30,0),(50,0),(0,10),(0,30),(0,50),(20,30),(-20,30),(20,-30)]:
                ix=round((fx-g['min_x'])/g['dx']);iy=round((fy-g['min_y'])/g['dy'])
                assert 0<=ix<g['nx'] and 0<=iy<g['ny']
                fx=g['min_x']+ix*g['dx'];fy=g['min_y']+iy*g['dy']
                # FFT PSF is sampled on the plane normal to the chief ray;
                # compare its Fourier frequency after the image-plane projection.
                # These Cooke fields lie in YZ, so sagittal frequency is unchanged.
                psf_fy=fy/abs(direction[2]) if family=='fft' else fy
                actual=g['values'][iy][ix];expected=bilinear(x,y,otf,fx,psf_fy)
                points.append(dict(fx=fx,fy=fy,actual=actual,reference=expected,error=actual-expected))
                try:e.check(f'{family} field{field} PSF/OTF ({fx},{fy})',actual,expected,atol=.005,rtol=0)
                except AssertionError:failures.append(e.checks[-1])
            records.append(dict(field=field,surface_task=surface['task']['task_id'],psf_task=psf['task']['task_id'],
                                surface_axes={k:g[k] for k in ['nx','ny','dx','dy','min_x','min_y','native_axes']},
                                psf_axes={k:p[k] for k in ['nx','ny','dx','dy','min_x','min_y']},
                                chief_direction=direction,fft_psf_projection='fy_psf=fy_image/abs(chief_n); XZ chief component zero',points=points))
            (e.folder/'fourier-comparison.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
            for result in [surface,psf]:
                task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert task['state']=='succeeded' and task['close_attempted']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute('surface_mtf283_'+family,work))
