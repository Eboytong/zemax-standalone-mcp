"""Formal processed-source outlet probe; dedicated viewer acceptance remains separate."""
import asyncio,json,uuid
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_owned_ima_source_bitmap_outlet():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        resources=await e.call('get_system_resources',dict(request=dict(kind='image_simulation_files')))
        target=Path(resources['directory'])/('ima449_'+uuid.uuid4().hex+'.IMA')
        rows=['0000000','0900000','0500000','0000000','0003000','0000000','0000000']
        target.write_text('7\n'+'\n'.join(rows)+'\n',encoding='ascii')
        try:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='image_simulation',input_file=target.name,wavelength=1,
                show_as='SourceBitmap',oversampling='None',guard_band='None',aberrations='None',psf_x_points=3,psf_y_points=3))))
            assert result['task']['settings']['native']['InputFile']==target.name
            assert result['task']['settings']['native']['ShowAs']=='SourceBitmap'
            assert len(result['grids'])==3
            expected=[[int(int(v)*255/9) for v in row] for row in reversed(rows)]
            for grid in result['grids']:
                assert (grid['nx'],grid['ny'])==(7,7)
                for iy,row in enumerate(expected):
                    for ix,value in enumerate(row):
                        e.check(grid['channel']+str((ix,iy))+' native source 8-bit pixel',grid['values'][iy][ix],value,atol=0,rtol=0)
            (e.folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'source.png'))))
        finally:target.unlink(missing_ok=True)
    asyncio.run(execute('ima449_source',work))
