import asyncio
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('control',['coordinate_transform','components','thermal_controls','volume_controls','update_mode'])
def test_native_star_controls_adoption_and_shutdown(control):
    async def work(e):
        await e.model()
        async def run(payload):
            return await e.finish(await e.call('run_star_operation',{'request':payload}))
        if control=='coordinate_transform':
            result=await run(dict(kind=control,surface=1,offset=dict(x=.1,y=.2,z=.3),
                rotation_matrix=[0,-1,0,1,0,0,0,0,1],enabled=True))
            for actual,expected in zip(result['actual']['offset'],[.1,.2,.3]):
                e.check('STAR offset',actual,expected,atol=1e-12,rtol=1e-12)
            assert result['actual']['enabled']
        elif control=='components':
            await e.call('insert_surfaces',{'at':2})
            result=await run(dict(kind='define_component',first_surface=1,last_surface=2))
            assert result['actual']['component']['members']==[1,2]
            result=await run(dict(kind='remove_component',first_surface=1))
            assert not result['actual']['component']['in_component']
        elif control=='thermal_controls':
            state=await e.call('get_star_data',{'request':dict(surface=1,data_kind='temperature')})
            code=state['controls']['thermal']['fit_type']
            result=await run(dict(kind=control,surface=1,fit_type=code,working_wavelength=1))
            assert result['actual']['working_wavelength']==1 and result['actual']['fit_type']==code
        elif control=='volume_controls':
            result=await run(dict(kind=control,surface=1,data_kind='temperature',grin_step=.1))
            e.check('native GRIN step',result['actual']['grin_step'],.1,atol=1e-12,rtol=1e-12)
        else:
            result=await run(dict(kind='update_mode',mode='Suspended',manual_update=True))
            assert result['actual']['update_mode']=='Suspended'
            await run(dict(kind='update_mode',mode='Normal'))
    asyncio.run(execute('star_controls_'+control,work))
