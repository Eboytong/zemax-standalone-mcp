"""Serial runtime settings and result discovery on the installed hologram sample."""
import asyncio
import math
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_diff_efficiency_hologram_runtime():
    async def work(e):
        path=Path(r'C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Samples\Sequential\Diffractive components\Transmission hologram.zos')
        await e.call('open_lens',dict(path=str(path)))
        await e.call('update_system_settings',dict(settings=dict(field_type='Angle')))
        # Manual pp.255-257: enable volume parameters before assigning the emulsion.
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={13:1},replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={14:.01,15:1,16:1,17:1.5,18:.02},replace_solves=True)]))
        before=await e.call('get_surfaces',dict(start=0,count=20))
        settings=await e.call('get_system_settings')
        results={}
        for kind in ['diff_efficiency_2d','diff_efficiency_angular','diff_efficiency_chromatic']:
            bounds={}
            if kind!='diff_efficiency_chromatic':bounds.update(min_angle=-5,max_angle=5)
            if kind!='diff_efficiency_angular':bounds.update(min_wavelength=.45,max_wavelength=.65)
            response=await e.call('run_analysis',dict(request=dict(kind=kind,surface=1,**bounds)))
            result=await e.finish(response)
            results[kind]=result
            assert result.get('series') or result.get('grids'),result
            terminal=await e.call('get_task_status',dict(task_id=response['task_id']))
            assert terminal['close_attempted'] is True
            task=response['task_id']
            if kind=='diff_efficiency_2d':
                grid=result['grids'][0]
                assert (grid['nx'],grid['ny'])==(64,64)
                assert (grid['x_unit'],grid['y_unit'])==('degrees','micrometers')
                await e.call('get_task_result',dict(task_id=task,grid=0,x_start=2,y_start=1,width=3,height=2))
            else:
                series=result['series'][0]
                # Installed S_65 returns 64 samples, excluding the upper bound.
                assert len(series['x'])==64
                assert series['y_unit']=='dimensionless'
                await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'{kind}.png'))))
        grid=results['diff_efficiency_2d']['grids'][0]
        angular=results['diff_efficiency_angular']['series'][0]
        chromatic=results['diff_efficiency_chromatic']['series'][0]
        # At normal incidence the sample's coincident construction directions give
        # Kogelnik eta=sin(pi*dn*d/lambda)^2; d=.01 mm=10 um, no Fresnel correction.
        for i,(wavelength,row) in enumerate(zip(chromatic['x'],chromatic['y'])):
            expected=math.sin(math.pi*.02*10/wavelength)**2
            e.check(f'normal Kogelnik wavelength {wavelength}',row[0],expected,atol=1e-8,rtol=1e-7)
            if i<64:e.check(f'grid wavelength row {i}',grid['values'][i][32],row[0])
        for i,row in enumerate(angular['y'][:64]):
            e.check(f'grid angle column {i}',grid['values'][32][i],row[0])
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_surfaces',dict(start=0,count=20))==before
    asyncio.run(execute('diff_efficiency056_probe',work))
