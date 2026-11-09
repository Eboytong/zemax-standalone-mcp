"""Selectable native-index derivative, analytic and controlled table references."""
import asyncio
import math
import runpy
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import glass_coefficients,sellmeier


@pytest.mark.zemax
def test_selected_derivative_reference_and_lifecycle():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces',dict(start=0,count=100))
        merit=await e.call('get_merit_function')
        request=dict(kind='dispersion_vs_wavelength',method='finite_difference',catalog='SCHOTT',
            glasses=['N-BK7','N-F2'],minimum_wavelength_um=.4,maximum_wavelength_um=.8,samples=101,
            minimum_dispersion=-.5,maximum_dispersion=-.001)
        result=await e.finish(await e.call('run_analysis',dict(request=request)))
        assert result['computation_method']=='finite_difference_of_native_ILDE_GetIndex'
        assert result['restoration']['analysis_copy_closed']
        assert result['actual_settings']['analysis_system_id']!=result['actual_settings']['source_system_id']
        curve=result['series'][0]
        assert curve['labels']==request['glasses'] and curve['value_units']==['1/micrometer']*2
        for w,values in zip(curve['x'],curve['y'],strict=True):
            for material,value in zip(request['glasses'],values,strict=True):
                c=glass_coefficients(material)
                expected=-w/sellmeier(w,c)*sum(c[i]*c[i+1]/(w*w-c[i+1])**2 for i in (0,2,4))
                e.check(f'{material} analytic derivative {w}',value,expected,atol=5.1e-8,rtol=0)
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=19,count=4))
        assert page['series'][0]['y']==curve['y'][19:23]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'derivative.png'))))
        records=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/probes/MA-01/athermal_missing_data.py'))['catalog_records'](
            Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF')
        from tests.support.athermal_reference import system_relative_index
        four=request|dict(glasses=['N-BK7','N-F2','N-SF6','N-SF10'],samples=7,
            use_temperature_pressure=True,temperature_c=30,pressure_atm=.8)
        thermal=await e.finish(await e.call('run_analysis',dict(request=four)))
        for w,values in zip(thermal['series'][0]['x'],thermal['series'][0]['y'],strict=True):
            for material,value in zip(four['glasses'],values,strict=True):
                f=lambda x:system_relative_index(records[material],x,30,.8)
                # Independent sixth-order, larger-step thermal reference.
                h=.0003
                expected=math.fsum(a*f(w+b*h) for a,b in [(1,-3),(-9,-2),(45,-1),(-45,1),(9,2),(-1,3)])/(-60*h)
                e.check(f'thermal derivative {material} {w}',value,expected,atol=5.1e-8,rtol=0)
        automatic=await e.finish(await e.call('run_analysis',dict(request=request|dict(
            minimum_wavelength_um=0,maximum_wavelength_um=0,samples=9))))
        assert automatic['invalid_point_count']==1
        for w,values in zip(automatic['series'][0]['x'],automatic['series'][0]['y'],strict=True):
            for material,value in zip(request['glasses'],values,strict=True):
                if value is None:continue
                c=glass_coefficients(material)
                expected=-w/sellmeier(w,c)*sum(c[i]*c[i+1]/(w*w-c[i+1])**2 for i in (0,2,4))
                e.check(f'boundary derivative {material} {w}',value,expected,atol=5.1e-8,rtol=0)
        table=Path.home()/'Documents/Zemax/Glasscat'/('MD'+e.folder.name[-8:]+'.ZTG')
        assert not table.exists()
        try:
            table.write_text('! Controlled linear index, derivative -0.1 /um\n'+'\n'.join(f'{w:.8f} {1.54-.1*w:.10f}' for w in [.4,.5,.6,.7,.8]))
            linear=await e.finish(await e.call('run_analysis',dict(request=request|dict(glasses=[table.name],samples=9))))
            for w,values in zip(linear['series'][0]['x'],linear['series'][0]['y'],strict=True):
                e.check(f'linear table derivative {w}',values[0],-.1,atol=5.1e-8,rtol=0)
        finally:table.unlink(missing_ok=True)
        await e.call('save_lens_as',dict(path=str(e.folder/'derivative-baseline.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'derivative-baseline.zos')))
        again=await e.finish(await e.call('run_analysis',dict(request=four)))
        assert again['series']==thermal['series']
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
    asyncio.run(execute('material_derivative_selected',work))
