"""Independent STEP solids exercise the production OpenCascade adapter."""
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.gp import gp_Pnt
from zemax_mcp.geometry_kernel import check_step_entities


def box(tmp_path, name, x, size=1, error=0):
    path=tmp_path/(name+'.step')
    writer=STEPControl_Writer()
    writer.Transfer(BRepPrimAPI_MakeBox(gp_Pnt(x,0,0),size,size,size).Shape(),STEPControl_AsIs)
    writer.Write(str(path))
    return dict(id=name,path=str(path),representation_error_mm=error,source='independent_STEP_fixture')


def test_known_gap_and_location(tmp_path):
    result=check_step_entities([box(tmp_path,'a',0),box(tmp_path,'b',2)])
    assert result['state']=='passed'
    pair=result['pairs'][0]
    assert pair['distance_mm']==pytest.approx(1,abs=1e-6)
    assert pair['distance_interval_mm'][0]<=1<=pair['distance_interval_mm'][1]
    assert len(pair['position_mm'])==3


@pytest.mark.parametrize('x,size',[(.5,1),(.25,.25)])
def test_overlap_and_containment_fail(tmp_path,x,size):
    assert check_step_entities([box(tmp_path,'a',0),box(tmp_path,'b',x,size)])['state']=='failed'


def test_contact_requires_explicit_relationship(tmp_path):
    entities=[box(tmp_path,'a',0),box(tmp_path,'b',1)]
    assert check_step_entities(entities)['state']=='unverified'
    assert check_step_entities(entities,relations=[dict(kind='contact',entities=['a','b'])])['state']=='passed'


def test_relationship_does_not_excuse_undeclared_penetration(tmp_path):
    entities=[box(tmp_path,'a',0),box(tmp_path,'b',.5)]
    assert check_step_entities(entities,relations=[dict(kind='contact',entities=['a','b'])])['state']=='failed'


def test_unknown_representation_error_keeps_solid_unverified(tmp_path):
    entity=box(tmp_path,'a',0,error=None)
    assert check_step_entities([entity])['state']=='unverified'


def test_precision_and_budget_cannot_be_promoted_to_pass(tmp_path):
    entities=[box(tmp_path,'a',0,error=.001),box(tmp_path,'b',1.001,error=.001)]
    assert check_step_entities(entities)['state']=='unverified'
    assert check_step_entities(entities,budget_seconds=0)['state']=='unverified'


def test_nonaxisymmetric_polynomial_has_independent_volume():
    import math
    entity=dict(id='freeform',source='native_polynomial_definition',native_definition=dict(
        kind='polynomial',mechanical_radius_mm=2,normalization_mm=1,thickness_mm=3,
        polynomials=[[],[[2,0,.03],[0,2,-.01],[1,1,.02]]],
        rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,0]))
    result=check_step_entities([entity])
    assert result['state']=='passed',result
    expected=3*math.pi*4+(.03-.01)*math.pi*2**4/4
    assert result['entities'][0]['volume_mm3']==pytest.approx(expected,abs=1e-6)
    assert result['entities'][0]['representation_error_mm']<1e-6


def test_bounded_radial_asphere_volume_against_integral():
    import math
    entity=dict(id='asphere',source='native_radial_definition',native_definition=dict(
        kind='radial',mechanical_radius_mm=2,thickness_mm=3,target_error_mm=1e-4,
        profiles=[dict(radius_mm=0,conic=0,terms=[[4,.002]]),dict(radius_mm=0,conic=0,terms=[])],
        rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,0]))
    result=check_step_entities([entity])
    assert result['state']=='passed',result
    error=result['entities'][0]['representation_error_mm']
    expected=3*math.pi*4-.002*math.pi*2**6/3
    assert abs(result['entities'][0]['volume_mm3']-expected)<=2*math.pi*4*(error+1e-7)
    assert error<=1.001e-4


def test_conflicting_relations_remain_unverified(tmp_path):
    entities=[box(tmp_path,'a',0),box(tmp_path,'b',1)]
    result=check_step_entities(entities,relations=[dict(kind='contact',entities=['a','b']),dict(kind='cemented',entities=['b','a'])])
    assert result['state']=='unverified'
    assert result['issues'][0]['code']=='relationship_conflict'


def test_face_catalog_selects_opposite_planes_for_wall(tmp_path):
    entity=box(tmp_path,'wall',0)
    first=check_step_entities([entity])['entities'][0]
    assert len(first['faces'])==6
    assert [f['id']for f in first['faces']]==list(range(1,7))
    assert all(f['geometry_type'].endswith('Plane')for f in first['faces'])
    assert all(f['area_mm2']==pytest.approx(1,abs=1e-8)for f in first['faces'])
    ordered=sorted(first['faces'],key=lambda f:f['center_mm'][0])
    entity['wall_requests']=[dict(id='wall',faces=[ordered[0]['id'],ordered[-1]['id']])]
    measured=check_step_entities([entity])['entities'][0]['wall_measurements'][0]
    assert measured['state']=='measured'
    assert measured['interval_mm'][0]<=1<=measured['interval_mm'][1]


def test_native_box_volume_and_verified_nested_relation():
    def entity(id,half,length,z):
        return dict(id=id,source='native_NCE_analytic_box',native_definition=dict(kind='box',half_x_mm=half,half_y_mm=half,length_mm=length,rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,z]))
    entities=[entity('O1',2,6,0),entity('O2',1,2,2)]
    result=check_step_entities(entities,relations=[dict(kind='nested',entities=['O1','O2'],native_verified=True)])
    assert result['state']=='passed',result
    assert result['entities'][0]['volume_mm3']==pytest.approx(96,abs=1e-6)
    assert result['pairs'][0]['intersection_volume_mm3']==pytest.approx(8,abs=1e-6)
    assert check_step_entities(entities,relations=[dict(kind='nested',entities=['O1','O2'],native_verified=False)])['state']=='failed'


def test_native_inside_relation_does_not_allow_partial_containment(tmp_path):
    result=check_step_entities([box(tmp_path,'a',0),box(tmp_path,'b',.5)],relations=[dict(kind='nested',entities=['a','b'],native_verified=True)])
    assert result['state']=='failed'
    assert result['pairs'][0]['reason']=='nested_region_not_contained'


def test_material_regions_subtract_native_child_volume():
    def e(id,half,length,z,material,parent=None):
        return dict(id=id,material=material,inside_of=parent,native_definition=dict(kind='box',half_x_mm=half,half_y_mm=half,length_mm=length,rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,z]))
    result=check_step_entities([e('O1',2,6,0,'N-BK7'),e('O2',1,2,2,'N-F2','O1')],relations=[dict(kind='nested',entities=['O1','O2'],native_verified=True)])
    assert [r['material']for r in result['media']]==['N-BK7','N-F2']
    assert [r['effective_volume_mm3']for r in result['media']]==pytest.approx([88,8],abs=1e-6)
    assert result['media'][1]['parent']=='O1'
    normals=[f['outward_normal']for f in result['entities'][0]['faces']]
    assert all(sum(v*v for v in n)==pytest.approx(1,abs=1e-8)for n in normals)
    assert any(n==[0,0,-1]for n in normals)and any(n==[0,0,1]for n in normals)


def test_medium_region_missing_native_parent_is_explicit(tmp_path):
    entity=box(tmp_path,'orphan',0);entity.update(material='N-BK7',inside_of='missing')
    result=check_step_entities([entity])
    assert result['media_state']=='unverified'
    assert result['media'][0]['reason']=='medium_parent_missing'
    assert 'effective_volume_mm3'not in result['media'][0]


def test_contact_material_boundary_mapping_matches_independent_face_area(tmp_path):
    a=box(tmp_path,'a',0);b=box(tmp_path,'b',1)
    a['material']='N-BK7';b['material']='N-F2'
    result=check_step_entities([a,b],relations=[dict(kind='contact',entities=['a','b'])])
    assert result['state']=='passed'
    assert result['media_state']=='measured'
    for m in result['media']:
        interface=m['interfaces'][0]
        assert interface['state']=='mapped'
        assert sum(p['area_mm2']for p in interface['patches'])==pytest.approx(1,abs=1e-8)
        assert {f['material']for p in interface['patches']for f in p['faces']}=={'N-BK7','N-F2'}


def test_native_containment_direction_checks_child_volume(tmp_path):
    result=check_step_entities([box(tmp_path,'host',0),box(tmp_path,'child',0,size=2)],relations=[dict(kind='nested',entities=['host','child'],native_verified=True,native_child='child')])
    assert result['state']=='failed'
    assert result['pairs'][0]['reason']=='nested_region_not_contained'


def test_selected_solid_gap_and_global_box_region(tmp_path):
    a=box(tmp_path,'a',0);b=box(tmp_path,'b',3)
    region=dict(x_min_mm=-1,x_max_mm=5,y_min_mm=.2,y_max_mm=.8,z_min_mm=.2,z_max_mm=.8)
    result=check_step_entities([a,b],gap_requests=[dict(id='full',entities=['a','b']),dict(id='clip',entities=['a','b'],region=region)])
    assert len(result['gap_measurements'])==2
    for measured in result['gap_measurements']:
        assert measured['state']=='measured'
        assert measured['interval_mm'][0]<=2<=measured['interval_mm'][1]
        assert measured['distance_mm']==pytest.approx(2,abs=1e-8)


def test_selected_solid_region_empty_is_not_a_zero_gap(tmp_path):
    region=dict(x_min_mm=20,x_max_mm=30,y_min_mm=0,y_max_mm=1,z_min_mm=0,z_max_mm=1)
    result=check_step_entities([box(tmp_path,'a',0),box(tmp_path,'b',3)],gap_requests=[dict(id='clip',entities=['a','b'],region=region)])
    assert result['gap_measurements'][0]['reason']=='region_has_no_selected_solid'
    assert 'distance_mm'not in result['gap_measurements'][0]


def test_noncoaxial_patch_distance_uses_global_transform():
    from zemax_mcp.geometry_patches import measure_surface_gap
    import math
    base=dict(radius=0,conic=0,quadratic=0,coefficients=[],mechanical_semi_diameter=2,rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,0])
    a=math.radians(20);c=math.cos(a);s=math.sin(a)
    back=dict(base,rotation=[c,0,s,0,1,0,-s,0,c],translation_mm=[0,0,3])
    measured=measure_surface_gap(dict(id='gap',front=base,back=back,scale_mm=1,target_mm=1e-6))
    expected=3-2*s
    assert measured['interval_mm'][0]<=expected<=measured['interval_mm'][1]


@pytest.mark.parametrize('region,xmax',[(dict(x_min_mm=0,x_max_mm=1,y_min_mm=-.1,y_max_mm=.1),1),(dict(r_min_mm=1,r_max_mm=1.5),1.5)])
def test_tilted_patch_region_uses_each_native_local_frame(region,xmax):
    from zemax_mcp.geometry_patches import measure_surface_gap
    import math
    a=math.pi/9;c=math.cos(a);s=math.sin(a)
    base=dict(radius=0,conic=0,quadratic=0,coefficients=[],mechanical_semi_diameter=2,rotation=[1,0,0,0,1,0,0,0,1],translation_mm=[0,0,0])
    back=dict(base,rotation=[c,0,s,0,1,0,-s,0,c],translation_mm=[0,0,3])
    result=measure_surface_gap(dict(id='gap',front=base,back=back,scale_mm=1,target_mm=1e-6,region=region))
    expected=3-xmax*s
    assert result['interval_mm'][0]<=expected<=result['interval_mm'][1]
