import asyncio,json
from pathlib import Path
import pytest
from support.native import execute
from zemax_mcp.evaluation import interpolate


@pytest.mark.zemax
@pytest.mark.parametrize("family",["fft","huygens"])
def test_surface_mtf_native_reference_probe(family):
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        records=[]
        request=dict(kind=family+'_surface_mtf',field=3,wavelength=1,sampling='S_256x256')
        if family=='huygens':request['image_sampling']='S_256x256';request['image_delta']=1
        surface=await e.finish(await e.call('run_analysis',dict(request=request)))
        single=await e.finish(await e.call('run_fft_mtf',dict(field=3,wavelength=1,sampling='S_256x256',maximum_frequency=200)))if family=='fft'else await e.finish(await e.call('run_analysis',dict(request=dict(kind='huygens_mtf',field=3,wavelength=1,sampling='S_256x256',image_sampling='S_256x256',image_delta=1,maximum_frequency=200))))
        records.append(dict(family=family,surface=surface,single=single))
        (e.folder/'references.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        if family=='huygens':
            g=surface['grids'][0];curve=single['series'][0];cx=g['zero_frequency_index']['x'];cy=g['zero_frequency_index']['y']
            e.check('Huygens DC X',g['min_x']+cx*g['dx'],0)
            e.check('Huygens DC Y',g['min_y']+cy*g['dy'],0)
            e.check('Huygens DC modulation',g['values'][cy][cx],1)
            for k in [1,2,3,4,5,8,12,16]:
                f=k*g['dx']
                for axis,actual,col in [('sagittal',g['values'][cy][cx+k],1),('tangential',g['values'][cy+k][cx],0)]:
                    expected=interpolate(curve['x'],[row[col]for row in curve['y']],f)
                    e.check('Huygens matched '+axis,actual,expected,atol=.005,rtol=0)
            assert (await e.call('get_task_status',dict(task_id=surface['task']['task_id'])))['close_attempted']
    asyncio.run(execute('surface_mtf090_matched',work))
