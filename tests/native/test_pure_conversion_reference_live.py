"""Pure-conversion persistence and generated source/detector runtime acceptance."""
import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute

def compare_saved(e,actual,expected,path='objects'):
    if isinstance(expected,dict):
        assert actual.keys()==expected.keys()
        for key,value in expected.items():compare_saved(e,actual[key],value,path+'.'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected)
        for i,value in enumerate(expected):compare_saved(e,actual[i],value,f'{path}[{i}]')
    elif isinstance(expected,float):
        e.check(path,actual,expected,atol=1e-8,rtol=1e-7)
    else:assert actual==expected,(path,actual,expected)


@pytest.mark.zemax
def test_pure_conversion_no_stop_source_detector_reload():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        result=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(mode='pure',convert_stop_to_nsc_aperture=False,create_sources_and_detectors=True,overfill_factor=1))))
        assert result['after']['mode']=='NonSequential'
        assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
        before=await e.call('get_nsc_objects',dict(request=dict(start=1,count=20)))
        saved=str(e.folder/'pure.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        compare_saved(e,await e.call('get_nsc_objects',dict(request=dict(start=1,count=20))),before)
        trace=await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42,ignore_errors=False))))
        assert (await e.call('get_task_status',dict(task_id=trace['task']['task_id'])))['close_attempted']
    asyncio.run(execute('pure_conversion063',work))
