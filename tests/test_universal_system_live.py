import asyncio
import pytest
from support.native import execute

@pytest.mark.zemax
def test_universal_system_settings():
    async def work(e):
        await e.model();await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=2,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(aperture_options=dict(apodization_type='Gaussian'),fields=[dict(x=0,y=0),dict(x=1,y=2)],wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        for parameter,low,high,unit in [('XField',-1,1,'degrees'),('YField',-2,2,'degrees'),('Wavelength',.45,.65,'micrometers'),('Temperature',10,30,'Celsius'),('Pressure',.8,1.2,'atmospheres'),('Aperture',4,6,'Millimeters'),('ApodizationFactor',1,3,'dimensionless')]:
            q=dict(kind='universal_plot_1d',category='System',parameter=parameter,start=low,stop=high,samples=3,first_surface=1,last_surface=1)
            if parameter in {'XField','YField','Wavelength'}:q['selection']=2
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            assert r['series'][0]['x_unit']==unit
            for y in r['series'][0]['y']:e.check('Fixed thickness during system scan',y[0],2)
            state=await e.call('get_task_status',dict(task_id=r['task']['task_id']));assert state['close_attempted']and not state.get('cleanup_warnings')
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=10,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(field_type='ObjectHeight',lens_units='Centimeters')))
        height_settings=await e.call('get_system_settings');height_surfaces=await e.call('get_surfaces')
        q=dict(kind='universal_plot_1d',category='System',parameter='XField',selection=2,start=-.1,stop=.1,samples=3,first_surface=1,last_surface=1)
        r=await e.finish(await e.call('run_analysis',dict(request=q)));assert r['series'][0]['x_unit']=='Centimeters'
        for y in r['series'][0]['y']:e.check('Object-height field fixed thickness',y[0],2)
        assert await e.call('get_system_settings')==height_settings and await e.call('get_surfaces')==height_surfaces
    asyncio.run(execute('universal224_system',work))
