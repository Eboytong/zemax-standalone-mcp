"""Serial native stock-catalog discovery, selection, insertion and candidates."""
import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_catalog_search_load_insert_stdio():
    async def work(e):
        await e.model()
        vendors=(await e.call('get_lens_catalogs'))['vendors']
        if not vendors:pytest.skip('native stock catalogs absent: install Stockcat vendor resources')
        selected=None
        for vendor in vendors[:5]:
            result=await e.finish(await e.call('run_lens_catalog_search',dict(request=dict(vendor=vendor,max_results=2))))
            if result['rows']:
                selected=result['rows'][0];break
        if selected is None:pytest.skip('first five native vendor catalogs have no matching candidates; prepare stock lens input')
        loaded=await e.finish(await e.call('run_catalog_lens',dict(request=dict(vendor=selected['vendor'],lens_name=selected['lens_name']))))
        assert loaded['selected']['lens_name']==selected['lens_name']and len(loaded['after']['surfaces'])>2
        for name in ('efl_mm','epd_mm'):e.check('selected '+name,loaded['selected'][name],selected[name],atol=1e-12,rtol=1e-12)
        path=str(e.folder/'loaded.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        before=(await e.call('get_surfaces',dict(count=1)))['total']
        inserted=await e.finish(await e.call('run_catalog_lens',dict(request=dict(vendor=selected['vendor'],lens_name=selected['lens_name'],action='insert',at_surface=1))))
        assert len(inserted['after']['surfaces'])>before
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=0,count=1))
        assert page
    asyncio.run(execute('catalog_selection021',work))

@pytest.mark.zemax
def test_material_candidates_independent_and_restored():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces',dict(start=1,count=1))
        material=baseline['surfaces'][0]['cells']['material']['value']
        q=dict(candidates=[dict(name='repeat_a',materials=[dict(surface=1,material=material,replace_solve=True)]),dict(name='repeat_b',materials=[dict(surface=1,material=material,replace_solve=True)])],evaluation=dict(merit=True))
        result=await e.finish(await e.call('run_catalog_evaluation',dict(request=q)))
        assert result['summary']['succeeded']==2 and result['restoration']['restored']
        a,b=result['rows']
        assert a['metrics']==b['metrics']
        restored=await e.call('get_surfaces',dict(start=1,count=1))
        assert restored['surfaces'][0]['cells']['material']['value']==material
    asyncio.run(execute('catalog_candidates021',work))
