"""Discriminate aperture clipping from unavailable native ring validity."""
import asyncio,json
import pytest
from support.native import execute


@pytest.mark.zemax
def test_power_map_aperture_ring_diagnostic():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)],
            fields=[dict(x=0,y=0),dict(x=0,y=1),dict(x=1,y=1)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=50,material='N-BK7',
            semi_diameter=8,is_stop=True,replace_solves=True)]))
        source=str(e.folder/'source.zos');await e.call('save_lens_as',dict(path=source));await e.call('open_lens',dict(path=source))
        record=dict(hypothesis='Native POWF/POWP may ignore aperture clipping on internal differential rays; shrinking a centered aperture distinguishes vignette loss from reported finite power',
            pupil_points=[0,1e-6,1e-5,1e-4,1e-3,1e-2,.1,.5],cases=[])
        for radius in [None,.1,.001,.00001]:
            if radius is not None:
                await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=radius))]))
            before=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
            trace=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(target_surface=1,
                rays=[dict(hx=0,hy=0,px=px,py=0,wavelength=1)for px in record['pupil_points']]))))
            assert trace['rows'][0]['error_code']==trace['rows'][0]['vignette_code']==0
            case=dict(aperture_radius=radius,trace=trace,results=[]);record['cases'].append(case)
            for kind in ['power_field_map','power_pupil_map']:
                for quantity in ['Power','EFL']:
                    q=dict(kind=kind,surface=1,wavelength=1,quantity=quantity,x_points=3,y_points=3)
                    if kind=='power_field_map':q.update(x_field_width=2,y_field_width=2)
                    result=await e.finish(await e.call('run_analysis',dict(request=q)))
                    case['results'].append(dict(request=q,center_value=result['grids'][0]['values'][1][1],result=result))
                    (e.folder/'ring-diagnostic.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
        path=str(e.folder/'after.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('power593_aperture_ring',guarded))
