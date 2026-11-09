"""Serial native imaging adoption; prepared, not counted as numerical acceptance."""
import asyncio
import shutil
import uuid
import struct
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_geometric_bitmap_invalid_resource_preserves_session():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        response=await e.call('run_analysis',dict(request=dict(kind='geometric_bitmap_image',input_file='point.IMA')),okay=False)
        assert response['error']['code']=='INVALID_RESOURCE'
        assert not response['context']['requires_reconnect']
        await e.call('get_system_resources',dict(request=dict(kind='geometric_image_files')))
    asyncio.run(execute('bitmap_interface050',work))

@pytest.mark.zemax
@pytest.mark.parametrize('kind,scene',[
    ('image_simulation','point'),('image_simulation','bars'),('image_simulation','edge'),
    ('geometric_image','point'),('geometric_image','bars'),('geometric_image','edge'),
    ('extended_source_encircled_energy','point'),
])
def test_imaging_native_resources_and_result(kind,scene):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        resource_kind='image_simulation_files' if kind=='image_simulation' else 'geometric_image_files'
        resources=await e.call('get_system_resources',dict(request=dict(kind=resource_kind)))
        target=Path(resources['directory'])/('mcp023_'+uuid.uuid4().hex+('.bmp' if kind=='image_simulation' else '.IMA'))
        if kind=='image_simulation':
            size=33;stride=(size*3+3)//4*4;pixels=bytearray()
            for y in range(size):
                for x in range(size):
                    lit=(x==16 and y==16) if scene=='point' else x>=16 if scene=='edge' else (x//4)%2==0
                    pixels.extend(bytes([255 if lit else 0])*3)
                pixels.extend(bytes(stride-size*3))
            header=struct.pack('<2sIHHI',b'BM',54+len(pixels),0,0,54)
            dib=struct.pack('<IiiHHIIiiII',40,size,size,1,24,0,len(pixels),0,0,0,0)
            target.write_bytes(header+dib+pixels)
        else:shutil.copy2(Path(__file__).parents[1]/'resources/imaging023'/(scene+'.IMA'),target)
        try:
            names=(await e.call('get_system_resources',dict(request=dict(kind=resource_kind))))['items']
            assert target.name.casefold() in [x.casefold() for x in names]
            q=dict(kind=kind,**({'image_name':target.name,'rays_x1000':10} if kind=='extended_source_encircled_energy'else {'input_file':target.name}))
            if kind=='image_simulation':q.update(wavelength=1,psf_x_points=3,psf_y_points=3,x_pixels=33,y_pixels=33)
            if kind in {'geometric_image','geometric_bitmap_image'}:q.update(rays_x1000=10,number_of_pixels=33,image_size=10)
            result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
            assert result['structured_data_available'] and result['task']['state']=='succeeded'
            if kind=='image_simulation':
                assert result['native_bitmap']['source']=='native ImageSimulation OutputFile'
                assert {g['channel']for g in result['grids']}==set('RGB')
                assert all(g['x_unit']=='output_pixel'and g['value_unit']=='8-bit display RGB'for g in result['grids'])
                output=e.folder/'native.png'
                await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],source='native',path=str(output))))
                assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
                assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
            task=result['task']['task_id']
            if result.get('grids'):
                page=await e.call('get_task_result',dict(task_id=task,grid=0,width=7,height=5))
                assert len(page['grid']['values'])<=5
            if result.get('series'):
                page=await e.call('get_task_result',dict(task_id=task,series=0,count=3))
                assert len(page['series'][0]['x'])<=3
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'image.png'))))
        finally:target.unlink(missing_ok=True)
    asyncio.run(execute('imaging023_'+kind+'_'+scene,work))

@pytest.mark.zemax
@pytest.mark.parametrize('kind',['fft_line_edge_spread','geometric_line_edge_spread'])
def test_line_edge_native(kind):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,wavelength=1,field=1))))
        assert result['series'] and result['artifacts']
        assert 'native_header' in result
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=1,count=5))
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'spread.png'))))
    asyncio.run(execute('imaging023_'+kind,work))
