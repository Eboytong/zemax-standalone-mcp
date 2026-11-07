"""Independent real-ray OPD comparison for nonzero Cooke pupil phase."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_interferogram_independent_opd():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(intensity_atol=.005,
            reference='Independent batch-ray OPD in waves; equal-amplitude cosine interference',
            signs='Record both beam-phase sign conventions before assigning native beam order'),indent=2),encoding='utf-8')
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        points=[(x,y) for y in range(7,57,6) for x in range(7,57,6) if ((x-31)/31)**2+((y-31)/31)**2<.85**2]
        rays=[dict(hx=0,hy=0,px=(x-31)/31,py=(y-31)/31,wavelength=1) for x,y in points]
        traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
        assert len(traced['rows'])==len(points)
        assert all(r['error_code']==0 and r['opd'] is not None for r in traced['rows'])
        opd=np.asarray([r['opd'] for r in traced['rows']])
        records=[]
        for patch in [dict(),dict(scale_factor=2),dict(x_tilt=1.3,y_tilt=.7),
                      dict(beam_1='Configuration_1',beam_2='Reference',x_tilt=1.3,y_tilt=.7)]:
            request=dict(kind='interferogram',sampling='S_64x64',use_exit_pupil=False)|patch
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            values=result['grids'][0]['values']
            actual=np.asarray([values[y][x] for x,y in points])
            tilt=np.asarray([.5*(patch.get('x_tilt',0)*(x-31)/31+patch.get('y_tilt',0)*(y-31)/31) for x,y in points])
            comparisons=[]
            for sign in [-1,1]:
                expected=(1+np.cos(2*np.pi*(sign*patch.get('scale_factor',1)*opd+tilt)))/2
                comparisons.append(dict(sign=sign,max_error=float(abs(actual-expected).max()),expected=expected.tolist()))
            records.append(dict(request=request,points=points,opd=opd.tolist(),actual=actual.tolist(),comparisons=comparisons,result=result))
            (e.folder/'comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            sign=1 if patch.get('beam_1')=='Configuration_1' else -1
            comparison=next(c for c in comparisons if c['sign']==sign)
            e.check(str(patch)+' independent OPD intensity',comparison['max_error'],0,atol=.005,rtol=0)
    asyncio.run(execute('interferogram304_opd',work))


@pytest.mark.zemax
@pytest.mark.parametrize('mirror',[True,False])
def test_interferogram_two_configurations_and_opl(mirror):
    async def work(e):
        delta=.00014
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=.005,
            model='parabolic mirror' if mirror else 'ideal paraxial lens',
            image_shift_mm=-delta if mirror else delta,wavelength_um=.56,
            chief_path_2_minus_1_waves=.25,
            reference='cosine of batch OPD1-OPD2 plus chief geometric path2-path1 and tilt'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.56)],fields=[dict(x=0,y=0)])))
        surface=(dict(radius=-200,conic=-1,material='MIRROR',thickness=-100) if mirror else
                 dict(surface_type='Paraxial',parameters={'1':100},thickness=100))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,semi_diameter=5,is_stop=True,replace_solves=True)|surface]))
        thickness=-100 if mirror else 100
        cells=[dict(configuration=1,value=thickness),
               dict(configuration=2,value=thickness+(-delta if mirror else delta))]
        await e.call('update_configurations',dict(request=dict(
            actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='THIC',parameters={'1':1},cells=cells)])))
        points=[(x,y) for y in [13,22,31,40,49] for x in [13,22,31,40,49] if (x-31)**2+(y-31)**2<25**2]
        rays=[dict(hx=0,hy=0,px=(x-31)/31,py=(y-31)/31,wavelength=1) for x,y in points]
        opds=[]
        for configuration in [1,2]:
            await e.call('set_configuration',dict(configuration=configuration))
            traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,opd=True))))
            assert all(r['error_code']==0 for r in traced['rows'])
            opds.append(np.asarray([r['opd'] for r in traced['rows']]))
        await e.call('set_configuration',dict(configuration=1))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');mce=await e.call('get_configurations',dict(request={}))
        records=[]
        for consider,swapped in [(False,False),(True,False),(True,True)]:
            q=dict(kind='interferogram',beam_1='Configuration_2' if swapped else 'Configuration_1',
                   beam_2='Configuration_1' if swapped else 'Configuration_2',
                   use_exit_pupil=False,consider_opl=consider,x_tilt=1.3,y_tilt=.7)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            actual=np.asarray([result['grids'][0]['values'][y][x] for x,y in points])
            tilt=np.asarray([.5*(1.3*(x-31)/31+.7*(y-31)/31) for x,y in points])
            sign=-1 if swapped else 1
            expected=(1+np.cos(2*np.pi*(sign*(opds[0]-opds[1]+(.25 if consider else 0))+tilt)))/2
            records.append(dict(request=q,points=points,opds=[a.tolist() for a in opds],expected=expected.tolist(),actual=actual.tolist(),result=result))
            (e.folder/'comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            e.check(f'two configurations OPL {consider} swapped {swapped}',float(abs(actual-expected).max()),0,atol=.005,rtol=0)
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_configurations',dict(request={}))==mce
    asyncio.run(execute('interferogram308_mirror' if mirror else 'interferogram308_paraxial',work))
