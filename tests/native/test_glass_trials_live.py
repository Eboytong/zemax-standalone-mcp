import asyncio
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_glass_trials_native_stdio():
    async def work(e):
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5,material_catalogs=['SCHOTT'],
            fields=[dict(x=0,y=0),dict(x=0,y=2)],wavelengths=[dict(wavelength_um=.4861327),dict(wavelength_um=.5875618),dict(wavelength_um=.6562725)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,is_stop=True,semi_diameter=5,radius=50,thickness=3,material='N-BK7',replace_solves=True),
            dict(surface=2,semi_diameter=5,radius=-40,thickness=2,material='N-F2',replace_solves=True),dict(surface=3,semi_diameter=5,radius=-150,thickness=90,replace_solves=True)]))
        original=await e.call('get_surfaces');settings=await e.call('get_system_settings');revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)],catalogs=['SCHOTT'],
            variables=[dict(surface=3,cell='thickness',minimum=65,maximum=110)],objectives=[dict(metric='rms_spot')],max_candidates=4)
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        assert r['summary']['succeeded']==5,r
        assert any(abs(row['identity']['nd']-r['rows'][0]['identity']['nd'])>1e-8 for row in r['rows'])
        assert r['resources']['all_copies_closed'] and not r['resources']['cleanup_errors']
        c=r['contributions'];n=c['native_reference']
        for key,actual in [('effective_focal_length',c['reference']['effective_focal_length']),('petzval_curvature',c['reference']['petzval_curvature']),
            ('axial_color',c['exact_paraxial_axial_color']),('lateral_color',c['exact_paraxial_lateral_color'])]:
            e.check('matrix/native '+key,actual,n[key],atol=1e-10,rtol=1e-6)
        e.check('cemented material Petzval sum',sum(g['petzval_curvature'] for g in c['groups']),n['petzval_curvature'],atol=1e-10,rtol=1e-6)
        for row in r['rows']:
            assert row['copy_closed'] and row['native_optimization']['succeeded']
            assert row['merit_after']<=row['merit_before']*1.001+1e-10
            assert all(math.isfinite(v) for v in row['after'].values())
            assert row['actual_settings']==r['rows'][0]['actual_settings']
            assert 65<=row['variables'][0]['actual']<=110
        assert await e.call('get_surfaces')==original
        assert await e.call('get_system_settings')==settings
        assert (await e.call('get_status'))['model_revision']==revision
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=1,count=1));assert len(page['rows'])==1
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'glass-trials.png'))))
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        best=next(row for row in r['rows'] if row['index']==r['summary']['best_index'])
        await e.call('open_lens',dict(path=best['saved_model']))
        replay=await e.finish(await e.call('run_analysis',dict(request=q|dict(max_candidates=1,cycles='Fixed_1_Cycle'))),timeout_seconds=180)
        for key,value in best['after'].items():e.check('reload metric '+key,replay['rows'][0]['before'][key],value,atol=1e-10,rtol=1e-7)
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        no=await e.finish(await e.call('run_analysis',dict(request=q|dict(max_relative_cost=.000001))),timeout_seconds=180)
        assert no['summary']['candidate_count']==1 and no['summary']['succeeded']==1
        # Cancel after a yielded optimization boundary; source remains available.
        t=await e.call('run_analysis',dict(request=q))
        await e.call('get_task_status',dict(task_id=t['task_id']))
        await e.call('cancel_task',dict(task_id=t['task_id']))
        for _ in range(500):
            t=await e.call('get_task_status',dict(task_id=t['task_id']))
            if t['state'] in ('succeeded','failed','cancelled'):break
            await asyncio.sleep(.02)
        assert t['state']=='cancelled',t
        cancelled=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert cancelled['resources']['all_copies_closed'] and not cancelled['resources']['cleanup_errors']
        await e.finish(await e.call('run_analysis',dict(request=q|dict(max_relative_cost=.000001))),timeout_seconds=180)
    asyncio.run(execute('glass_trials_native',work))


@pytest.mark.zemax
def test_glass_trials_radius_and_protection(tmp_path):
    import json
    import shutil
    import time
    import uuid
    from pathlib import Path
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config,DEFAULT_INSTALL
    from zemax_mcp.data import clean
    from tests.support.paths import run_dir

    folder=run_dir('glass_trials_protection');b=Backend(Config(DEFAULT_INSTALL,folder));record={};owned=None
    def call(name,**args):
        r=b.dispatch(name,args);assert r['ok'],r;return r['data']
    def finish(q,expected='succeeded'):
        t=call('run_analysis',request=q);deadline=time.monotonic()+180
        while t['state'] not in ('succeeded','failed','cancelled'):
            assert time.monotonic()<deadline
            time.sleep(.02);t=call('get_task_status',task_id=t['task_id'])
        result=b._full_result(t['task_id']);assert t['state']==expected,result;return result
    try:
        record['connect']=call('connect');call('new_system');call('insert_surfaces',at=1,count=2)
        call('update_system_settings',aperture_value=5,material_catalogs=['SCHOTT'],fields=[dict(x=0,y=0),dict(x=0,y=2)],
            wavelengths=[dict(wavelength_um=.4861327),dict(wavelength_um=.5875618),dict(wavelength_um=.6562725)])
        call('update_surfaces',changes=[dict(surface=1,is_stop=True,semi_diameter=5,radius=50,thickness=3,material='N-BK7',replace_solves=True),
            dict(surface=2,semi_diameter=5,radius=-40,thickness=2,material='N-F2',replace_solves=True),dict(surface=3,semi_diameter=5,radius=-150,thickness=90,replace_solves=True)])
        q=dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)],catalogs=['SCHOTT'],
            variables=[dict(surface=1,cell='radius',minimum=45,maximum=55),dict(surface=3,cell='thickness',minimum=65,maximum=110)],
            objectives=[dict(metric='rms_spot'),dict(metric='effective_focal_length',target=84.6,weight=.01)],max_relative_cost=.000001)
        record['radius']=finish(q)
        assert record['radius']['summary']['succeeded']==1
        assert record['radius']['rows'][0]['native_optimization']['succeeded']
        assert len(record['radius']['rows'][0]['variables'])==2
        assert record['radius']['resources']['all_copies_closed']
        # Native same-name material in two separate catalog files.
        glasscat=Path(str(b.native.application.ZemaxDataDir))/'Glasscat'
        owned=glasscat/('D008_'+uuid.uuid4().hex+'.AGF');shutil.copyfile(glasscat/'SCHOTT.AGF',owned)
        b.system.SystemData.MaterialCatalogs.AddCatalog(owned.stem)
        record['duplicate']=finish(q,'failed')
        assert record['duplicate']['error']['code']=='AMBIGUOUS_MATERIAL'
        assert record['duplicate']['resources']['all_copies_closed']
        b.system.SystemData.MaterialCatalogs.RemoveCatalog(owned.stem)
        cell=b.system.LDE.GetSurfaceAt(1).MaterialCell
        cell.SetSolveData(cell.CreateSolveType(b.native.api.Editors.SolveType.MaterialModel))
        record['solve']=finish(q,'failed')
        assert record['solve']['error']['code']=='SOLVE_PROTECTED'
        assert record['solve']['resources']['all_copies_closed']
    finally:
        record['disconnect']=b.dispatch('disconnect',{})
        if owned is not None and owned.is_file():owned.unlink()
        record['owned_catalog_removed']=owned is None or not owned.exists()
        (folder/'evidence.json').write_text(json.dumps(clean(record),ensure_ascii=False,indent=2),encoding='utf-8')
        print('Condition evidence:',folder,flush=True)

