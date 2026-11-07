"""Relative optical thickness retains its original primary wavelength in copies."""
import asyncio
from pathlib import Path
import pytest
from support.native import execute
from support.thin_film import single_layer,bk7_index


@pytest.mark.zemax
def test_relative_film_primary_preserved():
    resource=Path.home()/'Documents/Zemax/Coatings/MCP058_relative.DAT'
    coating='MATE MCP058_N138\n0.4 1.38 0\n0.8 1.38 0\nCOAT MCP058_REL\nMCP058_N138 .25 0 0\n'
    resource.write_text(coating,encoding='ascii')
    async def work(e):
        (e.folder/resource.name).write_text(coating,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name),wavelengths=[dict(wavelength_um=.45),dict(wavelength_um=.55),dict(wavelength_um=.7)],primary_wavelength=2)))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating='MCP058_REL',replace_solves=True)]))
        baseline=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces',dict(start=0,count=3))
        for metric in ['phase','retardance','diattenuation','reflection','transmission','absorption']:
            for axis in ['angle','wavelength','outside']:
                q=dict(kind=metric+'_vs_'+('angle' if axis=='angle' else 'wavelength'),surface=1,**(dict(wavelength=2,minimum_angle=0,maximum_angle=70)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.6 if axis=='outside'else .45,maximum_wavelength_um=.7)))
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                if axis!='angle':assert result['task']['settings']['evaluation_conditions']['primary_wavelength_um']==.55
                curve=result['series'][0]
                for i in range(0,len(curve['x']),max(1,len(curve['x'])//9)):
                    x=curve['x'][i];angle=x if axis=='angle'else 45;wave=.55 if axis=='angle'else x
                    reference=single_layer(angle,wave,bk7_index(wave),thickness_um=.25*.55/1.38)[metric]
                    for channel,(actual,want) in enumerate(zip(curve['y'][i],reference)):
                        delta=(actual-want+180)%360-180 if metric in ['phase','retardance']else actual-want
                        e.check(f'relative {metric}/{axis} {x} channel {channel}',delta,0,atol=1e-4 if metric in ['phase','retardance']else 1e-6,rtol=0)
                task=result['task']['task_id']
                assert (await e.call('get_task_status',dict(task_id=task)))['close_attempted']
                await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'relative_{metric}_{axis}.png'))))
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
        saved=str(e.folder/'relative_saved.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        assert (await e.call('get_system_settings'))['wavelengths']==baseline['wavelengths']
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
    try:asyncio.run(execute('coating_relative058',work))
    finally:resource.unlink(missing_ok=True)
