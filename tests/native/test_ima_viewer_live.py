"""Typed viewer exact intensity, native channel identity and serial lifecycle."""
import asyncio,json,struct,time,uuid
from pathlib import Path
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_viewer_files_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        resource=await e.call('get_system_resources',dict(request=dict(kind='image_simulation_files')))
        root=Path(resource['directory']);token=uuid.uuid4().hex
        planes=[]
        for j in range(3):
            plane=bytearray(49);plane[8+j*8]=[255,128,64][j];plane[15+j*8]=[64,32,16][j];planes.append(bytes(plane))
        fixtures={
            'rgb.IMA':struct.pack('<hhh',0,7,3)+b''.join(planes),
            'mono.IMA':struct.pack('<hhh',0,7,1)+planes[0],
            'zero.IMA':b'7\n'+b'0000000\n'*7,
            'float.BIM':struct.pack('<ii',7,7)+struct.pack('<49d',*([0,.123456789012345]+[0]*46+[2.])),
            'broken.BIM':struct.pack('<ii',7,7),
        }
        paths={name:root/('viewer454_'+token+'_'+name) for name in fixtures}
        for name,raw in fixtures.items():paths[name].write_bytes(raw)
        try:
            for name,map_index in [('rgb.IMA',1),('rgb.IMA',2),('rgb.IMA',3),('mono.IMA',1),('zero.IMA',1),('float.BIM',1)]:
                q=dict(kind='ima_bim_viewer',input_file=paths[name].name,map_index=map_index)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                assert result['native_settings']['InputFile']==paths[name].name
                assert result['native_settings']['ShowAs']=='SourceBitmap'
                assert len(result['grids'])==5
                task_id=result['task']['task_id']
                child=await e.call('get_task_status',dict(task_id=result['native_task_id']))
                assert child['state']=='succeeded' and child['close_attempted'] and not child.get('cleanup_warnings'),child
                if name in ('rgb.IMA','mono.IMA'):
                    plane=planes[map_index-1] if name=='rgb.IMA' else planes[0]
                    expected=[list(plane[i*7:(i+1)*7]) for i in reversed(range(7))]
                    native=result['grids'][map_index+1 if name=='rgb.IMA' else 2]['values']
                    for iy,row in enumerate(expected):
                        for ix,value in enumerate(row):
                            e.check(name+str(map_index)+' file '+str((ix,iy)),result['grids'][0]['values'][iy][ix],value,atol=0,rtol=0)
                            e.check(name+str(map_index)+' native '+str((ix,iy)),native[iy][ix],value,atol=0,rtol=0)
                elif name=='float.BIM':
                    e.check('BIM float64 retained',result['grids'][0]['values'][0][1],.123456789012345,atol=0,rtol=0)
                    e.check('BIM normalized double',result['grids'][1]['values'][0][1],.123456789012345/2,atol=0,rtol=0)
                else:assert result['normalization']['zero_input'] and all(v==0 for row in result['grids'][1]['values'] for v in row)
                page=await e.call('get_task_result',dict(task_id=task_id,grid=1,x_start=1,y_start=2,width=3,height=2))
                assert page['grid']['values']==[r[1:4] for r in result['grids'][1]['values'][2:4]]
                rows=await e.call('get_task_result',dict(task_id=task_id,start=7,count=9));assert len(rows['rows'])==9
                (e.folder/(name+str(map_index)+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/(name+str(map_index)+'.png')))))
            error=await e.call('run_analysis',dict(request=dict(kind='ima_bim_viewer',input_file=paths['broken.BIM'].name)),okay=False)
            assert error['error']['code']=='INVALID_RESOURCE_DATA',error
            q=dict(kind='ima_bim_viewer',input_file=paths['rgb.IMA'].name,map_index=2)
            task=await e.call('run_analysis',dict(request=q))
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+90
            while task['state'] not in ('succeeded','failed','cancelled'):
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='cancelled',task
            await e.finish(await e.call('run_analysis',dict(request=q)))
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
            await e.call('save_lens_as',dict(path=str(e.folder/'reloaded.zos')))
            await e.call('open_lens',dict(path=str(e.folder/'reloaded.zos')))
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            await e.finish(await e.call('run_analysis',dict(request=q)))
        finally:
            for path in paths.values():path.unlink(missing_ok=True)
    asyncio.run(execute('viewer454_acceptance',work))

@pytest.mark.zemax
def test_viewer_arbitrary_plane_formal_conversion():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        resource=await e.call('get_system_resources',dict(request=dict(kind='image_simulation_files')))
        root=Path(resource['directory']);token=uuid.uuid4().hex
        paths=[]
        try:
            for maps,selected in [(2,2),(4,4)]:
                path=root/('viewer455_'+token+str(maps)+'.IMA');paths.append(path)
                planes=[]
                for j in range(maps):
                    plane=bytearray(49);plane[8+j*8]=255;plane[15+j*8]=64;planes.append(bytes(plane))
                path.write_bytes(struct.pack('<hhh',0,7,maps)+b''.join(planes))
                q=dict(kind='ima_bim_viewer',input_file=path.name,map_index=selected)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                assert result['temporary_input_removed'] and not Path(result['native_input_identity']['path']).exists()
                assert result['input_identity']['path']==str(path)
                expected=[list(planes[selected-1][i*7:(i+1)*7]) for i in reversed(range(7))]
                for iy,row in enumerate(expected):
                    for ix,value in enumerate(row):
                        e.check('selected map '+str(maps)+str((ix,iy)),result['grids'][0]['values'][iy][ix],value,atol=0,rtol=0)
                        e.check('converted native map '+str(maps)+str((ix,iy)),result['grids'][2]['values'][iy][ix],value,atol=0,rtol=0)
                file_result=await e.finish(await e.call('run_analysis',dict(request=q|dict(method='file'))))
                assert file_result['grids'][:2]==result['grids'][:2] and file_result['native_task_id'] is None
                (e.folder/(str(maps)+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        finally:
            for path in paths:path.unlink(missing_ok=True)
    asyncio.run(execute('viewer455_planes',work))
