import pytest
from pydantic import ValidationError

from zemax_mcp.glass_trials import GlassTrials
from zemax_mcp.joint_glass import enumerate_assignments, assignment_key
def query(**changes):
    return dict(kind='glass_trials',groups=[dict(first_surface=1,last_surface=2)],catalogs=['SCHOTT'],
        variables=[dict(surface=2,cell='thickness',minimum=1,maximum=100)],objectives=[dict(metric='rms_spot')])|changes


def test_cartesian_control_dedup_budget_and_three_slots():
    pool = [dict(catalog='SCHOTT', material=name) for name in ['A', 'B', 'C']]
    pools = [(0, pool), (1, pool)]
    candidates = enumerate_assignments(pools, 'cartesian', 100)
    assert len(candidates) == 9
    assert len({assignment_key(c['assignments']) for c in candidates}) == 9
    assert [a['identity']['material'] for a in candidates[0]['assignments']] == ['A', 'A']
    assert len(enumerate_assignments(pools, 'cartesian', 4)) == 4
    assert len(enumerate_assignments(pools + [(2, pool)], 'cartesian', 100)) == 27
    assert len(enumerate_assignments(pools, 'one_at_time', 100)) == 5
    assert len(enumerate_assignments(pools, 'beam', 100)) == 3


@pytest.mark.parametrize('change', [dict(joint_slots=[dict(group=1)]),
    dict(joint_slots=[dict(group=0), dict(group=0)]), dict(max_evaluations=0),
    dict(total_budget_seconds=float('nan')), dict(design_id='../../x'),
    dict(design_id='x', save_candidates=False),
    dict(joint_slots=[dict(group=0, materials=[dict(catalog='SCHOTT', material='A'),dict(catalog='schott.agf', material='a')])])])
def test_joint_request_boundaries(change):
    with pytest.raises(ValidationError):
        GlassTrials.model_validate(query(**change))


def test_explicit_pool_reads_only_requested_materials(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace as NS
    from zemax_mcp import joint_glass, glass_trials, materials
    @contextmanager
    def owned(_):yield object()
    def scan(*args):raise AssertionError('explicit pool must not scan the catalog')
    read=[]
    def identity(tool,catalog,material):
        read.append(material)
        return dict(catalog=catalog,material=material,nd=1.5,vd=60,
            minimum_wavelength_um=.3,maximum_wavelength_um=2,relative_cost=1,exclude_substitution=False)
    monkeypatch.setattr(materials,'owned_catalog',owned)
    monkeypatch.setattr(glass_trials,'discover_steps',scan)
    monkeypatch.setattr(joint_glass,'read_identity',identity)
    b=NS(system=NS(SystemData=NS(MaterialCatalogs=NS(GetCatalogsInUse=lambda:['SCHOTT'],
        GetMaterialsInCatalog=lambda c:['A','B']),Wavelengths=NS(NumberOfWavelengths=1,
        GetWavelength=lambda i:NS(Wavelength=.55)))))
    q=GlassTrials.model_validate(query(joint_slots=[dict(group=0,materials=[dict(catalog='SCHOTT',material='B')])]))
    steps=joint_glass.discover_joint_steps(b,q,[dict(material='A')])
    while True:
        try:next(steps)
        except StopIteration as done:
            candidates,pools,result=done.value;break
    assert read==['A','B']
    assert result['combination_count']==2
    assert [v['material'] for v in pools[0][1]]==['A','B']


def test_catalog_discovery_can_release_resource_during_scan(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace as NS
    from zemax_mcp import glass_trials, materials
    lifecycle=[]
    names=['A']+[f'B{i}' for i in range(40)]
    tool=NS(GetAllCatalogs=lambda:['SCHOTT'],GetAllMaterials=lambda:names,RelCost='1',Nd=1.5,Vd=60,
        MinimumWavelength=.3,MaximumWavelength=2,ExcludeSubstitution=False,MaterialStatus='Standard')
    @contextmanager
    def owned(_):
        lifecycle.append('opened')
        try:yield tool
        finally:lifecycle.append('closed')
    monkeypatch.setattr(materials,'owned_catalog',owned)
    b=NS(system=NS(SystemData=NS(MaterialCatalogs=NS(GetCatalogsInUse=lambda:['SCHOTT'],
        GetMaterialsInCatalog=lambda c:names),Wavelengths=NS(NumberOfWavelengths=1,
        GetWavelength=lambda i:NS(Wavelength=.55)))))
    steps=glass_trials.discover_steps(b,GlassTrials.model_validate(query()),'A')
    next(steps)
    assert lifecycle==['opened']
    steps.close()
    assert lifecycle==['opened','closed']
