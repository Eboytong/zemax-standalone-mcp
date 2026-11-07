"""Evaluate documented FFT pupil stretching against retained coherent spread data."""
import json
from pathlib import Path

import numpy as np


def run():
    output=dict(hypothesis='FFT PSF documented sqrt(N/32) pupil stretching also determines coherent line pupil nodes',
        source_definition='Installed manual535 pages777/778; zero-based PDF indices',
        tolerance=.005, native_execution=False, records=[],
        limitations='Existing native independent-ray phase interpolated in entrance coordinates; dedicated stretched-node rays still required')
    for size,folder in [(64,'fft_spread513_guard_psf_auto_64_ff55d8cad8'),
                        (128,'fft_spread513_guard_psf_auto_128_8ffa9a3470')]:
        source=Path('outputs/runs')/folder
        records=json.loads((source/'comparisons.json').read_text(encoding='utf-8'))
        for record in records:
            old=np.asarray(record['pupil_real'])+1j*np.asarray(record['pupil_imag'])
            valid=abs(old)>0
            old_positions=np.asarray(record['pupil_positions_mm'])
            stretch=np.sqrt(size/32)
            positions=5*(np.arange(size)-size//2)/(size//2-1)*stretch
            inside=abs(positions)<5
            phase=np.interp(positions[inside],old_positions[valid],np.unwrap(np.angle(old[valid])))
            amp=np.interp(positions[inside],old_positions[valid],abs(old[valid]))
            pupil=np.zeros(size,dtype=complex);pupil[inside]=amp*np.exp(1j*phase)
            x=np.asarray(record['positions_um']);actual=np.asarray(record['actual'])
            amplitude=np.exp(-2j*np.pi*x[:,None]*positions[None,:]/(.55*abs(record['thickness'])))@pupil
            expected=abs(amplitude)**2;expected/=expected.max()
            output['records'].append(dict(source=str(source),size=size,thickness=record['thickness'],
                stretch=float(stretch),nonzero_nodes=int(inside.sum()),
                max_error=float(abs(actual-expected).max()),positions_um=x.tolist(),
                expected=expected.tolist(),actual=actual.tolist()))
    Path('verification/development/CV-01/offline544-stretched.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:r[k]for k in ['size','thickness','nonzero_nodes','max_error']}for r in output['records']]))


if __name__=='__main__':run()
