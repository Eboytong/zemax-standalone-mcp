from types import SimpleNamespace as N
from pathlib import Path
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.models import EngineeringPolicy


def backend(tmp_path, thickness):
    def surface(radius,z,thick,material=''):
        return N(Type='Standard',Radius=radius,Conic=0,SemiDiameter=5,
                 MechanicalSemiDiameter=5,Thickness=thick,Material=material,
                 ApertureData=N(CurrentType='None'),z=z)
    rows=[None,surface(10,0,thickness,'N-BK7'),surface(-10,thickness,5),None]
    lde=N(NumberOfSurfaces=4,GetSurfaceAt=lambda i:rows[i],GetGlobalMatrix=lambda i:(True,1,0,0,0,1,0,0,0,1,0,0,rows[i].z))
    system=N(Mode='Sequential',LDE=lde,MCE=N(CurrentConfiguration=1,NumberOfConfigurations=1),
             SystemData=N(Units=N(LensUnits='Millimeters')))
    b=Backend(Config(Path('unused'),tmp_path),N(system=system))
    b.session_id='test-session';b.revision=8
    return b




def test_full_native_observation_and_mutation_expiry(tmp_path):
    b=backend(tmp_path,4)
    assert b._check_geometry_now()['state']=='passed'
    b._checkpoint=lambda label:None
    b._mutate('update_surfaces')
    assert b.geometry_summary()['state']=='expired'
    assert b._check_geometry_now()['state']=='passed'
    assert b.geometry_summary()['model_revision']==9


def test_legacy_point_query_and_system_request_validation():
    assert COMMAND_MODELS['get_surface_geometry'].model_validate({'surface':1}).scope=='surface'
    assert COMMAND_MODELS['get_surface_geometry'].model_validate({'scope':'system'}).surface is None
    with pytest.raises(ValueError):COMMAND_MODELS['get_surface_geometry'].model_validate({'scope':'system','surface':1})


def test_engineering_boundary_facts_and_index_invalidation(tmp_path):
    b=backend(tmp_path,4)
    b._engineering_policy=EngineeringPolicy(version=1,constraints=[dict(id='edge',kind='min_thickness',surface=1,value_mm=2,source='fixture dimensions',reason='specified minimum')])
    fact=b._check_geometry_now()
    assert fact['state']=='passed'
    assert fact['engineering_state']=='violated'
    b._checkpoint=lambda _:None
    b._mutate('insert')
    fact=b._check_geometry_now()
    assert fact['engineering_state']=='unverified'




def test_multi_configuration_checks_restore_selection(tmp_path):
    b=backend(tmp_path,4)
    b.request_id='check';b.directory=tmp_path;b.get_system_settings=lambda _:{}
    b.system.MCE.NumberOfConfigurations=2
    def select(i):b.system.MCE.CurrentConfiguration=i
    b.system.MCE.SetCurrentConfiguration=select
    req=COMMAND_MODELS['get_surface_geometry'].model_validate({'scope':'system','configuration_scope':'required'})
    task=b.start_geometry_check(req)
    import time
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        b.tick()
        if not b.active:break
        time.sleep(.01)
    assert b.tasks[task['task_id']]['state']=='succeeded'
    assert b.system.MCE.CurrentConfiguration==1
    assert b.geometry_summary()['checked_configurations']==[1,2]
    assert b.geometry_summary()['state']=='passed'


def test_pure_geometry_process_cancel_keeps_native_connection_known(tmp_path):
    b=backend(tmp_path,4)
    b.request_id='cancel';b.directory=tmp_path;b.get_system_settings=lambda _:{}
    task=b.start_geometry_check(COMMAND_MODELS['get_surface_geometry'].model_validate({'scope':'system'}))
    b.tick();b.tick()
    process=b.tasks[task['task_id']]['geometry_process']
    b.cancel_task(COMMAND_MODELS['cancel_task'].model_validate({'task_id':task['task_id']}))
    b.tick()
    assert b.tasks[task['task_id']]['state']=='cancelled'
    assert process.poll() is not None
    assert b.requires_reconnect is False


def test_unequal_solid_edges_require_actual_edge_profile(tmp_path):
    b=backend(tmp_path,4)
    b._row(1).MechanicalSemiDiameter=6
    fact=b._check_geometry_now()
    assert fact['state']=='unverified'
    assert 'unequal_mechanical_boundaries_require_edge_profile' in fact['rows'][0]['issues']


def test_summary_does_not_embed_mesh_pair_details(tmp_path):
    b=backend(tmp_path,4)
    b._geometry_fact=dict(state='unverified',session_id=b.session_id,model_revision=b.revision,
                          mesh_diagnostics=dict(state='unverified',pairs=[{'data':'x'*10000}],entity_count=1),issues=[],rows=[])
    assert 'mesh_diagnostics' not in b.geometry_summary()
    assert b.geometry_summary()['mesh_summary']['entity_count']==1


def test_upper_limit_straddling_interval_stays_unverified(tmp_path, monkeypatch):
    from zemax_mcp import geometry
    b=backend(tmp_path,4)
    b._engineering_policy=EngineeringPolicy(version=1,constraints=[dict(
        id='slope',kind='max_surface_slope',surface=1,value=.2,unit='rad',source='fixture',reason='boundary')])
    monkeypatch.setattr(geometry,'surface_metric_bounds',lambda *args:[.19,.21])
    fact=b._check_geometry_now()
    assert fact['engineering_checks'][0]['state']=='unverified'
    assert fact['engineering_checks'][0]['actual_interval']==[.19,.21]
    assert 'actual_interval_mm' not in fact['engineering_checks'][0]


def test_no_applicable_constraints_do_not_certify_coverage(tmp_path):
    b=backend(tmp_path,4)
    b._engineering_policy=EngineeringPolicy(version=1,constraints=[dict(
        id='ct',kind='min_center_thickness',surface=1,value_mm=.5,configurations=[2],source='fixture',reason='condition')])
    fact=b._check_geometry_now()
    assert fact['engineering_state']=='unverified'
    assert fact['engineering_checks'][0]['state']=='not_applicable'


def test_full_check_does_not_omit_mirror_entity(tmp_path):
    import time
    b=backend(tmp_path,4);b._row(2).Material='MIRROR'
    b.request_id='mirror';b.directory=tmp_path;b.get_system_settings=lambda _:{}
    task=b.start_geometry_check(COMMAND_MODELS['get_surface_geometry'](scope='system',check='full'))
    deadline=time.monotonic()+10
    while b.active and time.monotonic()<deadline:
        b.tick();time.sleep(.005)
    fact=b._full_result(task['task_id'])['geometry']
    assert fact['state']=='unverified'
    assert any(i['code']=='physical_entity_adapter_required' and i['surface']==2 for i in fact['issues'])


@pytest.mark.parametrize('bad_sag',[False,True])
def test_localized_asphere_headers_require_native_sag_agreement(tmp_path,bad_sag):
    import math
    b=backend(tmp_path,4);b._row(1).Type='EvenAspheric'
    def cell(row,key):
        n=int(key.split('_')[1])
        return N(IsActive=n<=8,Header=f'{2*n}阶项',value=.002 if n==1 else -.00001 if n==2 else 0)
    b._cell=cell;b._cell_value=lambda c:c.value
    b.system.LDE.GetSag=lambda i,r,y:(True,10-math.sqrt(100-r*r)+.002*r*r-.00001*r**4+(1 if bad_sag else 0),0)
    fact=b._check_geometry_now()
    assert fact['state']==('unverified' if bad_sag else 'passed')
    if bad_sag:assert 'native_sag_contract_mismatch' in fact['issues'][0]['reason']


def test_wall_measurement_rejects_same_face_pair():
    from zemax_mcp.models import EngineeringBoundary
    with pytest.raises(ValueError,match='两个不同'):
        EngineeringBoundary(id='wall',kind='min_wall_thickness',surface=1,faces=[2,2],value_mm=1,source='drawing',reason='minimum wall')


@pytest.mark.parametrize('extra,reason',[
    ({'other_surface':4},'selected_boundary_unavailable'),
    ({'region':{'x_min':1}},'engineering_region_adapter_required'),
])
def test_gap_scope_cannot_silently_use_adjacent_full_face(tmp_path,extra,reason):
    b=backend(tmp_path,4)
    b._engineering_policy=EngineeringPolicy(version=1,constraints=[dict(id='gap',kind='min_gap',surface=2,value_mm=1,source='drawing',reason='clearance',**extra)])
    check=b._check_geometry_now()['engineering_checks'][0]
    assert check['state']=='unverified'
    assert check['reason']==reason
    assert 'actual_interval'not in check


def test_duplicate_engineering_rule_identity_rejected():
    rule=dict(id='gap',kind='min_gap',surface=2,value_mm=1,source='drawing',reason='clearance')
    with pytest.raises(ValueError,match='编号不能重复'):
        EngineeringPolicy(version=1,constraints=[rule,rule])


@pytest.mark.parametrize('value',[0,-1,1e-10,1,float('inf'),float('nan')])
def test_geometry_representation_tolerance_range(value):
    with pytest.raises(ValueError):COMMAND_MODELS['get_surface_geometry'](scope='system',representation_tolerance_mm=value)


@pytest.mark.parametrize('extra',[
    {'object':1,'other_object':1},
    {'object':1,'other_object':2,'region':{'x_min_mm':0}},
    {'surface':1,'region':{'x_min_mm':0}},
    {'object':1,'other_object':2,'other_surface':3},
])
def test_gap_target_and_region_model_constraints(extra):
    from zemax_mcp.models import EngineeringBoundary
    with pytest.raises(ValueError):EngineeringBoundary(id='gap',kind='min_gap',value_mm=1,source='drawing',reason='clearance',**extra)
