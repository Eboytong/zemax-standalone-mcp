"""Single-variable F-number diagnostic using the preserved independent pupil."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest

from support.native import execute
from support.diffraction_reference import pupil_autocorrelation
from zemax_mcp.pupil import real_f_numbers
from test_surface_mtf_psf_reference_live import bilinear


@pytest.mark.zemax
def test_fft_surface_mtf_independent_meridional_frequency_scales():
    source = Path(__file__).resolve().parents[1] / 'outputs/runs/surface_mtf509_pupil_3517781fe1'
    if not source.is_dir():
        pytest.skip('Requires preserved native509 independent pupil evidence')

    async def work(e):
        conditions = dict(source=str(source), wavelength=1, sampling=256,
            hypothesis='Independent sagittal/tangential marginal-ray F numbers set the two frequency scales',
            tolerance=.005, reference='509 complex pupil; only frequency scaling changes')
        (e.folder/'conditions.json').write_text(json.dumps(conditions, indent=2), encoding='utf-8')
        await e.call('open_lens', dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline = await e.call('get_surfaces')
        settings = await e.call('get_system_settings')
        records = json.loads((source/'autocorrelation.json').read_text(encoding='utf-8'))
        output = []
        wave = settings['wavelengths'][0]['wavelength_um']*.001
        for record in records:
            field = record['field']
            seed = await e.finish(await e.call('run_batch_ray_trace', dict(request=dict(rays=[
                dict(hx=0, hy=0 if field == 1 else 1, px=px, py=py, wavelength=1)
                for px, py in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]]))))
            fs, ft = real_f_numbers(seed['rows'])
            pupil = np.zeros((256,256), dtype=complex)
            for entry in json.loads((source/f'field{field}-rays.json').read_text(encoding='utf-8')):
                row = entry['ray']
                if not row['error_code'] and not row['vignette_code'] and row.get('opd') is not None:
                    pupil[entry['iy'],entry['ix']] = np.sqrt(row['intensity'])*np.exp(2j*np.pi*row['opd'])
            acf = pupil_autocorrelation(pupil)
            x = (np.arange(512)-256)/(wave*fs*254)
            y = (np.arange(512)-256)/(wave*ft*254)
            points = []
            for old in record['comparisons']['paraxial']['points']:
                reference = bilinear(x,y,acf,old['fx'],old['fy'])
                points.append(dict(fx=old['fx'],fy=old['fy'],native=old['native'],
                    reference=reference,error=abs(reference-old['native'])))
            task = await e.call('get_task_status',dict(task_id=seed['task']['task_id']))
            assert task['state'] == 'succeeded' and not task.get('cleanup_warnings')
            output.append(dict(field=field,sagittal_f_number=fs,tangential_f_number=ft,
                ray_reference=seed,points=points,maximum_error=max(p['error'] for p in points)))
            (e.folder/'anisotropic.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces') == baseline
        assert await e.call('get_system_settings') == settings
    asyncio.run(execute('surface_mtf510_anisotropic',work))
