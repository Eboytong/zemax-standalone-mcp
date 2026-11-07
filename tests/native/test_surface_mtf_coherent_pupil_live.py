"""Probe whether coherent OTF exposes the internally sampled complex pupil."""
import asyncio,json
from pathlib import Path
import numpy as np
import pytest
from tests.support.native import execute
from tests.support.diffraction_reference import pupil_autocorrelation


@pytest.mark.zemax
def test_fft_surface_mtf_coherent_pupil_diagnostic():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        records=[]
        for field in [1,3]:
            modes={}
            for mode in ['MTF_Incoherent','Real_Coherent','Imaginary_Coherent']:
                q=dict(kind='fft_surface_mtf',field=field,wavelength=2,sampling='S_256x256',mtf_type=mode)
                modes[mode]=await e.finish(await e.call('run_analysis',dict(request=q)))
                status=await e.call('get_task_status',dict(task_id=modes[mode]['task']['task_id']))
                assert status['state']=='succeeded'and status['close_attempted']and not status.get('cleanup_warnings')
            real=modes['Real_Coherent']['grids'][0];imag=modes['Imaginary_Coherent']['grids'][0];mtf=modes['MTF_Incoherent']['grids'][0]
            pupil=np.asarray(real['values'])+1j*np.asarray(imag['values']);amplitude=abs(pupil)
            assert pupil.shape==np.asarray(mtf['values']).shape
            acf=pupil_autocorrelation(pupil)
            cx=mtf['zero_frequency_index']['x'];cy=mtf['zero_frequency_index']['y']
            center_y,center_x=np.array(acf.shape)//2
            predicted=acf[center_y-cy:center_y-cy+mtf['ny'],center_x-cx:center_x-cx+mtf['nx']]
            differences=abs(predicted-np.asarray(mtf['values']))
            support=np.argwhere(amplitude>1e-10)
            records.append(dict(field=field,modes=modes,coherent_support=dict(count=int(len(support)),
                min_yx=support.min(axis=0).tolist(),max_yx=support.max(axis=0).tolist(),amplitude_min=float(amplitude.min()),amplitude_max=float(amplitude.max())),
                autocorrelation=dict(integer_lag_convention='native offset from native DC; coherent grid node spacing equals lag spacing',
                    maximum_error=float(differences.max()),rms_error=float(np.sqrt(np.mean(differences**2))),absolute_tolerance=.005,
                    passed=bool(np.max(differences)<=.005))))
            (e.folder/'coherent-pupil.json').write_text(json.dumps(dict(hypothesis='Native coherent OTF exposes complex pupil whose autocorrelation yields incoherent MTF',
                scope='Cross-outlet diagnostic; independent traced phase identity still required',records=records),ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('surface_mtf605_coherent_pupil',guarded))
