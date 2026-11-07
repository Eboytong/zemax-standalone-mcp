"""Controlled ideal mirror fringes, pupil mask and discrete coordinate convention."""
import asyncio
import json

import pytest
import numpy as np
from tests.support.native import execute


@pytest.mark.zemax
def test_interferogram_controlled_fringe_outlets():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            intensity_absolute_tolerance=.005,period_relative_tolerance=.01,
            reference='I=(1+cos(pi*(Xtilt*px+Ytilt*py)))/2 inside circular pupil',
            coordinates='px=(column-31)/31; py=(row-31)/31; 64 samples',
            outside='Reference/configuration fills 1; identical configuration beams fill 0'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,
            material='MIRROR',thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for patch in [dict(),dict(x_tilt=2),dict(y_tilt=3),dict(x_tilt=2,y_tilt=3),
                      dict(beam_1='Configuration_1',beam_2='Configuration_1',x_tilt=2)]:
            request=dict(kind='interferogram',sampling='S_64x64',use_exit_pupil=False)|patch
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            y,x=np.indices((64,64));px=(x-31)/31;py=(y-31)/31
            mask=px**2+py**2<=1+1e-14
            expected=(1+np.cos(np.pi*(request.get('x_tilt',0)*px+request.get('y_tilt',0)*py)))/2
            expected[~mask]=0 if request.get('beam_1')=='Configuration_1' else 1
            actual=np.asarray(result['grids'][0]['values'])
            e.check(str(patch)+' maximum fringe intensity error',float(abs(actual-expected).max()),0,atol=.005,rtol=0)
            np.testing.assert_allclose(actual,expected,atol=.005,rtol=0)
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('interferogram301',work))
