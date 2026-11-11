import math
from types import SimpleNamespace as S

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.glass_trials import GlassTrials,catalog_filter
from zemax_mcp.errors import ZemaxError


def query(**changes):
    return dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2)],catalogs=['SCHOTT'],
        variables=[dict(surface=2,cell='thickness',minimum=1,maximum=100)],objectives=[dict(metric='rms_spot')])|changes


@pytest.mark.parametrize('change',[
    dict(groups=[]),dict(groups=[dict(first_surface=2,last_surface=2)]),
    dict(groups=[dict(first_surface=1,last_surface=3),dict(first_surface=2,last_surface=4)]),
    dict(target_group=1),dict(catalogs=['SCHOTT','schott.agf']),dict(catalogs=[]),
    dict(variables=[]),dict(variables=[dict(surface=1,cell='radius',minimum=-1,maximum=1)]),
    dict(variables=[dict(surface=1,cell='thickness',minimum=1,maximum=1)]),
    dict(variables=[dict(surface=1,cell='radius',minimum=1,maximum=float('inf'))]),
    dict(objectives=[]),dict(objectives=[dict(metric='rms_spot'),dict(metric='rms_spot')]),
    dict(red_wavelength=2),dict(budget_per_candidate_seconds=0),dict(max_candidates=31),dict(rings=0),dict(mtf_frequency=0),
])
def test_invalid_contract(change):
    with pytest.raises(ValidationError):GlassTrials.model_validate(query(**change))


def test_registered_request_and_cemented_boundary():
    q=RunAnalysis(request=query(groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)])).request
    assert isinstance(q,GlassTrials) and q.target_group==0


def test_optional_contribution_is_default_compatible_and_separates_spectral_rules():
    assert GlassTrials.model_validate(query()).include_contributions is True
    q=GlassTrials.model_validate(query(include_contributions=False,blue_wavelength=1,reference_wavelength=1,red_wavelength=1))
    assert q.include_contributions is False


def test_material_groups_allow_aspheric_and_partial_system_but_protect_solves():
    from zemax_mcp.glass_trials import material_groups
    rows={1:S(Type='EvenAspheric',Material='N-BK7',MaterialCell=S(Solve='Fixed'))}
    system=S(LDE=S(NumberOfSurfaces=5,GetSurfaceAt=lambda i:rows[i]))
    q=GlassTrials.model_validate(query(include_contributions=False))
    assert material_groups(system,q)[0]['material']=='N-BK7'
    rows[1].MaterialCell.Solve='MaterialModel'
    with pytest.raises(ZemaxError,match='solve'):material_groups(system,q)


def test_catalog_filters_missing_cost_and_wave_limits():
    q=GlassTrials.model_validate(query(max_relative_cost=2))
    base=dict(nd=1.5,vd=60)
    c=dict(nd=1.51,vd=65,minimum_wavelength_um=.3,maximum_wavelength_um=2.5,relative_cost=1,exclude_substitution=False)
    reasons,distance=catalog_filter(c,base,q,[.486,.588,.656])
    assert reasons==[] and distance==pytest.approx(.1**2+.25**2)
    assert catalog_filter(c|dict(relative_cost=None),base,q,[.5])[0]==['relative_cost']
    assert catalog_filter(c|dict(exclude_substitution=True),base,q,[.5])[0]==['excluded_by_catalog']
    assert catalog_filter(c|dict(minimum_wavelength_um=.55),base,q,[.5])[0]==['wavelength_range']
    assert 'nd_range' in catalog_filter(c|dict(nd=math.nan),base,q,[.5])[0]
    q.max_relative_cost=None
    assert catalog_filter(c|dict(relative_cost=None),base,q,[.5])[0]==[]


@pytest.mark.parametrize('cleanup_fails',[False,True])
def test_contribution_failure_closes_copy_and_preserves_error(monkeypatch,cleanup_fails):
    import zemax_mcp.glass_trials as module
    closed=[]
    def close(save):
        closed.append(save)
        if cleanup_fails:raise RuntimeError('owned close failed')
    def fail(*args):raise ZemaxError('REFERENCE_FAILED','original reference failure')
    monkeypatch.setattr(module,'contributions',fail)
    task={'task_id':'test','rows':[]}
    b=S(system=S(CopySystem=lambda:S(Close=close)),requires_reconnect=False,
        _require_sequential=lambda **kw:None,_require_work=lambda:None,_cancel_boundary=lambda task:None,
        _composite=lambda kind,settings,factory:factory(task),_evaluation_error=lambda exc:dict(code=exc.code,message=str(exc)))
    flow=module.run_glass_trials(b,GlassTrials.model_validate(query()))
    with pytest.raises(ZemaxError) as err:next(flow)
    assert closed==[False]
    if cleanup_fails:
        assert err.value.code=='CLEANUP_FAILED' and err.value.details['operation_error']['code']=='REFERENCE_FAILED'
        assert b.requires_reconnect and not task['payload']['resources']['all_copies_closed']
    else:
        assert err.value.code=='REFERENCE_FAILED' and task['payload']['resources']['all_copies_closed']
