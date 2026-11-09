"""Selected formal index curves, independent dispersion and copy ownership."""
import asyncio
import runpy
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import glass_coefficients,sellmeier


@pytest.mark.zemax
def test_selected_dispersion_curves_reference_and_copy_lifecycle():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces',dict(start=0,count=100))
        merit=await e.call('get_merit_function')
        request=dict(kind='dispersion_diagram',method='index',catalog='SCHOTT',glasses=['N-BK7','N-F2'],
            minimum_wavelength_um=.4,maximum_wavelength_um=.8,samples=101,minimum_index=1.45,maximum_index=1.7)
        result=await e.finish(await e.call('run_analysis',dict(request=request)))
        assert result['computation_method']=='native_ILDE_GetIndex'
        assert result['restoration']['analysis_copy_closed']
        curve=result['series'][0]
        assert curve['labels']==request['glasses'] and len(curve['x'])==101
        assert result['actual_settings']['analysis_system_id']!=result['actual_settings']['source_system_id']
        for col,material in enumerate(request['glasses']):
            coefficients=glass_coefficients(material)
            for w,values in zip(curve['x'],curve['y'],strict=True):
                e.check(f'{material} n({w})',values[col],sellmeier(w,coefficients),atol=1e-12,rtol=0)
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=19,count=4))
        assert page['series'][0]['y']==curve['y'][19:23]
        image=await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'dispersion.png'))))
        assert image['plotting_settings']['y_limits']==[1.45,1.7]
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=100))==surfaces
        assert await e.call('get_merit_function')==merit
        native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='dispersion_diagram'))))
        native_curve=native['series'][0]
        selected=await e.finish(await e.call('run_analysis',dict(request=request|dict(
            glasses=['BK7G18'],minimum_wavelength_um=native_curve['x'][0],
            maximum_wavelength_um=native_curve['x'][-1],samples=len(native_curve['x'])))))
        col=native_curve['labels'].index('BK7G18')
        for i,values in enumerate(selected['series'][0]['y']):
            e.check(f'default report node {i}',values[0],native_curve['y'][i][col],atol=5.1e-8,rtol=0)
        records=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/probes/MA-01/athermal_missing_data.py'))['catalog_records'](
            Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF')
        from tests.support.athermal_reference import system_relative_index
        four=request|dict(glasses=['N-BK7','N-F2','N-SF6','N-SF10'],samples=7,
            use_temperature_pressure=True,temperature_c=30,pressure_atm=.8)
        thermal=await e.finish(await e.call('run_analysis',dict(request=four)))
        assert thermal['environment']['temperature_c']==30 and thermal['environment']['pressure_atm']==.8
        for wavelength,values in zip(thermal['series'][0]['x'],thermal['series'][0]['y'],strict=True):
            for material,value in zip(four['glasses'],values,strict=True):
                expected=system_relative_index(records[material],wavelength,30,.8)
                e.check(f'thermal {material} n({wavelength})',value,expected,atol=1e-12,rtol=0)
        automatic=await e.finish(await e.call('run_analysis',dict(request=request|dict(
            minimum_wavelength_um=0,maximum_wavelength_um=0,samples=9))))
        bounds=automatic['actual_settings']['resources']
        assert automatic['actual_settings']['automatic_wavelength_range']
        assert automatic['series'][0]['x'][0]==min(v['minimum_wavelength_um'] for v in bounds)
        assert automatic['series'][0]['x'][-1]==max(v['maximum_wavelength_um'] for v in bounds)
        for w,values in zip(automatic['series'][0]['x'],automatic['series'][0]['y'],strict=True):
            for material,value,resource in zip(request['glasses'],values,bounds,strict=True):
                if resource['minimum_wavelength_um']<=w<=resource['maximum_wavelength_um']:
                    e.check(f'auto range {material} n({w})',value,sellmeier(w,glass_coefficients(material)),atol=1e-12,rtol=0)
                else:
                    assert value is None
        assert automatic['invalid_point_count']==1
        table=await e.finish(await e.call('run_analysis',dict(request=request|dict(
            glasses=['TABLETEST.ZTG'],samples=101))))
        source=Path.home()/'Documents/Zemax/Glasscat/TABLETEST.ZTG'
        nodes=[tuple(map(float,line.split()[:2])) for line in source.read_text().splitlines()
               if line.strip() and not line.strip().startswith(('!','DENSITY'))]
        for (wave,values),(expected_wave,expected_index) in zip(zip(table['series'][0]['x'],table['series'][0]['y']),nodes,strict=True):
            e.check(f'table wavelength {wave}',wave,expected_wave,atol=1e-12,rtol=0)
            e.check(f'table index {wave}',values[0],expected_index,atol=1e-12,rtol=0)
        await e.call('save_lens_as',dict(path=str(e.folder/'index-baseline.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'index-baseline.zos')))
        again=await e.finish(await e.call('run_analysis',dict(request=four)))
        assert again['series']==thermal['series']
        missing=await e.call('run_analysis',dict(request=request|dict(glasses=['MCP_MISSING_MATERIAL'])),okay=False)
        assert missing['error']['code']=='INVALID_RESOURCE'
        invalid=await e.call('run_analysis',dict(request=request|dict(minimum_wavelength_um=.01)),okay=False)
        assert invalid['error']['code']=='WAVELENGTH_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=request|dict(samples=2001)))
        state=await e.call('cancel_task',dict(task_id=task['task_id']))
        while state['state'] not in {'cancelled','succeeded','failed'}:
            await asyncio.sleep(.02)
            state=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert state['state']=='cancelled'
        cancelled=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert cancelled['restoration']['analysis_copy_closed']
        reused=await e.finish(await e.call('run_analysis',dict(request=four)))
        assert reused['series']==thermal['series']
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=100))==surfaces
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('material_index_selected',work))
