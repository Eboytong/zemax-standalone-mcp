"""Absolute-thickness film against independent complex-amplitude summation."""
import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.thin_film import single_layer,bk7_index


@pytest.mark.zemax
def test_absolute_film_polarization_reference():
    resource=Path.home()/'Documents/Zemax/Coatings/MCP057_reference.DAT'
    coating='MATE MCP057_N138\n0.4 1.38 0\n0.8 1.38 0\nCOAT MCP057_FILM\nMCP057_N138 .1 1 0\n'
    resource.write_text(coating,encoding='ascii')
    async def work(e):
        (e.folder/resource.name).write_text(coating,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name),wavelengths=[dict(wavelength_um=.45),dict(wavelength_um=.55),dict(wavelength_um=.7)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating='MCP057_FILM',replace_solves=True)]))
        failures=[]
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces',dict(start=0,count=3))
        for metric in ['phase','retardance','diattenuation','reflection','transmission','absorption']:
            for axis,number in [('angle',1),('angle',2),('angle',3),('wavelength',None)]:
                q=dict(kind=metric+'_vs_'+axis,surface=1,**(dict(wavelength=number,minimum_angle=0,maximum_angle=70)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)))
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                curve=result['series'][0]
                for i in range(0,len(curve['x']),max(1,len(curve['x'])//9)):
                    x=curve['x'][i];angle=x if axis=='angle'else 45;wave=[.45,.55,.7][number-1] if axis=='angle'else x
                    reference=single_layer(angle,wave,bk7_index(wave))[metric]
                    for channel,(actual,expected) in enumerate(zip(curve['y'][i],reference)):
                        delta=(actual-expected+180)%360-180 if metric in ['phase','retardance']else actual-expected
                        try:e.check(f'{metric}/{axis}/{number} {x} channel {channel}',delta,0,atol=1e-4 if metric in ['phase','retardance']else 1e-6,rtol=0)
                        except AssertionError:failures.append(e.checks[-1])
                terminal=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert terminal['close_attempted'] is True
                task=result['task']['task_id']
                await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'{metric}_{axis}_{number}.png'))))
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
        assert not failures,failures[:5]
    try:asyncio.run(execute('coating_reference057',work))
    finally:resource.unlink(missing_ok=True)
