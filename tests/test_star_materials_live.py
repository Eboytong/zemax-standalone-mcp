import asyncio
import pytest
from support.native import execute


@pytest.mark.zemax
def test_native_six_wavelength_material_conditions_and_dndt():
    async def work(e):
        await e.model()
        await e.call('update_system_settings',{'settings':{'material_catalogs':['SCHOTT']}})
        baseline=await e.call('get_system_settings')
        waves=[.3650146,.4861327,.5875618,.6562725,1.01398,1.529582]
        samples=[dict(wavelength_um=w,material_temperature_c=t,delta_temperature_c=.01)
                 for w in waves for t in [20.,19.99,20.01]]
        data=await e.call('get_material_properties',{'request':dict(catalog='SCHOTT',material='N-BK7',
            include_internal_transmission=False,include_birefringence=False,star_samples=samples)})
        rows=data['star_samples']['rows']
        assert len(rows)==18
        for i,w in enumerate(waves):
            center,minus,plus=rows[3*i:3*i+3]
            assert center['wavelength_um']==w and center['refractive_index']>1
            reference=(plus['refractive_index']-minus['refractive_index'])/.02
            e.check('dn/dT central difference '+str(w),center['dn_dt'],reference,atol=1e-8,rtol=.01)
        assert await e.call('get_system_settings')==baseline
    asyncio.run(execute('star_materials_six_wavelengths',work))
