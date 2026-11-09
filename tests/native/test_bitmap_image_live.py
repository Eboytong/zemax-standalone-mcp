"""GBM typed CFG adoption, asymmetric RGB, native pixels and stdio lifecycle."""
import asyncio
from pathlib import Path
import pytest
from PIL import Image
from tests.support.native import execute
from zemax_mcp.native_bitmap import read_bitmap


@pytest.mark.zemax
def test_bitmap_cfg_rgb_identity_paging_rotation_and_zero_input():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces')
        source=e.folder/'asymmetric.bmp'
        image=Image.new('RGB',(7,5))
        image.putdata([(255 if x<2 else 0,160 if y<2 else 0,96 if x>=4 and y>=3 else 0)
                       for y in range(5) for x in range(7)])
        image.save(source)
        result0=None
        for rotation in [0,90]:
            q=dict(kind='geometric_bitmap_image',input_file=str(source),surface=7,field_size=1,
                   rotation=rotation,rays_per_pixel=10,x_pixels=17,y_pixels=11,x_pixel_size=.05,y_pixel_size=.05)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            if rotation==0:result0=result
            else:assert result['grids'][0]['values']!=result0['grids'][0]['values']
            actual=result['actual_settings']['actual_readback']
            assert actual['rotation']==rotation and actual['surface']==7
            assert actual['input_file']==str(source) and actual['rays_per_pixel']==10
            assert result['input_selection']['identity_verified']
            assert all(item['accepted'] for item in result['actual_settings']['cfg_operations'])
            bitmap=read_bitmap(result['actual_settings']['native_output_file'])
            for grid in result['grids'][:3]:
                assert (grid['nx'],grid['ny'])==(17,11)
                assert grid['values']==bitmap['channels'][grid['channel']]
            task=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=task,grid=1,x_start=2,y_start=1,width=7,height=5))
            assert page['grid']['values']==[row[2:9] for row in result['grids'][1]['values'][1:6]]
            intensity=result['grids'][3]
            assert intensity['quantity']=='native_normalized_intensity'
            assert result['normalized_intensity_available']
            assert len(intensity['values'])==11 and all(len(row)==17 for row in intensity['values'])
            assert all(value>=0 for row in intensity['values'] for value in row)
            scalar_page=await e.call('get_task_result',dict(task_id=task,grid=3,x_start=2,y_start=1,width=7,height=5))
            assert scalar_page['grid']['values']==[row[2:9] for row in intensity['values'][1:6]]
            assert result['native_efficiency']['unit']=='percent'
            png=e.folder/f'rotation{rotation}.png'
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(png))))
            assert png.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            await e.call('export_analysis_image',dict(request=dict(task_id=task,item=3,path=str(e.folder/f'intensity{rotation}.png'))))
            status=await e.call('get_task_status',dict(task_id=task))
            assert status['state']=='succeeded' and status['close_attempted'] and not status.get('cleanup_warnings')
        Image.new('RGB',(7,5)).save(e.folder/'black.bmp')
        zero=await e.finish(await e.call('run_analysis',dict(request={**q,'input_file':str(e.folder/'black.bmp')})))
        assert all(value==0 for grid in zero['grids'] for row in grid['values'] for value in row)
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('bitmap_cfg_rgb',work))

@pytest.mark.zemax
def test_bitmap_cancel_native_failure_reuse_and_model_reload():
    async def work(e):
        import time
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(field_type='ObjectHeight',aperture_value=2,
            fields=[dict(x=0,y=0)],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=200,replace_solves=True),
            dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,
                 semi_diameter=1,is_stop=True,replace_solves=True)]))
        settings=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        merit=await e.call('get_merit_function');configs=await e.call('get_configurations',dict(request={}))
        source=e.folder/'cancel-source.bmp'
        Image.new('RGB',(128,128),(255,160,96)).save(source)
        q=dict(kind='geometric_bitmap_image',input_file=str(source),surface=2,field_size=1,
               rays_per_pixel=10000,x_pixels=17,y_pixels=11,x_pixel_size=.1,y_pixel_size=.1)
        task=await e.call('run_analysis',dict(request=q))
        assert task['state'] not in {'succeeded','failed','cancelled'},task
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.03)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled',task
        assert task['close_attempted'] and not task.get('cleanup_warnings'),task
        await e.call('get_task_result',dict(task_id=task['task_id']))
        missing=await e.call('run_analysis',dict(request=q|dict(input_file=str(e.folder/'absent.bmp'))),okay=False)
        assert missing['error']['code']=='INVALID_RESOURCE',missing
        broken=e.folder/'broken.bmp';broken.write_bytes(b'owned invalid bitmap')
        failed=await e.call('run_analysis',dict(request=q|dict(input_file=str(broken),rays_per_pixel=1)))
        deadline=time.monotonic()+60
        while failed['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.03)
            failed=await e.call('get_task_status',dict(task_id=failed['task_id']))
        raw=await e.call('get_task_result',dict(task_id=failed['task_id']))
        assert failed['state']=='failed' and raw['task']['error']['code']=='INVALID_RESULT_DATA',raw
        assert failed['close_attempted'] and not failed.get('cleanup_warnings'),failed
        Image.new('RGB',(7,5),(255,160,96)).save(source)
        reuse=q|dict(rays_per_pixel=100)
        result=await e.finish(await e.call('run_analysis',dict(request=reuse)))
        assert result['input_selection']['identity_verified']
        assert any(v for grid in result['grids'] for row in grid['values'] for v in row)
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_surfaces')==surfaces
        assert await e.call('get_merit_function')==merit
        assert await e.call('get_configurations',dict(request={}))==configs
        saved=str(e.folder/'bitmap-reload.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_surfaces')==surfaces
        assert await e.call('get_merit_function')==merit
        assert await e.call('get_configurations',dict(request={}))==configs
        final=await e.finish(await e.call('run_analysis',dict(request=reuse)))
        assert final['input_selection']['identity_verified']
    asyncio.run(execute('bitmap_lifecycle',work))

