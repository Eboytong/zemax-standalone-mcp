"""Documented scene CFG selection, raw-grid/text readback and MCP paging."""
import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['extended_diffraction_image','partially_coherent_image'])
def test_scene_image_cfg_readback_grid_paging_and_restore(kind):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces')
        q=dict(kind=kind,field=2,wavelength=1)
        if kind=='extended_diffraction_image':q.update(source_width=.1,display_width=.2)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['actual_settings']['actual_readback']['field_deg']==14
        assert result['actual_settings']['actual_readback']['wavelength_um']==.48
        assert all(x['accepted'] for x in result['actual_settings']['cfg_operations'])
        assert result['input_selection']['identity_verified'] is False
        grid=result['grids'][0]
        assert len(grid['values'])==grid['ny'] and len(grid['values'][0])==grid['nx']
        assert grid['text_comparison_max_error']<=5.1e-5
        task=result['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=2,width=7,height=5))
        assert page['grid']['values']==[row[1:8] for row in grid['values'][2:7]]
        image=e.folder/'scene.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(image))))
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        status=await e.call('get_task_status',dict(task_id=task))
        assert status['state']=='succeeded' and status['close_attempted'] and not status.get('cleanup_warnings')
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces')==surfaces
    asyncio.run(execute('scene_'+kind,work))
