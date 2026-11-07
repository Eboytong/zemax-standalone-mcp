"""Native spread/PSF outlets for matching sampling, orientation and integration."""
import asyncio
import json
from pathlib import Path

import pytest
import numpy as np
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('field',[1,3])
def test_fft_spread_psf_integration_outlets(field):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            lsf_esf_atol=.005,complex_intensity_atol=2e-6,phase_atol_degrees=.005,
            phase_minimum_intensity=1e-4,
            reference='same pupil64 full internal128 PSF; orthogonal marginal and midpoint cumulative; native FFT knots every second text sample'),indent=2),encoding='utf-8')
        records=[]
        requests=[dict(kind='fft_psf',sampling='S_64x64',image_sampling='S_256x256')]
        requests += [dict(kind='fft_line_edge_spread',spread=spread,data_type=kind)
                     for spread in ['Line','Edge'] for kind in ['X_Linear','Y_Linear']]
        requests += [dict(kind='fft_line_edge_spread',spread='Line',data_type=kind,use_coherent_psf=True)
                     for kind in ['X_Linear','X_Logarithmic','X_Phase','X_RealPart','X_ImaginaryPart']]
        for request in requests:
            request.update(field=field,wavelength=1)
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
        g=records[0]['result']['grids'][0];psf=np.asarray(g['values'])
        for orientation,axis,line_index,edge_index in [('X',1,1,3),('Y',0,2,4)]:
            marginal=psf.sum(axis=axis)
            coordinates=g['min_y' if axis==1 else 'min_x']+np.arange(len(marginal))*g['dy' if axis==1 else 'dx']
            line=records[line_index]['result']['series'][0];edge=records[edge_index]['result']['series'][0]
            actual_line=np.interp(coordinates,line['x'],np.asarray(line['y'])[:,0])
            actual_edge=np.interp(coordinates,edge['x'],np.asarray(edge['y'])[:,0])
            expected_line=marginal/marginal.max()
            expected_edge=(np.cumsum(marginal)-.5*marginal)/marginal.sum()
            e.check(orientation+' PSF marginal',float(abs(actual_line-expected_line).max()),0,atol=.005,rtol=0)
            e.check(orientation+' PSF midpoint cumulative',float(abs(actual_edge-expected_edge).max()),0,atol=.005,rtol=0)
        intensity,log,phase,real,imag=[np.asarray(r['result']['series'][0]['y'])[:,0] for r in records[5:]]
        np.testing.assert_array_equal(intensity,log)
        knots=np.arange(0,len(intensity),2);amplitude=(real+1j*imag)[knots]
        e.check('coherent original knots amplitude squared',float(abs(intensity[knots]-abs(amplitude)**2).max()),0,atol=2e-6,rtol=0)
        valid=intensity[knots]>1e-4
        error=(np.angle(amplitude,deg=True)-phase[knots]+180)%360-180
        e.check('coherent original knots phase degrees',float(abs(error[valid]).max()),0,atol=.005,rtol=0)
    asyncio.run(execute('fft_spread315',work))
