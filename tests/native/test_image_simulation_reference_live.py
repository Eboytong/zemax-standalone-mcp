"""Controlled ideal pixel-source probe with actual raster and state evidence."""
import asyncio,json,struct,uuid,time
from pathlib import Path
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_ideal_image_simulation_pixel_probe():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',is_stop=True,parameters={'1':100},thickness=100,semi_diameter=5,replace_solves=True),dict(surface=2,semi_diameter=5,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=1)])))
        directory=(await e.call('get_system_resources',dict(request=dict(kind='image_simulation_files'))))['directory']
        source=Path(directory)/('mcp145_'+uuid.uuid4().hex+'.bmp');w,h=17,11;stride=(w*3+3)//4*4;data=bytearray();expected=[]
        for y in range(h):
            row=[]
            for x in range(w):
                color=(255,255,255)if 2<=x<=5 and 2<=y<=4 else(0,255,0)if 10<=x<=13 and 7<=y<=9 else(0,0,0)
                row.append(list(color));data.extend(bytes(reversed(color)))
            expected.append(row);data.extend(bytes(stride-w*3))
        source.write_bytes(struct.pack('<2sIHHI',b'BM',54+len(data),0,0,54)+struct.pack('<IiiHHIIiiII',40,w,h,1,24,0,len(data),0,0,0,0)+data)
        (e.folder/'source.bmp').write_bytes(source.read_bytes())
        settings=await e.call('get_system_settings');surfaces=await e.call('get_surfaces');records=[]
        baseline_file=str(e.folder/'ideal.zos');await e.call('save_lens_as',dict(path=baseline_file))
        try:
            for show in ['SimulatedImage','SourceBitmap','PSFGrid']:
                q=dict(kind='image_simulation',input_file=source.name,wavelength='RGB',oversampling='None',guard_band='None',aberrations='None',psf_x_points=3,psf_y_points=3,x_pixels=w,y_pixels=h,use_relative_illumination=False,apply_fixed_apertures=False,suppress_frame=True,show_as=show)
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                records.append(dict(show=show,result=result))
                (e.folder/'pixels.json').write_text(json.dumps(dict(expected=expected,records=records),indent=2),encoding='utf-8')
                assert all(g['nx']==w and g['ny']==h for g in result['grids'])
                if show in ['SimulatedImage','SourceBitmap']:
                    for channel,grid in enumerate(result['grids']):
                        for y,row in enumerate(grid['values']):
                            for x,value in enumerate(row):e.check(show+' ideal pixel',value,expected[y][x][channel],atol=1 if show=='SimulatedImage'else 0,rtol=0)
                else:
                    for grid in result['grids']:
                        nonzero=[v for row in grid['values']for v in row if v]
                        e.check('ideal PSF-grid delta count',len(nonzero),9,atol=0,rtol=0)
                        e.check('ideal PSF-grid display peak',max(nonzero),255,atol=0,rtol=0)
                        e.check('ideal PSF-grid display sum',sum(nonzero),9*255,atol=0,rtol=0)
                assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
                assert await e.call('get_system_settings')==settings and await e.call('get_surfaces')==surfaces
            for flip,rotation,oversampling,guard in [('TopBottom','Rotate_0','None','None'),('LeftRight','Rotate_0','None','None'),('None','Rotate_180','None','None'),('None','Rotate_0','X2','X2')]:
                q.update(show_as='SourceBitmap',flip_source=flip,rotation_source=rotation,oversampling=oversampling,guard_band=guard)
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                expected_view=expected
                if flip=='TopBottom':expected_view=list(reversed(expected_view))
                if flip=='LeftRight':expected_view=[list(reversed(row))for row in expected_view]
                if rotation=='Rotate_180':expected_view=[list(reversed(row))for row in reversed(expected_view)]
                if oversampling=='X2':
                    expanded=[]
                    for row in expected_view:
                        doubled=[pixel for pixel in row for _ in range(2)];expanded.extend([doubled,doubled])
                    zero=[0,0,0];width=len(expanded[0]);height=len(expanded)
                    expected_view=[[zero]*(2*width)for _ in range(height//2)]+[[zero]*(width//2)+row+[zero]*(width//2)for row in expanded]+[[zero]*(2*width)for _ in range(height//2)]
                records.append(dict(show='source transform',request=q.copy(),result=result))
                (e.folder/'pixels.json').write_text(json.dumps(dict(expected=expected,records=records),indent=2),encoding='utf-8')
                assert (result['grids'][0]['nx'],result['grids'][0]['ny'])==(len(expected_view[0]),len(expected_view))
                for channel,grid in enumerate(result['grids']):
                    for y,row in enumerate(grid['values']):
                        for x,value in enumerate(row):e.check('processed source pixel',value,expected_view[y][x][channel],atol=0,rtol=0)
                assert await e.call('get_system_settings')==settings and await e.call('get_surfaces')==surfaces
            await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=v)for v in [.465,.535,.606]])))
            spectral=await e.call('get_system_settings')
            for wave in [1,2,3,'1+2+3']:
                monochrome=dict(q,wavelength=wave,show_as='SimulatedImage',flip_source='None',rotation_source='Rotate_0',oversampling='None',guard_band='None',use_polarization=wave=='1+2+3')
                result=await e.finish(await e.call('run_analysis',dict(request=monochrome)),timeout_seconds=180)
                records.append(dict(show='spectral',request=monochrome,result=result))
                (e.folder/'pixels.json').write_text(json.dumps(dict(expected=expected,records=records),indent=2),encoding='utf-8')
                for channel,grid in enumerate(result['grids']):
                    active=wave=='1+2+3'or channel==3-wave
                    for y,row in enumerate(grid['values']):
                        for x,value in enumerate(row):e.check('native spectral display pixel',value,expected[y][x][channel]if active else 0,atol=1 if active else 0,rtol=0)
                assert await e.call('get_system_settings')==spectral and await e.call('get_surfaces')==surfaces
            for aberrations in ['Geometric','Diffraction']:
                optical=dict(monochrome,aberrations=aberrations,psf_x_points=3,psf_y_points=3)
                result=await e.finish(await e.call('run_analysis',dict(request=optical)),timeout_seconds=180)
                records.append(dict(show=aberrations,request=optical,result=result))
                (e.folder/'pixels.json').write_text(json.dumps(dict(expected=expected,records=records),indent=2),encoding='utf-8')
                e.check('native optical display peak',max(v for g in result['grids']for row in g['values']for v in row),255,atol=1,rtol=0)
                assert await e.call('get_system_settings')==spectral and await e.call('get_surfaces')==surfaces
            await e.call('open_lens',dict(path=baseline_file))
            assert await e.call('get_system_settings')==settings and await e.call('get_surfaces')==surfaces
            base=dict(q,show_as='SimulatedImage',flip_source='None',rotation_source='Rotate_0',oversampling='None',guard_band='None')
            bad=await e.call('run_analysis',dict(request=dict(base,input_file='absent_mcp145.bmp')),okay=False)
            assert bad['error']['code']=='INVALID_RESOURCE'and not bad['context']['requires_reconnect']
            task=await e.call('run_analysis',dict(request=dict(base,aberrations='Diffraction',pupil_sampling='S_256x256',image_sampling='S_256x256',psf_x_points=31,psf_y_points=31,x_pixels=128,y_pixels=128)))
            deadline=time.monotonic()+15
            while task['state']=='queued':
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='running',task
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+60
            while task['state']not in ['cancelled','succeeded','failed']:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            (e.folder/'cancellation.json').write_text(json.dumps(task,indent=2),encoding='utf-8')
            assert task['state']=='cancelled'and task['close_attempted']and not task.get('cleanup_warnings'),task
            await e.finish(await e.call('run_analysis',dict(request=base)),timeout_seconds=180)
            assert await e.call('get_system_settings')==settings and await e.call('get_surfaces')==surfaces
        finally:source.unlink(missing_ok=True)
    asyncio.run(execute('image145_ideal',work))
