"""Prepared native catalog identity and internal-transmission thickness reference."""
import asyncio
import pytest
from pathlib import Path
from support.native import execute

@pytest.mark.zemax
def test_material_properties_and_transmission_native():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        baseline=await e.call('get_system_settings')
        data=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT.AGF',material='N-BK7')))
        assert data['coefficients'] and data['internal_transmission']
        lines=(Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig').splitlines()
        start=next(i for i,line in enumerate(lines) if line.split()[:2]==['NM','N-BK7'])
        reference=next([float(v) for v in line.split()[1:7]] for line in lines[start+1:] if line.startswith('CD '))
        assert len(data['coefficients'])==6
        for coefficient,expected in zip(data['coefficients'],reference):
            e.check('catalog AGF '+coefficient['name'],coefficient['value'],expected,atol=1e-12,rtol=1e-12)
        assert (await e.call('get_system_settings'))==baseline
        q=dict(kind='internal_transmission_vs_wavelength',catalog='SCHOTT.AGF',glasses=['N-BK7'],thickness_mm=10)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['series'] and result['task']['settings']['native']['Thickness']==10
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=5))
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'transmission.png'))))
    asyncio.run(execute('materials025_properties',work))

@pytest.mark.zemax
def test_material_thickness_beer_lambert():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        table=(await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7'))))['internal_transmission']
        reference=next(p for p in table if 0<p['transmission']<1 and p['thickness_mm']>0)
        thickness=reference['thickness_mm']*.5
        q=dict(kind='internal_transmission_vs_wavelength',catalog='SCHOTT',glasses=['N-BK7'],minimum_wavelength_um=reference['wavelength_um'],maximum_wavelength_um=reference['wavelength_um']+.001,thickness_mm=thickness)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        curve=result['series'][0]
        e.check('first wavelength matches input table',curve['x'][0],reference['wavelength_um'],atol=1e-10,rtol=1e-10)
        e.check('internal transmission power law',curve['y'][0][0],reference['transmission']**.5,atol=1e-6,rtol=1e-5)
    asyncio.run(execute('materials025_thickness',work))
