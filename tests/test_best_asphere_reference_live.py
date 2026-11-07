"""Compare the selected conic against independently constructed candidates."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_best_conic_matches_independent_candidates():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_merit_function',dict(mode='rms_spot_wizard'))
        await e.call('set_variables',dict(variables=[dict(surface=s,cell='radius',variable=True,replace_solve=True) for s in [1,2]]))
        baseline=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=baseline))
        before=(await e.call('evaluate_merit_function'))['merit_function']
        native=await e.finish(await e.call('run_design_tool',dict(request=dict(kind='find_best_asphere',first_surface=1,last_surface=2,asphere_type='Conic'))))
        native_state=await e.call('get_surfaces',dict(start=0,count=8))
        saved=str(e.folder/'selected.zos');await e.call('save_lens_as',dict(path=saved))
        candidates={}
        for surface in [1,2]:
            await e.call('open_lens',dict(path=baseline))
            await e.call('set_variables',dict(variables=[dict(surface=surface,cell='conic',variable=True,replace_solve=True)]))
            await e.finish(await e.call('run_local_optimization',dict(algorithm='DampedLeastSquares',cycles='Automatic',number_of_cores=1)))
            candidates[surface]=(await e.call('evaluate_merit_function'))['merit_function']
        (e.folder/'candidate-reference.json').write_text(json.dumps(dict(native_surface=native['BestSurface'],native_merit=native['BestMeritFunction'],candidates=candidates,initial=before),indent=2),encoding='utf-8')
        best=min(candidates,key=candidates.get)
        assert int(native['BestSurface'])==best
        e.check('native optimum vs manual conic candidate',native['BestMeritFunction'],candidates[best],atol=1e-7,rtol=1e-5)
        assert native['BestMeritFunction']<before
        await e.call('open_lens',dict(path=saved))
        assert await e.call('get_surfaces',dict(start=0,count=8))==native_state
        e.check('selected merit after reload',(await e.call('evaluate_merit_function'))['merit_function'],native['BestMeritFunction'],atol=1e-7,rtol=1e-5)
    asyncio.run(execute('best_asphere062',work))
