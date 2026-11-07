import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.power_maps import arguments,axis


def test_tangent_field_coordinates_use_physical_angle_for_native_queries():
    import math
    from zemax_mcp.power_maps import field_axes
    q=RunAnalysis(request=dict(kind='power_field_map',surface=1,x_field_width=120,
        y_field_width=80,x_points=5,y_points=3,use_tangent_of_field_angle=True)).request
    x,y,fx,fy,unit=field_axes(q,dict(field_type='Angle',lens_units='Millimeters'))
    assert unit=='dimensionless tangent'
    assert x==pytest.approx([-math.sqrt(3),-math.sqrt(3)/2,0,math.sqrt(3)/2,math.sqrt(3)])
    assert fx==pytest.approx([-60,-40.8933946491,0,40.8933946491,60])
    assert fy==pytest.approx([-40,0,40])
    assert arguments(q,fx[1]/60,fy[1]/60)[2:4]==pytest.approx([-40.8933946491/60,0])


@pytest.mark.parametrize('field_type,width,code',[
    ('ObjectHeight',40,'INACTIVE_SETTING'),('Angle',180,'INVALID_ARGUMENT'),
    ('Angle',200,'INVALID_ARGUMENT')])
def test_tangent_field_rejects_inactive_and_singular_domains(field_type,width,code):
    from zemax_mcp.power_maps import field_axes
    from zemax_mcp.errors import ZemaxError
    q=RunAnalysis(request=dict(kind='power_field_map',surface=1,x_field_width=width,
        y_field_width=20,use_tangent_of_field_angle=True)).request
    with pytest.raises(ZemaxError) as caught:
        field_axes(q,dict(field_type=field_type,lens_units='Millimeters'))
    assert caught.value.code==code


def test_tangent_setting_is_field_map_only():
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='power_pupil_map',surface=1,use_tangent_of_field_angle=True))

@pytest.mark.parametrize('extra',[dict(surface=0),dict(wavelength=0),dict(x_points=2),dict(y_points=130),dict(x_points=3.5),dict(offset=float('inf')),dict(data_type='Watts'),dict(field=1)])
def test_power_field_boundaries(extra):
    q=dict(kind='power_field_map',surface=2,x_field_width=10,y_field_width=5);q.update(extra)
    with pytest.raises(ValidationError):RunAnalysis(request=q)

@pytest.mark.parametrize('kind',['power_field_map','power_pupil_map'])
@pytest.mark.parametrize('data,quantity,code',[('Spherical','Power',0),('Tangential','EFL',13),('Astigmatic','Power',8),('Cylinder','EFL',10)])
def test_native_argument_identity(kind,data,quantity,code):
    kw=dict(x_field_width=10,y_field_width=5) if kind=='power_field_map' else dict(field=2)
    q=RunAnalysis(request=dict(kind=kind,surface=3,wavelength=2,data_type=data,quantity=quantity,**kw)).request
    a=arguments(q,.2,-.3,.4,-.5)
    assert a==([3,2,.2,-.3,float(code),0,0,0] if kind=='power_field_map' else [3,2,.2,-.3,.4,-.5,float(code),0])

def test_grid_endpoints_and_non_square_resolution():
    assert axis(6,3)==[-3,0,3]
    assert len(axis(8,5))==5 and axis(8,5)[-1]==4


def test_power_validity_mask_region_and_summary(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.models import TaskResult
    b=Backend(Config(tmp_path,tmp_path/'out'))
    g=dict(nx=3,ny=2,values=[[1,None,2],[3,4,None]],valid_mask=[[True,False,True],[True,True,False]])
    result=dict(grids=[g])
    summary=b._page_task_result(result,TaskResult(task_id='a'))
    assert 'valid_mask' not in summary['grids'][0] and summary['grids'][0]['valid_mask_in_artifacts']
    region=b._page_task_result(result,TaskResult(task_id='a',grid=0,x_start=1,y_start=0,width=2,height=1))['grid']
    assert region['values']==[[None,2]] and region['valid_mask']==[[False,True]]


def fake_power_trace(raw=0.,invalid_center=False):
    from types import SimpleNamespace as NS
    from zemax_mcp.power_maps import run_power_map
    task=dict(context=dict(configuration=1),rows=[])
    settings=dict(wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0.,y=1.)],
        lens_units='Millimeters',field_type='Angle',field_normalization='Radial')
    def composite(kind,request,flow):
        for unused in flow(task):pass
        return task
    def child(parent,launch,request):
        yield
        return dict(rows=[dict(error_code=1 if invalid_center and r.px==r.py==0 else 0,vignette_code=0)
            for r in request.rays])
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,_row=lambda i:None,
        get_system_settings=lambda req:settings,native=NS(api=NS(Editors=NS(MFE=NS(MeritOperandType=object()))),
        enum=lambda owner,name:name),system=NS(MFE=NS(GetOperandValue=lambda *args:raw)),
        _cancel_boundary=lambda task:None,_composite=composite,_child_job=child,run_batch_ray_trace=lambda req:None)
    return b,task


@pytest.mark.parametrize('quantity',['Power','EFL'])
def test_power_native_zero_identity_survives_output_offset(quantity):
    from zemax_mcp.power_maps import run_power_map
    b,t=fake_power_trace()
    q=RunAnalysis(request=dict(kind='power_pupil_map',surface=1,quantity=quantity,offset=7,x_points=3,y_points=3)).request
    run_power_map(b,q)
    assert len(t['rows'])==5
    for row in t['rows']:
        assert row['raw_value']==0 and row['value']==7
        assert row['raw_value_state']=='native_zero'
        assert row['zero_interpretation']=='unresolved_native_zero_semantics'
        assert row['native_query_status']=='returned_finite_value'
    grid=t['payload']['grids'][0]
    assert grid['native_zero_count']==5 and grid['values'][1][1]==7
    assert grid['valid_mask'][1][1]and grid['native_ring_validity']=='unavailable'
    assert 'peripheral native ring status unavailable'in grid['valid_mask_scope']


def test_power_invalid_reference_ray_remains_distinct_from_native_zero():
    from zemax_mcp.power_maps import run_power_map
    b,t=fake_power_trace(invalid_center=True)
    q=RunAnalysis(request=dict(kind='power_pupil_map',surface=1,x_points=3,y_points=3)).request
    run_power_map(b,q)
    center=t['rows'][2]
    assert center['state']=='invalid_reference_ray'
    assert center['native_query_status']=='not_executed_invalid_reference_ray'
    assert center['raw_value_state']=='not_queried'and center['raw_value']is None
    grid=t['payload']['grids'][0]
    assert grid['invalid_reference_ray_count']==1 and grid['native_zero_count']==4
    assert grid['values'][1][1]is None and not grid['valid_mask'][1][1]


def test_power_finite_nonzero_value_retains_validation_scope():
    from zemax_mcp.power_maps import run_power_map
    b,t=fake_power_trace(raw=-6.)
    q=RunAnalysis(request=dict(kind='power_pupil_map',surface=1,x_points=3,y_points=3)).request
    run_power_map(b,q)
    assert all(r['raw_value_state']=='finite_nonzero'for r in t['rows'])
    assert all('zero_interpretation'not in r for r in t['rows'])
    assert t['payload']['grids'][0]['native_zero_count']==0
