"""Phase, retardance and diattenuation against the installed native coating model."""
import asyncio
import math
from pathlib import Path
import pytest
from tests.support.native import execute

COATING='''MATE MCP055_N138
0.4 1.38 0
0.8 1.38 0
COAT MCP055_FILM
MCP055_N138 .25
'''


@pytest.mark.zemax
def test_coating_polarization_channels_and_wavelength_copy():
    resource=Path.home()/'Documents/Zemax/Coatings'/'MCP055_acceptance.DAT'
    resource.write_text(COATING,encoding='ascii')
    async def work(e):
        (e.folder/'MCP055_acceptance.DAT').write_text(COATING,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name),wavelengths=[dict(wavelength_um=.45),dict(wavelength_um=.55),dict(wavelength_um=.7)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating='MCP055_FILM',replace_solves=True)]))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces',dict(start=0,count=3))
        for metric in ['phase','retardance','diattenuation']:
            for axis in ['angle','wavelength']:
                request=dict(kind=metric+'_vs_'+axis,surface=1,**(dict(wavelength=2,minimum_angle=0,maximum_angle=70)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)))
                result=await e.finish(await e.call('run_analysis',dict(request=request)))
                assert result['series']
                terminal=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert terminal['close_attempted'] is True
                main=result['series'][0]
                assert len(main['labels'])==2 and all(len(row)==2 for row in main['y'])
                assert main['labels_source'].startswith('official analysis definition')
                assert main['x_unit']==('degrees'if axis=='angle'else'micrometers')
                assert main['y_unit']==('dimensionless'if metric=='diattenuation'else'degrees')
                if axis=='wavelength':
                    assert result['actual_wavelength_scan_um']==[.45,.7]
                    settings=result['task']['settings']
                    assert settings['evaluation_conditions']['source_system_id']>0
                    assert settings['evaluation_conditions']['wavelength_scan_system_id']!=settings['evaluation_conditions']['source_system_id']
                task=result['task']['task_id']
                await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'{metric}_{axis}.png'))))
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
    try:asyncio.run(execute('coating_polarization055',work))
    finally:resource.unlink(missing_ok=True)
