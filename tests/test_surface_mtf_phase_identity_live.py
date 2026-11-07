"""Separate native wavefront phase identity from Fourier-coordinate diagnostics."""
import asyncio
import json
from pathlib import Path
import numpy as np
import pytest
from support.native import execute
from support.diffraction_reference import pupil_autocorrelation
from test_surface_mtf_psf_reference_live import bilinear as interpolate


@pytest.mark.zemax
def test_fft_surface_mtf_native_phase_identity_diagnostic():
    root=Path(__file__).resolve().parents[1]
    sources={False:root/'outputs/runs/surface_mtf512_primary_89cacce054',
             True:root/'outputs/runs/surface_mtf531_apparent_b12614714b'}
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        conditions=dict(hypothesis='Surface-MTF residual may originate in the phase reference rather than frequency mapping',
            field=3,wavelength=2,sampling='S_256x256',remove_tilt=False,absolute_mtf_tolerance=.005,
            phase_tolerance='1e-8 waves+1e-7 relative',
            scope='Native wavefront vs independently traced retained OPD; downstream Fourier comparisons are diagnostics')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        surface=await e.finish(await e.call('run_analysis',dict(request=dict(kind='fft_surface_mtf',field=3,wavelength=2,sampling='S_256x256'))))
        grid=surface['grids'][0];records=[]
        for exit_pupil,source in sources.items():
            prior=json.loads((source/'autocorrelation.json').read_text(encoding='utf-8'))[0]
            assert prior['field']==3 and prior['result']['task']['settings']['native']['Wavelength']==2
            request=dict(kind='wavefront',field=3,wavelength=2,sampling='S_256x256',remove_tilt=False,use_exit_pupil=exit_pupil)
            wavefront=await e.finish(await e.call('run_analysis',dict(request=request)))
            phase=np.asarray(wavefront['grids'][0]['values'],dtype=float)
            assert phase.shape==(256,256)
            entries=json.loads((source/'field3-rays.json').read_text(encoding='utf-8'))
            native_pupil=np.zeros((256,256),complex);ray_pupil=np.zeros((256,256),complex)
            phase_errors=[];failures=0
            for entry in entries:
                r=entry['ray'];iy=entry['iy'];ix=entry['ix']
                if r['error_code']or r['vignette_code']or r.get('opd')is None:continue
                actual=phase[iy,ix];error=abs(actual-r['opd'])
                phase_errors.append(error)
                failures+=not(error<=1e-8+1e-7*abs(r['opd']))
                amplitude=np.sqrt(r['intensity'])
                native_pupil[iy,ix]=amplitude*np.exp(2j*np.pi*actual)
                ray_pupil[iy,ix]=amplitude*np.exp(2j*np.pi*r['opd'])
            assert phase_errors
            native_acf=pupil_autocorrelation(native_pupil);ray_acf=pupil_autocorrelation(ray_pupil)
            chief=next(entry['ray']for entry in entries if entry['ray']['input']['px']==entry['ray']['input']['py']==0)
            cos=abs(chief['direction'][2]);comparisons=[]
            for hypothesis,old in prior['comparisons'].items():
                freq=(np.arange(512)-256)*old['frequency_spacing']
                for projection,multiplier in [('none',1.),('chief_normal_to_image',1/cos)]:
                    points=[]
                    for point in old['points']:
                        ix=round((point['fx']-grid['min_x'])/grid['dx']);iy=round((point['fy']-grid['min_y'])/grid['dy'])
                        fx=grid['min_x']+ix*grid['dx'];fy=grid['min_y']+iy*grid['dy']
                        ref=interpolate(freq,freq,native_acf,fx,fy*multiplier)
                        actual=grid['values'][iy][ix]
                        points.append(dict(fx=fx,fy=fy,native=actual,reference=ref,error=abs(actual-ref)))
                    comparisons.append(dict(frequency=hypothesis,projection=projection,points=points,maximum_error=max(p['error']for p in points)))
            records.append(dict(request=request,wavefront=wavefront,source=str(source),
                phase_samples=len(phase_errors),maximum_phase_error=max(phase_errors),phase_failed_samples=int(failures),
                maximum_acf_difference=float(np.max(abs(native_acf-ray_acf))),comparisons=comparisons))
            (e.folder/'phase-identity.json').write_text(json.dumps(dict(surface=surface,records=records),ensure_ascii=False,indent=2),encoding='utf-8')
            status=await e.call('get_task_status',dict(task_id=wavefront['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted'] and not status.get('cleanup_warnings')
        status=await e.call('get_task_status',dict(task_id=surface['task']['task_id']))
        assert status['close_attempted'] and not status.get('cleanup_warnings')
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('surface_mtf603_phase_identity',guarded))
