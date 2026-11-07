import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_property_pages_stdio():
    async def work(e):
        await e.call('open_lens',{'path':str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')})
        original=await e.call('get_system_settings')
        await e.call('update_system_settings',{'settings':{'author':'ED-01','afocal_mode_units':'Milliradians','aperture_options':{'apodization_type':'Gaussian','apodization_factor':1,'semi_diameter_margin':0.1},'advanced':{'reference_opd':'ExitPupil','huygens_integral_method':'Auto'}}})
        settings=await e.call('get_system_settings');assert settings['author']=='ED-01'
        for kind in ['None','Lambertian','Gaussian','ABg']:
            patch={'type':kind}
            if kind in {'Lambertian','Gaussian'}:patch['scatter_fraction']=0.1
            if kind=='ABg':patch['abg_name']='ABG-EXAMPLE'
            if kind=='Gaussian':patch['sigma']=1
            await e.call('update_surfaces',{'changes':[{'surface':1,'scattering':patch}]})
        for aperture in [{'type':'Spider','width_of_arms':0.1,'number_of_arms':3},{'type':'UserAperture','aperture_file':'square.uda','uda_scale':1},{'type':'UserObscuration','aperture_file':'hexagon.uda','uda_scale':1},{'type':'FloatingAperture'}]:
            await e.call('update_surfaces',{'changes':[{'surface':1,'aperture':aperture}]})
        await e.call('open_lens',{'path':str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')})
        await e.call('update_surfaces',{'changes':[{'surface':1,'drawing':{'draw_local_axis':True,'draw_edges_as':'Tapered'},'type_properties':{'ignore_surface':False},'physical_optics':{'resample_after_refraction':True,'auto_resample':False,'x_sampling':'S64','y_sampling':'S64','x_width':10,'y_width':10},'disable_clear_semi_diameter_margins':True}]})
        pages=(await e.call('get_surfaces',{'start':1,'count':2}))['surfaces'][0]['properties']
        for name in ['composite','type_properties','physical_optics']:
            await e.call('update_surfaces',{'changes':[{'surface':1,name:pages[name]}]})
        current=await e.call('get_system_settings')
        await e.call('update_system_settings',{'settings':{'advanced':current['advanced']}})
        for kind in ['ABg','ABgFile','BSDF','User','ISScatterCatalog']:
            result=await e.call('get_system_resources',{'request':{'kind':'scattering_files','scattering_type':kind}},okay=kind not in {'User','BSDF'})
            if kind=='User' and 'error' in result:assert result['error']['code']=='UNSUPPORTED_SETTING'
            if kind=='BSDF' and 'error' in result:
                assert result['error']['code']=='UNSUPPORTED_SETTING'
                assert result['error']['details']['capability']=='sequential_bsdf_resource_selection'
        await e.call('get_system_resources',{'request':{'kind':'aperture_files'}})
        await e.call('update_system_settings',{'settings':{'aperture_options':{'afocal_image_space':True}}})
        assert (await e.call('get_system_settings'))['afocal_image_space']
        await e.call('update_system_settings',{'settings':{'aperture_options':{'afocal_image_space':False}}})
    asyncio.run(execute('property_pages',work))
