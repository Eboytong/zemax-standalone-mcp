import asyncio
import math
import json
import uuid
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_geometric_image_ideal_asymmetric_source():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',is_stop=True,parameters={'1':100},thickness=100,semi_diameter=5,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=1)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,semi_diameter=5,replace_solves=True)]))
        resources=await e.call('get_system_resources',dict(request=dict(kind='geometric_image_files')))
        source=Path(resources['directory'])/('mcp086_'+uuid.uuid4().hex+'.IMA')
        pixels=[''.join('9'if (x,y)==(22,10)else'0'for x in range(33))for y in range(33)]
        source.write_text('33\n'+'\n'.join(pixels)+'\n',encoding='ascii')
        try:
            q=dict(kind='geometric_image',input_file=source.name,wavelength=1,field_size=1,image_size=3,number_of_pixels=65,rays_x1000=100,use_pixel_interpolation=False,total_watts=1,reference='Vertex')
            before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
            saved=str(e.folder/'ideal.zos')
            await e.call('save_lens_as',dict(path=saved))
            records=[]
            for rotation,parity,sx,sy in [(0,'Even',1,-1),(0,'Odd',1,1),(90,'Even',1,1),(90,'Odd',-1,1)]:
                result=await e.finish(await e.call('run_analysis',dict(request={**q,'rotation':rotation,'parity':parity})))
                records.append(result)
                (e.folder/'ideal-images.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                assert result['grids']
                for g in result['grids']:
                    total=sum(v for row in g['values']for v in row if v is not None)
                    x=sum((g['min_x']+ix*g['dx'])*v for row in g['values']for ix,v in enumerate(row)if v is not None)/total
                    y=sum((g['min_y']+iy*g['dy'])*v for iy,row in enumerate(g['values'])for v in row if v is not None)/total
                    e.check('integrated source watts',total*g['dx']*g['dy'],1,atol=1e-8,rtol=1e-7)
                    e.check('ideal asymmetric X '+str(rotation)+parity,x,sx*100*math.tan(math.radians(6/33)),atol=3/65,rtol=0)
                    e.check('ideal asymmetric Y '+str(rotation)+parity,y,sy*100*math.tan(math.radians(6/33)),atol=3/65,rtol=0)
                task=result['task']['task_id']
                page=await e.call('get_task_result',dict(task_id=task,grid=0,x_start=0,y_start=0,width=7,height=5))
                assert page['grid']['values']==[row[:7]for row in result['grids'][0]['values'][:5]]
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/(str(rotation)+parity+'.png')))))
                assert (await e.call('get_task_status',dict(task_id=task)))['close_attempted']
                assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
            await e.call('open_lens',dict(path=saved))
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
            await e.finish(await e.call('run_analysis',dict(request=q)))
            import time
            task=await e.call('run_analysis',dict(request={**q,'rays_x1000':100000}))
            running=task['state']=='running'
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+60
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
            (e.folder/'cancellation.json').write_text(json.dumps(dict(started_running=running,task=task),ensure_ascii=False,indent=2),encoding='utf-8')
            rejected=await e.call('run_analysis',dict(request={**q,'input_file':'absent_mcp_resource.IMA'}),okay=False)
            assert rejected['error']['code']=='INVALID_RESOURCE'
            await e.finish(await e.call('run_analysis',dict(request=q)))
            assert await e.call('get_system_settings')==before and await e.call('get_surfaces')==surfaces
        finally:source.unlink(missing_ok=True)
    asyncio.run(execute('geoimage087',work))
