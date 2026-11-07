"""Prepared serial conversion acceptance; native initialization is currently blocked."""
import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute

async def cooke(e):
    await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
    await e.call('insert_surfaces',dict(at=1))
    surfaces=await e.call('get_surfaces')
    # Insert the trailing dummy immediately before the image.
    last=surfaces['total']-1
    await e.call('insert_surfaces',dict(at=last))
    return last

@pytest.mark.zemax
def test_nsc_group_conversion_reference_rays():
    async def work(e):
        last=await cooke(e)
        request=dict(rays=[dict(px=x,py=y,wavelength=1)for x,y in [(0,0),(.2,0),(0,.2),(-.2,-.2)]])
        before=await e.finish(await e.call('run_batch_ray_trace',dict(request=request)))
        result=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(first_surface=1,last_surface=last))))
        assert result['after']['mode']=='Sequential' and result['checkpoint']
        after=await e.finish(await e.call('run_batch_ray_trace',dict(request=request)))
        assert len(before['rows'])==len(after['rows'])==4
        for a,b in zip(before['rows'],after['rows']):
            assert a['state']==b['state']=='succeeded'
            for axis in range(3):
                e.check('converted position',b['position'][axis],a['position'][axis],atol=1e-7,rtol=1e-7)
                e.check('converted direction',b['direction'][axis],a['direction'][axis],atol=1e-7,rtol=0)
        saved=e.folder/'converted-group.zos'
        await e.call('save_lens_as',dict(path=str(saved)))
        await e.call('open_lens',dict(path=str(saved)))
        await e.call('get_nsc_objects',dict(request=dict(nsc_surface=result['after']['nsc_groups'][0],start=1,count=10)))
    asyncio.run(execute('conversion026_group',work))

@pytest.mark.zemax
def test_nsc_pure_conversion_sources_and_reload():
    async def work(e):
        await cooke(e)
        result=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(mode='pure',create_sources_and_detectors=True))))
        assert result['after']['mode']=='NonSequential' and result['after']['object_count']>0
        objects=await e.call('get_nsc_objects',dict(request=dict(start=1,count=20)))
        saved=e.folder/'converted-pure.zos'
        await e.call('save_lens_as',dict(path=str(saved)))
        await e.call('open_lens',dict(path=str(saved)))
        assert (await e.call('get_nsc_objects',dict(request=dict(start=1,count=20))))==objects
    asyncio.run(execute('conversion026_pure',work))

@pytest.mark.zemax
def test_nsc_conversion_rejects_partial_source_generation():
    async def work(e):
        await cooke(e)
        response=await e.call('run_nsc_conversion',dict(request=dict(mode='pure',first_surface=2,create_sources_and_detectors=True)),okay=False)
        assert response['error']['code']=='CONDITION_NOT_MET'
    asyncio.run(execute('conversion026_reject',work))
