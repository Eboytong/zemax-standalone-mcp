"""Controlled ideal mirror knife-edge output and complementary orientations."""
import asyncio
import json

import pytest
import numpy as np

from support.native import execute
from support.foucault_reference import pupil, shadowgram


@pytest.mark.zemax
def test_foucault_ideal_mirror_outlets():
    async def work(e):
        tolerance = dict(atol=1e-7, rtol=1e-7)
        (e.folder/'reference-conditions.json').write_text(json.dumps(dict(
            tolerance=tolerance, sampling=64, padded_size=128,
            pupil_center=[32,32], pupil_radius=31, central_knife_weight=.5,
            normalization='maximum cropped intensity',
            reference='independent scalar FFT, focal knife mask, inverse FFT'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=-200,conic=-1,
            material='MIRROR',thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for knife,position in [('Horiz_Above',0),('Horiz_Below',0),('Vert_Right',0),('Vert_Left',0),
                               ('Horiz_Above',-1000),('Horiz_Above',1000)]:
            request=dict(kind='foucault',sampling='S_64x64',knife=knife,y_position=position)
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            actual=np.asarray(result['grids'][0]['values'])
            expected=shadowgram(knife) if position==0 else pupil() if position>0 else np.zeros((64,64))
            error=abs(actual-expected)
            e.check(f'{knife} {position} max pixel error',float(error.max()),0,
                    atol=tolerance['atol']+tolerance['rtol']*float(abs(expected).max()),rtol=0)
            np.testing.assert_allclose(actual,expected,**tolerance)
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['state']=='succeeded' and task['close_attempted']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('foucault297',work))
