"""Independent dimensions and analytic references for physical geometry."""
import math
import pytest

from zemax_mcp.geometry import check_radial_pair, check_meshes


def face(radius, aperture, **kw):
    return dict(radius=radius, semi_diameter=aperture,
                mechanical_semi_diameter=aperture, conic=0, coefficients=[], **kw)


def test_mechanical_edge_is_part_of_solid():
    a, b = face(16, 11.90195), face(-22, 10.02477)
    b['mechanical_semi_diameter'] = 11.90195
    result = check_radial_pair(a, b, 6.5)
    assert result['state'] == 'failed'
    expected = 6.5-22+math.sqrt(22**2-11.90195**2)-16+math.sqrt(16**2-11.90195**2)
    assert result['minimum_mm'][1] == pytest.approx(expected, abs=1e-8)
    assert result['optical_minimum_mm'][0] > 0


@pytest.mark.parametrize('scale', [1, 0.1, 25.4])
def test_units_and_air_overlap(scale):
    result = check_radial_pair(face(-30/scale, 7/scale), face(-14/scale, 7/scale), .4/scale, scale_mm=scale)
    assert result['state'] == 'failed'
    expected = .4 - 14 + math.sqrt(14**2-7**2) + 30 - math.sqrt(30**2-7**2)
    assert result['minimum_mm'][1] == pytest.approx(expected, abs=1e-7)


def test_internal_aspheric_thin_zone():
    a, b = face(0, 2), face(0, 2)
    # gap = .2 - t**2 + .25*t**3; minimum at t=8/3, between endpoints
    b['coefficients'] = [-1, .25]
    result = check_radial_pair(a, b, .2)
    assert result['state'] == 'failed'
    assert result['minimum_mm'][1] == pytest.approx(.2-64/27, abs=1e-6)


def test_undefined_sag_is_unverified():
    assert check_radial_pair(face(1, 2), face(0, 2), 1)['state'] == 'unverified'


def cube(x=0, size=1):
    vertices = [[x+i*size,j*size,k*size] for i,j,k in
                [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
    triangles = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                 [1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    return dict(vertices=vertices, triangles=triangles, error_mm=0, source='analytic_fixture')


def test_mesh_gap_overlap_and_containment():
    assert check_meshes([cube(), cube(2)])['state'] == 'passed'
    assert check_meshes([cube(), cube(.5)])['state'] == 'failed'
    inner = cube(.25, .25)
    inner['vertices'] = [[x,y+.25,z+.25] for x,y,z in inner['vertices']]
    assert check_meshes([cube(), inner])['state'] == 'failed'


def test_open_mesh_cannot_pass():
    mesh = cube(); mesh['triangles'].pop()
    assert check_meshes([mesh])['state'] == 'unverified'


def test_mesh_export_error_prevents_uncertified_clearance():
    a,b=cube(),cube(1.001)
    a['error_mm']=b['error_mm']=.001
    assert check_meshes([a,b])['state'] == 'unverified'


def test_missing_export_bound_is_never_assumed_zero():
    mesh=cube();mesh['error_mm']=None
    assert check_meshes([mesh])['state']=='unverified'


def test_nested_solids_with_bounded_mesh_error_cannot_pass_clearance():
    outer, inner = cube(), cube(.25, .25)
    inner['vertices'] = [[x,y+.25,z+.25] for x,y,z in inner['vertices']]
    outer['error_mm'] = inner['error_mm'] = .001
    result = check_meshes([outer, inner])
    assert result['state'] == 'failed'
    assert result['pairs'][0]['reason'] == 'penetration_or_containment'


def test_disagreeing_containment_rays_keep_pair_unverified(monkeypatch):
    from zemax_mcp import geometry
    monkeypatch.setattr(geometry, '_contains', lambda *args: None)
    result = check_meshes([cube(), cube(2)])
    assert result['state'] == 'unverified'
    assert result['pairs'][0]['reason'] == 'containment_or_ray_classification_uncertainty'


def test_deadline_retains_unverified_result():
    assert check_meshes([cube(),cube(2)],budget_seconds=0)['state']=='unverified'


def test_annular_selected_gap_contains_independent_minimum():
    from zemax_mcp.geometry import selected_radial_gap
    a=face(0,2,z_mm=0);b=face(0,2,z_mm=3);b['coefficients']=[-.1]
    result=selected_radial_gap(a,b,1,dict(r_min_mm=1,r_max_mm=1.5))
    expected=3-.1*1.5**4
    assert result['bounds'][0]<=expected<=result['bounds'][1]
    assert result['position_radius_mm']==pytest.approx(1.5)


@pytest.mark.parametrize('region',[{'r_max_mm':3},{'r_min_mm':-1},{'r_min_mm':1,'r_max_mm':1}])
def test_selected_gap_rejects_region_outside_actual_boundary(region):
    from zemax_mcp.geometry import selected_radial_gap
    assert selected_radial_gap(face(0,2,z_mm=0),face(0,2,z_mm=3),1,region)['reason']=='engineering_region_outside_boundary'


def test_radial_interval_includes_algebraic_reference_roundoff():
    a=face(0,2);b=face(-20,2)
    result=check_radial_pair(a,b,6)
    expected=6-20+math.sqrt(400-4)
    assert result['minimum_mm'][0]<=expected<=result['minimum_mm'][1]


@pytest.mark.parametrize('scale',[.1,1,25.4])
def test_selected_annulus_uses_physical_mm_in_lens_units(scale):
    from zemax_mcp.geometry import selected_radial_gap
    a=face(0,2/scale,z_mm=0);b=face(-20/scale,2/scale,z_mm=6)
    result=selected_radial_gap(a,b,scale,dict(r_min_mm=1,r_max_mm=1.5))
    expected=6-20+math.sqrt(400-1.5**2)
    assert result['bounds'][0]<=expected<=result['bounds'][1]


def test_explicit_cemented_relation_reuses_native_shared_boundary():
    from zemax_mcp.geometry import merge_native_relations
    inferred=[dict(kind='cemented',entities=['a','b'],native_verified=True)]
    declaration=dict(id='bond',kind='cemented',entities=['b','a'],native_verified=False)
    merged=merge_native_relations(inferred,[declaration])
    assert len(merged)==1 and merged[0]['native_verified']is True
    assert merged[0]['id']=='bond'
    assert len(merge_native_relations(inferred,[declaration,declaration]))==2
    assert len(merge_native_relations(inferred,[dict(declaration,kind='contact')]))==2


def test_native_parent_chain_checks_ancestors_and_cycles():
    from zemax_mcp.geometry import native_containment_path
    assert native_containment_path({'O1':None,'O2':'O1','O3':'O2'},'O3','O1')==['O3','O2','O1']
    assert native_containment_path({'O1':'O2','O2':'O1'},'O2','O1')is None


def test_rectangular_gap_domain_intersects_circular_aperture():
    from zemax_mcp.geometry import selected_radial_gap
    a=face(0,2,z_mm=0);b=face(0,2,z_mm=3);b['coefficients']=[-.1]
    region=dict(x_min_mm=.5,x_max_mm=1,y_min_mm=.2,y_max_mm=.6)
    result=selected_radial_gap(a,b,1,region)
    expected=3-.1*(1+.6**2)**2
    assert result['bounds'][0]<=expected<=result['bounds'][1]
    assert result['radial_domain_mm']['r_min_mm']==pytest.approx(math.hypot(.5,.2))
