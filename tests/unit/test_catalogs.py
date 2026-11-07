"""Stock catalog selection and baseline-controlled candidate evaluation."""
from pathlib import Path
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.catalog_models import CatalogSearch, CatalogLens
from zemax_mcp.models import CatalogEvaluation
from zemax_mcp.errors import ZemaxError
from tests.unit.test_design_tools import Backend

class Lens:
    def __init__(self,name):
        self.Vendor='Local';self.LensName=name;self.EFL=25.;self.EPD=5.;self.Shape='Plano';self.Type='Spherical';self.NumberOfElements=1;self.Telecentric=False
        self.loaded=[];self.inserted=[]
    def LoadLens(self,save):self.loaded.append(save)
    def InsertLensSeq(self,*args):self.inserted.append(args);return True

@pytest.fixture
def b(monkeypatch,tmp_path):
    from zemax_mcp import catalogs
    from zemax_mcp.detectors import check_setting_readback
    b=Backend();b.source_path='source.zos';b.work_path=tmp_path/'work.zos';b.directory=tmp_path
    b.lenses=[Lens('first'),Lens('second')]
    b.tool.GetAllVendors=lambda:['Local']
    b.tool.GetResult=lambda i:b.lenses[i]
    b.tool.MatchingLenses=2
    b.tool.NumberOfElements=1
    b.tool.SetNumberOfElementsAny=lambda:setattr(b.tool,'NumberOfElements',0)
    b.system.Tools.OpenLensCatalogs=lambda:b.tool
    b._working_copy=lambda:setattr(b,'work_path',tmp_path/'new-work.zos')
    def checked(native,target,name,value):
        setattr(target,name,value);check_setting_readback(target,name,value)
    monkeypatch.setattr(catalogs,'checked_setting',checked)
    monkeypatch.setattr(catalogs,'scalar_settings',lambda target:{k:v for k,v in vars(target).items()if isinstance(v,(str,bool,int,float))})
    return b

@pytest.mark.parametrize('payload',[
    dict(vendor='',efl_mm=dict(minimum=1,maximum=2)),
    dict(vendor='Local',efl_mm=dict(minimum=2,maximum=1)),
    dict(vendor='Local',epd_mm=dict(minimum=0,maximum=float('nan'))),
    dict(vendor='Local',number_of_elements=True),dict(vendor='Local',max_results=0),
])
def test_search_contract_rejects(payload):
    with pytest.raises(ValidationError):CatalogSearch(**payload)

@pytest.mark.parametrize('payload',[
    dict(vendor='Local',lens_name='first',action='insert'),
    dict(vendor='Local',lens_name='first',at_surface=1),
    dict(vendor='Local',lens_name='first',reverse_surface_geometry=True),
    dict(vendor='Local',lens_name='first',action='insert',at_surface=True),
])
def test_load_insert_contract_rejects(payload):
    with pytest.raises(ValidationError):CatalogLens(**payload)

def test_search_records_native_identity_and_filters(b):
    view=b.run_lens_catalog_search(CatalogSearch(vendor='local',efl_mm=dict(minimum=10,maximum=30),max_results=1))
    result=b.tasks[view['task_id']]['result']
    assert view['state']=='succeeded'and b.tool.closed==1 and b.revision==0
    assert result['total_matches']==2 and result['truncated']and result['rows'][0]['lens_name']=='first'
    assert b.tool.SelectedVendor=='Local'and b.tool.UseEFL and b.tool.MinEFL==10

def test_vendor_missing_closes_without_mutation(b):
    with pytest.raises(ZemaxError)as exc:b.run_lens_catalog_search(CatalogSearch(vendor='missing'))
    assert exc.value.code=='INVALID_RESOURCE'and b.tool.closed==1 and b.revision==0

def test_negative_epd_rejected(b):
    with pytest.raises(ZemaxError)as exc:b.run_lens_catalog_search(CatalogSearch(vendor='Local',epd_mm=dict(minimum=-1,maximum=2)))
    assert exc.value.code=='INVALID_ARGUMENT'and b.tool.closed==1

def test_silent_filter_rejection_closes(b):
    b.tool.UseEFL=False;b.tool.reject='UseEFL'
    with pytest.raises(ZemaxError)as exc:b.run_lens_catalog_search(CatalogSearch(vendor='Local',efl_mm=dict(minimum=10,maximum=30)))
    assert exc.value.code=='SETTING_REJECTED'and b.tool.closed==1

def test_empty_results_are_valid(b):
    b.tool.MatchingLenses=0
    view=b.run_lens_catalog_search(CatalogSearch(vendor='Local'))
    assert view['state']=='succeeded'and b.tasks[view['task_id']]['result']['rows']==[]

def test_lookup_errors_retain_native_origin(b):
    b.tool.GetResult=lambda i:(_ for _ in ()).throw(RuntimeError('native index failure'))
    view=b.run_lens_catalog_search(CatalogSearch(vendor='Local'))
    assert view['state']=='failed'and b.tasks[view['task_id']]['error']['message']=='native index failure'and b.tool.closed==1

def test_load_uses_unique_name_and_working_copy(b):
    view=b.run_catalog_lens(CatalogLens(vendor='Local',lens_name='second'))
    assert view['state']=='succeeded'and b.lenses[1].loaded==[False]and b.lenses[0].loaded==[]
    assert b.tool.closed==1 and b.revision==1 and b.source_path is None and b.work_path.name=='new-work.zos'

def test_duplicate_name_fails_without_loading(b):
    b.lenses[1].LensName='first'
    view=b.run_catalog_lens(CatalogLens(vendor='Local',lens_name='first'))
    assert view['state']=='failed'and b.tasks[view['task_id']]['error']['code']=='INVALID_SELECTION'
    assert not b.lenses[0].loaded and b.tool.closed==1

def test_insert_readback_and_arguments(b):
    view=b.run_catalog_lens(CatalogLens(vendor='Local',lens_name='first',action='insert',at_surface=2,reverse_surface_geometry=True))
    assert view['state']=='succeeded'and b.lenses[0].inserted==[(2,True,True)]and b.source_path=='source.zos'

def test_insert_failure_keeps_checkpoint(b):
    b.lenses[0].InsertLensSeq=lambda *args:False
    view=b.run_catalog_lens(CatalogLens(vendor='Local',lens_name='first',action='insert',at_surface=1))
    task=b.tasks[view['task_id']]
    assert view['state']=='failed'and task['error']['details']['checkpoint']=='checkpoint.zos'and b.tool.closed==1

def test_insert_bounds_before_checkpoint(b):
    with pytest.raises(ZemaxError)as exc:b.run_catalog_lens(CatalogLens(vendor='Local',lens_name='first',action='insert',at_surface=4))
    assert exc.value.code=='INDEX_OUT_OF_RANGE'and b.revision==0

def test_catalog_discovery_closes(b):
    result=b.get_lens_catalogs(None)
    assert result['vendors']==['Local']and b.tool.closed==1 and b.revision==0

@pytest.mark.parametrize('candidates',[
    [dict(name='empty')],
    [dict(name='duplicate',materials=[dict(surface=1,material='N-BK7'),dict(surface=1,material='N-F2')])],
])
def test_candidate_contract(candidates):
    with pytest.raises(ValidationError):CatalogEvaluation(candidates=candidates,evaluation=dict(merit=True))

def evaluation_setup(b):
    b.materials={1:'N-BK7'};b.observed=[];b.restored=0
    b._checkpoint=lambda label:'baseline.zos'
    def restore(task,*args):
        b.materials={1:'N-BK7'};b.restored+=1;task['restoration']=dict(restored=True)
    b._restore_model=restore
    def update(patch):
        for change in patch.changes:
            if change.material=='FAIL':raise ZemaxError('SETTING_REJECTED','bad material')
            b.materials[change.surface]=change.material
        return dict(applied=dict(b.materials))
    b.update_surfaces=update
    def evaluate(task,spec):
        b.observed.append(dict(b.materials))
        if False:yield
        return dict(metrics=[dict(value=len(b.materials))])
    b._evaluate=evaluate
    return b

def test_candidates_use_independent_baseline_and_restore(b):
    evaluation_setup(b)
    req=CatalogEvaluation(candidates=[dict(name='a',materials=[dict(surface=1,material='N-F2')]),dict(name='b',materials=[dict(surface=2,material='F_SILICA')])],evaluation=dict(merit=True),save_candidates=False)
    view=b.run_catalog_evaluation(req)
    for _ in range(4):b.tick()
    task=b.tasks[view['task_id']]
    assert task['state']=='succeeded'and b.observed==[{1:'N-F2'},{1:'N-BK7',2:'F_SILICA'}]
    assert b.materials=={1:'N-BK7'}and task['result']['summary']['succeeded']==2 and b.restored==3

def test_candidate_failure_continues_and_cancel_restores(b):
    evaluation_setup(b)
    req=CatalogEvaluation(candidates=[dict(name='bad',materials=[dict(surface=1,material='FAIL')]),dict(name='good',materials=[dict(surface=1,material='N-F2')])],evaluation=dict(merit=True),save_candidates=False)
    view=b.run_catalog_evaluation(req);b.tick();task=b.tasks[view['task_id']]
    assert task['rows'][0]['state']=='failed'
    task['cancel_requested']=True;b.tick()
    assert task['state']=='cancelled'and b.materials=={1:'N-BK7'}and task['result']['restoration']['restored']

def test_mismatched_candidate_conditions_are_reported(b):
    evaluation_setup(b)
    def evaluate(task,spec):
        if False:yield
        return dict(metrics=[dict(value=1)],conditions=dict(system=dict(aperture=dict(value=len(b.materials)))))
    b._evaluate=evaluate
    req=CatalogEvaluation(candidates=[dict(name='a',materials=[dict(surface=1,material='N-F2')]),dict(name='b',materials=[dict(surface=2,material='F_SILICA')])],evaluation=dict(merit=True),save_candidates=False)
    view=b.run_catalog_evaluation(req)
    for _ in range(4):b.tick()
    task=b.tasks[view['task_id']]
    assert task['result']['summary']['succeeded']==1 and task['result']['rows'][1]['error']['code']=='CONDITION_MISMATCH'
    assert task['result']['restoration']['restored']

def test_common_settings_applied_to_each_candidate(b):
    evaluation_setup(b);b.applied_settings=[]
    b.update_system_settings=lambda q:b.applied_settings.append(q.aperture_value)or dict(aperture_value=q.aperture_value)
    req=CatalogEvaluation(candidates=[dict(name='a',materials=[dict(surface=1,material='N-F2')]),dict(name='b',materials=[dict(surface=1,material='N-BK7')])],evaluation=dict(merit=True),common_settings=dict(aperture_value=10),save_candidates=False)
    view=b.run_catalog_evaluation(req)
    for _ in range(4):b.tick()
    assert b.applied_settings==[10,10]and b.tasks[view['task_id']]['state']=='succeeded'
