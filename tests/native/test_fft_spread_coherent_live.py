"""Independent one-dimensional pupil diffraction for coherent line response."""
import asyncio
import json

import numpy as np
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('pupil_size',[64,128])
@pytest.mark.parametrize('plot_sampling',['psf_auto','dft_knots'])
@pytest.mark.parametrize('pupil_nodes',['interior','guard','fft_stretched'])
def test_fft_coherent_line_pupil_slice(pupil_size,plot_sampling,pupil_nodes):
    async def work(e):
        half=pupil_size//2
        stretch=np.sqrt(pupil_size/32)if pupil_nodes=='fft_stretched'else 1.
        radius=half if pupil_nodes=='interior'else (half-1)/stretch
        (e.folder/'conditions.json').write_text(json.dumps(dict(intensity_atol=.005,
            reference='Scalar Fraunhofer sum at native physical positions; complex pupil slice from independent OPD batch rays',
            pupil_size=pupil_size,plot_sampling=plot_sampling,pupil_nodes=pupil_nodes,
            pupil_center=half,pupil_radius=radius,pupil_stretch=stretch,
            stretching_source='OpticStudio2024R2 FFT PSF discussion: sqrt(N/32); manual535 indices777/778',
            wavelength_um=.55,pupil_radius_mm=5,reference_distance_mm='absolute image distance',
            interpolation='native original knots, every second text sample; no fitted coordinate scale'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        records=[];failures=[];half=pupil_size//2
        for thickness in [-100,-100.02]:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,
                material='MIRROR',thickness=thickness,semi_diameter=5,is_stop=True,replace_solves=True)]))
            nodes = [i for i in range(pupil_size) if abs((i-half)/radius)<1]
            rays=[dict(hx=0,hy=0,px=0,py=(i-half)/radius,wavelength=1) for i in nodes]
            traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
            assert all(r['error_code']==0 for r in traced['rows'])
            pupil=np.zeros(pupil_size,dtype=complex)
            pupil[nodes]=[np.sqrt(r['intensity'])*np.exp(2j*np.pi*r['opd']) for r in traced['rows']]
            psf=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fft_psf',sampling=f'S_{pupil_size}x{pupil_size}',image_sampling='S_256x256'))))
            grid=psf['grids'][0]
            scale=(pupil_size*grid['dy'] if plot_sampling=='psf_auto'
                   else pupil_size*.55*abs(thickness)/10/2)
            wavefronts=[]
            for exit_pupil in [False,True]:
                wavefronts.append(await e.finish(await e.call('run_analysis',dict(request=dict(kind='wavefront',
                    sampling=f'S_{pupil_size}x{pupil_size}',use_exit_pupil=exit_pupil)))))
            summary=await e.call('get_system_summary')
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fft_line_edge_spread',
                use_coherent_psf=True,data_type='X_Linear',sampling=f'S_{pupil_size}x{pupil_size}',plot_scale=scale))))
            actual=np.asarray(result['series'][0]['y'])[2::2,0]
            positions=np.asarray(result['series'][0]['x'])[2::2]
            pupil_positions=5*(np.arange(pupil_size)-half)/radius
            amplitude=np.exp(-2j*np.pi*positions[:,None]*pupil_positions[None,:]/(.55*abs(thickness)))@pupil
            expected=abs(amplitude)**2;expected/=expected.max()
            records.append(dict(thickness=thickness,pupil_real=pupil.real.tolist(),pupil_imag=pupil.imag.tolist(),
                positions_um=positions.tolist(),pupil_positions_mm=pupil_positions.tolist(),
                expected=expected.tolist(),actual=actual.tolist(),psf=psf,wavefronts=wavefronts,summary=summary,result=result))
            (e.folder/'comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            try:e.check(str(thickness)+' coherent pupil slice',float(abs(actual-expected).max()),0,atol=.005,rtol=0)
            except AssertionError:failures.append(e.checks[-1])
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
