"""PSF Fourier/energy identities on the fixed Cooke field/wavelength matrix."""
import asyncio
import json
from pathlib import Path
import pytest
from support.native import execute
from support.finite_reference import normalized_otf
from zemax_mcp.evaluation import interpolate


@pytest.mark.zemax
@pytest.mark.parametrize('field', [1,2,3])
@pytest.mark.parametrize('wavelength', [1,2,3,0])
def test_cooke_finite_psf_mtf_energy_native(field,wavelength):
    async def work(e):
        import numpy as np
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(lens)))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=y)for y in (0,14,20)],
            wavelengths=[dict(wavelength_um=w,weight=p)for w,p in ((.486,.2),(.55,.5),(.644,.3))])))
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        records=[]
        for family in ('huygens','fft'):
            for n in (256,512):
                sample=f'S_{n}x{n}'
                psf=await e.finish(await e.call('run_analysis',dict(request=dict(kind=family+'_psf',field=field,wavelength=wavelength,
                    sampling=sample,image_sampling='S_512x512',image_delta=.5,normalize=True))),timeout_seconds=600)
                g=psf['grids'][0]; values=np.asarray(g['values'],dtype=float)
                assert np.isfinite(values).all() and values.sum()>0
                fx,fy,otf=normalized_otf(values,g['dx']/1000,g['dy']/1000)
                if family=='huygens':
                    mtf=await e.finish(await e.call('run_analysis',dict(request=dict(kind='huygens_mtf',field=field,wavelength=wavelength,
                        sampling=sample,image_sampling='S_512x512',image_delta=.5,maximum_frequency=50))))
                else:
                    mtf=await e.finish(await e.call('run_fft_mtf',dict(field=field,wavelength=wavelength,
                        sampling=sample,maximum_frequency=50)))
                for series in mtf['series']:
                    for column,label in enumerate(series['labels']):
                        assert label in ('Tangential','Sagittal','子午','弧矢'),label
                        tangential=label in ('Tangential','子午')
                        frequencies=fy if tangential else fx
                        center=(values.shape[0]//2,values.shape[1]//2)
                        line=abs(otf[:,center[1]])if tangential else abs(otf[center[0],:])
                        for f in (10,25,50):
                            reference=float(np.interp(f,frequencies,line))
                            actual=interpolate(series['x'],[v[column]for v in series['y']],f)
                            records.append(dict(check='PSF Fourier MTF',family=family,sampling=n,label=label,
                                frequency_cycles_mm=f,actual=actual,expected=reference,atol=.02,passed=abs(actual-reference)<=.02))
                if family=='fft':
                    ee=await e.finish(await e.call('run_analysis',dict(request=dict(kind='diffraction_encircled_energy',
                        field=field,wavelength=wavelength,sampling=sample,reference='ChiefRay',maximum_radius=40))))
                    x=g['min_x']+np.arange(g['nx'])*g['dx'];y=g['min_y']+np.arange(g['ny'])*g['dy']
                    for series in ee['series']:
                        if series['description'].strip().casefold() in ('衍射极限','diffraction limit'):
                            continue
                        for r in (10,20):
                            expected=float(values[y[:,None]**2+x[None,:]**2<=r*r].sum()/values.sum())
                            actual=interpolate(series['x'],[v[0]for v in series['y']],r)
                            records.append(dict(check='PSF energy cross reference',family=family,sampling=n,radius_um=r,
                                actual=actual,expected=expected,atol=.025,passed=abs(actual-expected)<=.025,
                                scope='FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'))
        (e.folder/'imaging-reference.json').write_text(json.dumps(dict(field=field,wavelength=wavelength,
            scope='Independent Fourier and disk integration of saved native PSF; not a fully independent optical pupil model',
            checks=records),indent=2),encoding='utf-8')
        assert records and all(r['passed']for r in records),[r for r in records if not r['passed']]
    asyncio.run(execute(f'finite_imaging_F{field}_W{wavelength}',work,role='fixture'))
