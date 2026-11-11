import asyncio

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_optional_contribution_finite_aspheric_and_native_composition():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5,material_catalogs=['SCHOTT'],
            field_type='ObjectHeight',fields=[dict(x=0,y=0),dict(x=0,y=2)],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=500,replace_solves=True),
            dict(surface=1,surface_type='EvenAspheric',is_stop=True,semi_diameter=5,radius=50,thickness=3,material='N-BK7',replace_solves=True),
            dict(surface=2,semi_diameter=5,radius=-40,thickness=2,material='N-F2',replace_solves=True),
            dict(surface=3,semi_diameter=5,radius=-150,thickness=90,replace_solves=True)]))
        original=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        baseline=str(e.folder/'finite-aspheric.zos')
        await e.call('save_lens_as',dict(path=baseline))
        slots=await e.call('get_glass_slots')
        assert len(slots['slots'])==2,slots
        assert slots['slots'][0]['contribution_conditions']==['contribution_requires_standard_surfaces']
        q=dict(kind='glass_trials',include_contributions=False,reference_wavelength=1,
            groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)],catalogs=['SCHOTT'],
            variables=[dict(surface=3,cell='thickness',minimum=65,maximum=110)],objectives=[dict(metric='rms_spot')],
            cycles='Fixed_1_Cycle',nd_tolerance=1,vd_tolerance=200,
            joint_slots=[dict(group=0,materials=[dict(catalog='SCHOTT',material='N-BK7'),dict(catalog='SCHOTT',material='N-BAK4')]),
                         dict(group=1,materials=[dict(catalog='SCHOTT',material='N-F2')])])
        result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=240)
        assert result['summary']['succeeded']==2,result
        assert result['contributions'] is None and result['contribution_status']=='disabled by request'
        assert result['resources']['all_copies_closed'] and result['finalist_recheck']['passed']
        assert await e.call('get_surfaces')==original
        assert await e.call('get_system_settings')==settings
        # Same material pairs, native objectives, bounds and optimizer, composed through public tools.
        for row in result['rows']:
            await e.call('open_lens',dict(path=baseline))
            await e.call('update_surfaces',dict(changes=[dict(surface=a['group']+1,material=a['identity']['material']) for a in row['assignments']]))
            await e.call('update_merit_function',dict(mode='replace',operands=[
                dict(type='RSCE',parameters={'2':3,'3':1,'4':0,'5':1},target=0,weight=1),
                dict(type='CTGT',parameters={'2':3},target=65,weight=10000),
                dict(type='CTLT',parameters={'2':3},target=110,weight=10000)]))
            await e.call('set_variables',dict(variables=[dict(surface=3,cell='thickness',variable=True)]))
            await e.finish(await e.call('run_local_optimization',dict(cycles='Fixed_1_Cycle')))
            await e.call('evaluate_merit_function')
            mfe=await e.call('get_merit_function')
            e.check('composed native RSCE',mfe['operands'][0]['value'],row['after']['rms_spot'],atol=1e-8,rtol=1e-7)
            surfaces=await e.call('get_surfaces')
            e.check('composed optimized thickness',surfaces['surfaces'][3]['cells']['thickness']['value'],row['variables'][0]['actual'],atol=1e-8,rtol=1e-7)
        await e.call('open_lens',dict(path=baseline))
        assert await e.call('get_surfaces')==original
    asyncio.run(execute('d026_optional_contribution',work))
