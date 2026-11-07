"""Bare ideal-mirror phase channels and inactive sequential reverse option."""
import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_mirror_phase_and_reverse_activity():
    resource=Path.home()/'Documents/Zemax/Coatings/MCP058_mirror.DAT'
    coating='IDEAL2 MCP058_IDEAL -1 0 0 0 1 0 0 0 1\n'
    resource.write_text(coating,encoding='ascii')
    async def work(e):
        (e.folder/resource.name).write_text(coating,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(files=dict(coating_file=resource.name),wavelengths=[dict(wavelength_um=.45),dict(wavelength_um=.55),dict(wavelength_um=.7)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='MIRROR',coating='MCP058_IDEAL',thickness=-10,replace_solves=True)]))
        before=await e.call('get_surfaces',dict(start=0,count=3))
        for axis in ['angle','wavelength']:
            q=dict(kind='phase_vs_'+axis,surface=1,**(dict(wavelength=2,minimum_angle=0,maximum_angle=70)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)))
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            curve=result['series'][0]
            assert curve['labels']==['S reflection phase','P reflection phase']
            for i in range(0,len(curve['x']),max(1,len(curve['x'])//9)):
                for channel,want in enumerate([180,0]):
                    delta=(curve['y'][i][channel]-want+180)%360-180
                    e.check(f'ideal mirror {axis} {i} channel {channel}',delta,0,atol=1e-8,rtol=0)
            task=result['task']['task_id']
            assert (await e.call('get_task_status',dict(task_id=task)))['close_attempted']
            await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'mirror_{axis}.png'))))
        rejected=await e.call('run_analysis',dict(request=dict(kind='phase_vs_angle',surface=1,reverse_direction=True)),okay=False)
        assert rejected['error']['code']=='INACTIVE_SETTING'
        assert await e.call('get_surfaces',dict(start=0,count=3))==before
    try:asyncio.run(execute('coating_mirror058',work))
    finally:resource.unlink(missing_ok=True)
