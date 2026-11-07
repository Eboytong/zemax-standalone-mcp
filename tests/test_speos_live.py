import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('mode',['cartesian','radial','whitebox'])
def test_speos_owned_copy_native(mode):
    async def work(e):
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',{'path':str(lens)})
        before_settings=await e.call('get_system_settings')
        before_surfaces=await e.call('get_surfaces')
        if mode=='whitebox':
            request=dict(kind='whitebox',output_directory=str(e.folder/'whitebox'))
        else:
            request=dict(kind='lens_system',path=str(e.folder/(mode+'.optdistortion')),
                         sensor_width=10,sensor_height=8,assume_radial_symmetry=mode=='radial')
        result=await e.finish(await e.call('run_speos_export',{'request':request}),timeout_seconds=600)
        assert result['copy_closed'] and result['tool_closed']
        assert result['source_metadata_preserved']
        assert Path(result['path']).is_file()
        assert before_settings==await e.call('get_system_settings')
        assert before_surfaces==await e.call('get_surfaces')
    asyncio.run(execute('speos_'+mode,work))
