"""Independent physical-unit scaling and raw degenerate-zero controls."""
import asyncio,json
import pytest
from support.native import execute

@pytest.mark.zemax
def test_power_maps_equivalent_mm_cm_models():
    async def work(e):
        await e.model()
        glass=await e.call('get_material_properties',dict(request=dict(catalog='SCHOTT',material='N-BK7',
            include_internal_transmission=False,include_birefringence=False)))
        n=glass['properties']['Nd'];efl_mm=n*50/(n-1)
        record=dict(reference='Single spherical interface n*R/(n-1); identical physical model inmm/cm; planar no-power control retains raw native zeros',
            nd=n,reference_efl_mm=efl_mm,absolute_tolerance_mm=2e-4,absolute_tolerance_diopters=2e-4,relative_tolerance=2e-5,cases=[])
        def save():(e.folder/'units.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        save()
        for unit,mm_per_unit in [('Millimeters',1.),('Centimeters',10.)]:
            await e.call('update_system_settings',dict(settings=dict(lens_units=unit,aperture_value=10/mm_per_unit,
                wavelengths=[dict(wavelength_um=.5875618)],fields=[dict(x=0,y=0),dict(x=1,y=1)])))
            for radius_mm in [50.,0.]:
                await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=radius_mm/mm_per_unit,
                    thickness=50/mm_per_unit,material='N-BK7',semi_diameter=8/mm_per_unit,is_stop=True,replace_solves=True)]))
                baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
                assert settings['lens_units']==unit
                for kind in ['power_field_map','power_pupil_map']:
                    for quantity in ['Power','EFL']:
                        q=dict(kind=kind,surface=1,quantity=quantity,x_points=3,y_points=3)
                        if kind=='power_field_map':q.update(x_field_width=2,y_field_width=2)
                        result=await e.finish(await e.call('run_analysis',dict(request=q)))
                        center=next(r for r in result['rows']if r['grid_x']==r['grid_y']==1)
                        case=dict(unit=unit,mm_per_unit=mm_per_unit,radius_mm=radius_mm,request=q,result=result)
                        record['cases'].append(case);save()
                        assert result['grids'][0]['value_unit']==('diopters'if quantity=='Power'else unit)
                        if radius_mm:
                            reference=1000/efl_mm if quantity=='Power'else efl_mm/mm_per_unit
                            e.check(kind+unit+quantity,center['raw_value'],reference,atol=2e-4 if quantity=='Power'else 2e-4/mm_per_unit,rtol=2e-5)
                        else:
                            assert center['raw_value']==0 and center['raw_value_state']=='native_zero'
                            assert center['zero_interpretation']=='unresolved_native_zero_semantics'
                        assert result['native_ring_validity']=='unavailable'
                        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=1,y_start=1,width=1,height=1))
                        assert page['grid']['values']==[[center['value']]]
                        state=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                        assert state['state']=='succeeded'and not state.get('cleanup_warnings')
                assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
                assert await e.call('get_merit_function')==merit
                path=str(e.folder/(unit+str(radius_mm)+'.zos'))
                await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
                assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
                assert await e.call('get_merit_function')==merit
        save()
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('power634_units',guarded))
