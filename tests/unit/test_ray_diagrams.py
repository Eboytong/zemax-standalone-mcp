import math
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.ray_diagrams import signed_plane_angle,native_query
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('q',[dict(kind='yybar_diagram',last_surface=0),dict(kind='yybar_diagram',plot_scale=-1),
    dict(kind='yybar_diagram',wavelength=0),dict(kind='yybar_diagram',field_density=20),
    dict(kind='incident_angle_vs_image_height',first_surface=2),dict(kind='incident_angle_vs_image_height',field_density=1),
    dict(kind='incident_angle_vs_image_height',field_density=1002),dict(kind='incident_angle_vs_image_height',wavelength=0)])
def test_ray_diagram_request_boundaries(q):
    with pytest.raises(ValidationError):RunAnalysis(request=q)

@pytest.mark.parametrize('angle',[-70,-15,0,15,70])
def test_incidence_signed_forward_and_backward_local_plane(angle):
    a=math.radians(angle)
    assert signed_plane_angle([0,math.sin(a),math.cos(a)])==pytest.approx(angle)
    assert signed_plane_angle([0,-math.sin(a),-math.cos(a)])==pytest.approx(angle)

@pytest.mark.parametrize('v',[[0,float('nan'),1],[0,.1,1],[0,0,0]])
def test_invalid_direction_is_not_reported_as_zero_angle(v):
    with pytest.raises(ZemaxError):signed_plane_angle(v)

@pytest.mark.parametrize('value',[float('nan'),float('inf')])
def test_ray_operand_nonfinite_result_retains_parameter_identity(value):
    b=NS(system=NS(MFE=NS(GetOperandValue=lambda code,*args:value)))
    with pytest.raises(ZemaxError) as exc:native_query(b,'PARY',[1,1,0,1,0,0,0,0])
    assert exc.value.code=='INVALID_RESULT_DATA' and exc.value.details['operand']=='PARY'

def test_ray_operand_original_failure_is_preserved():
    def fail(code,*args):raise RuntimeError('lens-query-native-test')
    b=NS(system=NS(MFE=NS(GetOperandValue=fail)))
    with pytest.raises(ZemaxError)as exc:native_query(b,'PARY',[1,1,0,1,0,0,0,0])
    assert exc.value.details['native_exception']=='lens-query-native-test'


def test_yybar_paged_surface_annotation_tracks_points(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.models import TaskResult
    b=Backend(Config(tmp_path,tmp_path/'out'))
    curve=dict(x=[0,1,2],y=[[3],[4],[5]],point_labels=['1','2','3'])
    page=b._page_task_result(dict(series=[curve]),TaskResult(task_id='a',series=0,start=1,count=1))['series'][0]
    assert page['point_labels']==['2'] and page['x']==[1] and page['y']==[[4]]
    assert curve['point_labels']==['1','2','3']


@pytest.mark.parametrize('trace_error,close_ok',[(False,True),(True,True),(True,False),(False,False),('cancelled',False),('runtime',False)])
def test_incident_copy_close_and_original_failure(trace_error,close_ok):
    from types import MethodType
    from zemax_mcp.ray_diagrams import incoming_trace
    state=dict(copy_closed=0,tool_closed=0)
    row=NS(Type='Standard',Material='N-BK7',MaterialCell=NS(GetSolveData=lambda:NS(Type='Fixed')))
    def copy_close(save):state['copy_closed']+=1;return close_ok
    copy=NS(SystemID=4,LDE=NS(GetSurfaceAt=lambda n:row),Close=copy_close)
    source=NS(SystemID=3,LDE=NS(GetSurfaceAt=lambda n:NS(Type='Standard',Material='N-BK7')),CopySystem=lambda:copy)
    def trace(owner,task,request,target):
        assert owner.system is copy and row.Material==''
        def close():state['tool_closed']+=1;return True
        owner._close_task_native(dict(native=NS(Close=close)))
        if trace_error is True:raise ZemaxError('TASK_FAILED','original-trace-error')
        if trace_error=='cancelled':
            from zemax_mcp.evaluation import Cancelled
            raise Cancelled()
        if trace_error=='runtime':raise RuntimeError('native-runtime-original')
        if False:yield
    def composite(kind,settings,factory):
        for _ in factory({}):pass
        return dict(rows=[],task=dict(task_id='child'))
    def child(parent,method,q):
        if False:yield
        return method(q)
    def release(owned):
        if not owned.Close():raise ZemaxError('CLEANUP_FAILED','copy-close-failed')
    b=NS(system=source,native=NS(),_composite=composite,_child_job=child,_trace_flow=MethodType(trace,NS()),
         _cancel_boundary=lambda task:None,_close_task_native=lambda task:task['native'].Close(),_release_owned=release,requires_reconnect=False)
    parent=dict(payload={});request=NS(model_dump=lambda:{})
    if trace_error or not close_ok:
        with pytest.raises(ZemaxError)as exc:
            for _ in incoming_trace(b,parent,request,2):pass
        assert exc.value.code==('TASK_FAILED'if trace_error is True else 'CLEANUP_FAILED')
        if trace_error and not close_ok:assert exc.value.details['cleanup_error']=='copy-close-failed'
        if trace_error in ('cancelled','runtime'):
            assert exc.value.details['original_error']['type']==('Cancelled'if trace_error=='cancelled'else'RuntimeError')
    else:
        for _ in incoming_trace(b,parent,request,2):pass
    assert state==dict(copy_closed=1,tool_closed=1)
    assert parent['payload']['incoming_trace_copy']['closed']==close_ok
    assert b.requires_reconnect==(not close_ok)


@pytest.mark.parametrize('mode',['all_error','chief_missing','invalid_normal'])
def test_incident_invalid_rays_keep_original_codes_and_never_create_zero_curve(mode):
    from zemax_mcp.ray_diagrams import run_incident_angle
    task=dict(context=dict(lens_units='Millimeters',configuration=1),
        system_settings=dict(fields=[dict(x=0,y=20)],field_type='Angle',field_normalization='Radial',wavelengths=[dict(wavelength_um=.55)]),rows=[])
    rays=[]
    for i in range(6):
        error=mode=='all_error' or (mode=='chief_missing' and i%3==1)
        rays.append(dict(index=i,error_code=42 if error else 0,vignette_code=0,state='error'if error else'succeeded',
            position=None if error else[0,0,0],direction=None if error else[0,0,1],
            surface_normal=None if error else[.1,0,math.sqrt(.99)]if mode=='invalid_normal'else[0,0,1]))
    def child(parent,method,q):
        if False:yield
        return dict(rows=rays,task=dict(task_id='native-child'))
    def composite(kind,settings,factory):
        for _ in factory(task):pass
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,_row=lambda n:NS(Radius=float('inf')),
        system=NS(LDE=NS(NumberOfSurfaces=3,GetSurfaceAt=lambda n:NS(Type='Standard',Material='')),
                  SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1))),
        _composite=composite,_child_job=child,run_batch_ray_trace=lambda q:None,_cancel_boundary=lambda t:None)
    with pytest.raises(ZemaxError)as exc:
        run_incident_angle(b,RunAnalysis(request=dict(kind='incident_angle_vs_image_height',field_density=2)).request)
    assert exc.value.code=='NO_VALID_RAYS' and len(task['rows'])==2
    assert exc.value.details['counts']['invalid'if mode=='invalid_normal'else'error']==(2 if mode=='chief_missing'else 6)
    assert all(r['chief_angle_deg']is None for r in task['rows'])
    if mode!='invalid_normal':assert all(r['rays'][1]['error_code']==42 for r in task['rows'])
