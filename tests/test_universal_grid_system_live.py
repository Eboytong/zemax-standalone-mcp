"""Native two-dimensional System selectors, physical axes and mixed response."""
import asyncio
import pytest
from support.native import execute


@pytest.mark.zemax
def test_universal_grid_system_axes():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=2,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(
            aperture_options=dict(apodization_type='Gaussian'),
            fields=[dict(x=0,y=0),dict(x=1,y=2)],
            wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        saved=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=saved))
        await e.call('open_lens',dict(path=saved))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        for parameter,low,high,unit in [
            ('XField',-1,1,'degrees'),('YField',-2,2,'degrees'),
            ('Wavelength',.45,.65,'micrometers'),('Temperature',10,30,'Celsius'),
            ('Pressure',.8,1.2,'atmospheres'),('Aperture',4,6,'Millimeters'),
            ('ApodizationFactor',1,3,'dimensionless')]:
            axis=dict(category='System',parameter=parameter,start=low,stop=high,samples=3)
            if parameter in {'XField','YField','Wavelength'}:axis['selection']=2
            q=dict(kind='universal_plot_2d',
                x=dict(surface=1,parameter='Radius',start=20,stop=40,samples=5),
                y=axis,operand='CVVA',first_surface=1)
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            g=r['grids'][0];assert (g['nx'],g['ny'])==(5,3)
            assert g['x_unit']=='Millimeters'and g['y_unit']==unit
            for row in g['values']:
                for x,value in zip(g['x'],row):e.check('Mixed-axis reciprocal radius '+parameter,value,1/x)
            task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
            assert state['close_attempted']and not state.get('cleanup_warnings')
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=10,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(field_type='ObjectHeight',lens_units='Centimeters')))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        q=dict(kind='universal_plot_2d',
            x=dict(category='System',parameter='XField',selection=2,start=-.1,stop=.1,samples=5),
            y=dict(category='System',parameter='Wavelength',selection=2,start=.45,stop=.65,samples=3),
            first_surface=1,last_surface=1)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        g=r['grids'][0];assert (g['nx'],g['ny'])==(5,3)
        assert g['x_unit']=='Centimeters'and g['y_unit']=='micrometers'
        for row in g['values']:
            for value in row:e.check('Dual System axes fixed thickness',value,2)
        task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'system-grid.png'))))
        assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
    asyncio.run(execute('universal227_system_grid',work))
