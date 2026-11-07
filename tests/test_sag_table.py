import math
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.sag_table import sphere_at

@pytest.mark.parametrize('patch',[dict(surface=0),dict(surface=1,samples=1),dict(surface=1,samples=10002),
    dict(surface=1,minimum_radius=1),dict(surface=1,minimum_radius=2,maximum_radius=1),
    dict(surface=1,maximum_radius=float('inf')),dict(surface=1,best_fit_sphere='bad'),dict(surface=1,best_fit_sphere='MinimumRMS',reverse=True),
    dict(surface=1,best_fit_sphere='MinimumRMS',maximum_radius=5),dict(surface=1,reverse=True,maximum_radius=5)])
def test_sag_table_invalid_request(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='sag_table')|patch)

def test_sag_table_defaults_and_explicit_annulus():
    q=RunAnalysis(request=dict(kind='sag_table',surface=2)).request
    assert q.samples==51 and q.maximum_radius==0
    q=RunAnalysis(request=dict(kind='sag_table',surface=2,minimum_radius=1,maximum_radius=3)).request
    assert q.maximum_radius==3

@pytest.mark.parametrize('c',[0,.025,-.025])
def test_stable_sphere_sag_and_slope(c):
    z,d=sphere_at(c,3.)
    if c==0:assert z==d==0
    else:
        radius=1/c
        assert z==pytest.approx(radius-math.copysign(math.sqrt(radius*radius-9),radius))
        assert d==pytest.approx(c*3/math.sqrt(1-9*c*c))


from types import SimpleNamespace as NS
from zemax_mcp.sag_table import run_sag_table
from zemax_mcp.errors import ZemaxError

def fake_sag(query_error=None,failed_point=None):
    t=dict(context=dict(lens_units='Millimeters',configuration=1),rows=[])
    def native(code,*args):
        if query_error:raise query_error
        return float('inf') if code=='BFSD' and args[1]==1 else 0.
    def sag(surface,x,y):return (y!=failed_point,0.,0.)
    def composite(kind,settings,flow):
        for _ in flow(t):pass
        return t
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,_row=lambda n:NS(SemiDiameter=5.,Type='Standard',
        ApertureData=NS(CurrentType='None',IsPickedUp=False)),
        native=NS(api=NS(Editors=NS(MFE=NS(MeritOperandType=object()))),enum=lambda owner,name:name),
        system=NS(MFE=NS(GetOperandValue=native),LDE=NS(GetSag=sag)),
        _cancel_boundary=lambda task:None,_composite=composite)
    return b,t


def test_sag_table_plane_infinite_radius_serialized_as_state():
    b,t=fake_sag();run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,samples=2)).request)
    assert t['payload']['summary']['radius'] is None and t['payload']['summary']['radius_state']=='infinite'
    assert len(t['rows'])==2 and len(t['payload']['series'])==3


def test_sag_table_native_failure_keeps_arguments_and_original_error():
    b,t=fake_sag(RuntimeError('native-material-failure'))
    with pytest.raises(ZemaxError) as exc:run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1)).request)
    assert exc.value.code=='NATIVE_ERROR' and exc.value.details['operand']=='BFSD'
    assert exc.value.details['native_exception']=='native-material-failure'
    assert exc.value.details['arguments']==[1,0,0,5.,0.,0.,0.,0.]
    assert not t['rows']


def test_sag_table_failed_point_preserves_only_completed_rows():
    b,t=fake_sag(failed_point=5.)
    with pytest.raises(ZemaxError) as exc:run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,samples=2)).request)
    assert exc.value.code=='INVALID_RESULT_DATA' and exc.value.details['y']==5.
    assert len(t['rows'])==1 and t['rows'][0]['y']==0


def test_sag_table_asymmetric_witness_rejected_before_manufacturing_queries():
    b,t=fake_sag()
    b.system.LDE.GetSag=lambda surface,x,y:(True,.001*x*x+.002*y*y,0.)
    with pytest.raises(ZemaxError)as exc:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1)).request)
    assert exc.value.code=='UNSUPPORTED_MODEL'
    assert exc.value.details['witness']['error']>exc.value.details['witness']['tolerance']
    assert t['payload']['rotational_symmetry_check']['state']=='asymmetry_detected'
    assert not t['payload']['summary']and not t['rows']


def test_sag_table_rotational_samples_and_aperture_scope_retained():
    b,t=fake_sag()
    b.system.LDE.GetSag=lambda surface,x,y:(True,.001*(x*x+y*y),0.)
    run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,samples=2)).request)
    checked=t['payload']['rotational_symmetry_check']
    assert checked['state']=='sampled_meridians_agree'and len(checked['samples'])==24
    assert t['payload']['actual_settings']['aperture']==dict(type='None',pickup_from=None)
    assert 'full rotational radial interval'in t['payload']['aperture_interpretation']


def test_sag_table_rotational_probe_preserves_native_failure():
    b,t=fake_sag()
    def failed(*args):raise RuntimeError('native-sag-probe-failed')
    b.system.LDE.GetSag=failed
    with pytest.raises(ZemaxError)as exc:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1)).request)
    assert exc.value.code=='NATIVE_ERROR'
    assert exc.value.details['native_exception']=='native-sag-probe-failed'


def test_sag_table_rotational_probe_observes_cancellation():
    b,t=fake_sag();count=0
    def cancel(task):
        nonlocal count
        count+=1
        if count==3:raise ZemaxError('TASK_CANCELLED','cancelled')
    b._cancel_boundary=cancel
    with pytest.raises(ZemaxError)as exc:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1)).request)
    assert exc.value.code=='TASK_CANCELLED'
    assert len(t['payload']['rotational_symmetry_check']['samples'])==2


from zemax_mcp.sag_table import slope_query_system


def fake_slope_copy(adopt=True,clear_error=None,close_error=None):
    events=[]
    aperture=NS(CurrentType='CircularAperture',SetPickupNone=lambda:events.append('pickup'),
        CreateApertureTypeSettings=lambda kind:kind)
    def change(setting):
        events.append('clear')
        if clear_error:raise clear_error
        if adopt:aperture.CurrentType=setting
        return adopt
    aperture.ChangeApertureTypeSettings=change
    copy=NS(SystemID=2,MCE=NS(CurrentConfiguration=1),
        LDE=NS(GetSurfaceAt=lambda n:NS(ApertureData=aperture)),
        Close=lambda save:events.append('close')or True)
    def release(owned):
        owned.Close()
        if close_error:raise close_error
    b=NS(system=NS(SystemID=1,MCE=NS(CurrentConfiguration=1),CopySystem=lambda:copy),
        native=NS(api=NS(Editors=NS(LDE=NS(SurfaceApertureTypes=object()))),enum=lambda owner,name:name),
        _release_owned=release,requires_reconnect=False)
    return b,dict(payload={}),dict(aperture=dict(type='CircularAperture')),events,copy


def test_sag_table_slope_copy_closes_after_success():
    b,t,c,events,copy=fake_slope_copy()
    with slope_query_system(b,1,t,c)as system:assert system is copy
    assert events==['pickup','clear','close']
    assert t['payload']['slope_query_copy']['closed']


@pytest.mark.parametrize('adopt,error',[(False,None),(True,RuntimeError('clear-failed'))])
def test_sag_table_slope_copy_closes_after_clear_refusal(adopt,error):
    b,t,c,events,copy=fake_slope_copy(adopt,clear_error=error)
    with pytest.raises((ZemaxError,RuntimeError))as exc:
        with slope_query_system(b,1,t,c):pytest.fail('refused settings reached query')
    if error:assert exc.value is error
    else:assert exc.value.code=='SETTING_REJECTED'
    assert events[-1]=='close'and t['payload']['slope_query_copy']['closed']


@pytest.mark.parametrize('code',['TASK_CANCELLED','NATIVE_ERROR'])
def test_sag_table_slope_copy_closes_preserving_original_error(code):
    b,t,c,events,copy=fake_slope_copy();original=ZemaxError(code,'original')
    with pytest.raises(ZemaxError)as exc:
        with slope_query_system(b,1,t,c):raise original
    assert exc.value is original and events[-1]=='close'


def test_sag_table_slope_copy_cleanup_failure_retains_original_and_reconnect():
    b,t,c,events,copy=fake_slope_copy(close_error=RuntimeError('close-failed'))
    original=ZemaxError('NATIVE_ERROR','query-failed')
    with pytest.raises(ZemaxError)as exc:
        with slope_query_system(b,1,t,c):raise original
    assert exc.value is original and exc.value.details['cleanup_error']=='close-failed'
    assert b.requires_reconnect and not t['payload']['slope_query_copy']['closed']


def test_sag_table_slope_copy_closes_when_metadata_getter_fails():
    b,t,c,events,copy=fake_slope_copy();b.system.SystemID=None
    with pytest.raises(TypeError):
        with slope_query_system(b,1,t,c):pytest.fail('invalid metadata reached query')
    assert events==['close']


@pytest.mark.parametrize('criterion,reverse,flag',[('MinimumRMS',False,1),('MinimumRMSWithOffset',False,2),('MinimumVolume',True,3)])
def test_sag_table_formal_criterion_reconstruction(criterion,reverse,flag):
    b,t=fake_sag();calls=[];c=.025
    b.system.LDE.GetSag=lambda surface,x,y:(True,.0126*(x*x+y*y),0.)
    def native(code,*args):
        calls.append((code,args))
        if code=='SSAG':
            assert args[5:7]==(2.,float(flag))
            y=args[3]
            return .0126*y*y-sphere_at(c,y)[0]
        if code=='DSAG':
            assert args in [(1,0,9,1,0,2,flag,0.),(1,0,10,1,0,2,flag,0.)]
            return 1/c if args[2]==9 else -.0002
        assert code=='SSLP'
        return .0252*args[3]
    b.system.MFE.GetOperandValue=native
    q=RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere=criterion,reverse=reverse,samples=3)).request
    run_sag_table(b,q)
    result=t['payload']
    assert result['summary']['curvature']==pytest.approx(c,abs=1e-14)
    assert result['summary']['vertex_offset']==(0. if criterion=='MinimumRMS'else None)
    assert result['manufacturing_state']==('unavailable'if reverse else'not_applicable')
    assert len([code for code,args in calls if code=='SSAG'])==4
    assert all(code!='BFSD'for code,args in calls)
    assert all(row['removal_depth']is None for row in t['rows'])
    if not reverse:
        assert result['native_bfs_fit']['vertex_z_offset']==-.0002
        assert result['native_bfs_fit']['curve_radius_check']['passed']
    else:assert 'native_bfs_fit'not in result
    assert result['series'][1]['labels']==['deviation (Millimeters)']
    assert result['statistics_sampling']['completed_nodes']==1001
    assert result['statistics_sampling']['state']=='succeeded'
    assert result['summary']['maximum_slope_difference']>=0
    assert result['summary']['rms_slope_difference']>=0
    for row in t['rows']:
        assert row['bfs_slope']==pytest.approx(sphere_at(c,row['y'])[1])


def test_sag_table_criterion_query_error_preserves_flag():
    b,t=fake_sag(RuntimeError('ssag-native-failed'))
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,reverse=True)).request)
    assert error.value.details['operand']=='SSAG'
    assert error.value.details['arguments'][6]==3.
    assert error.value.details['native_exception']=='ssag-native-failed'
    assert not t['rows']


def test_sag_table_criterion_inconsistent_sphere_rejected():
    b,t=fake_sag()
    b.system.MFE.GetOperandValue=lambda code,*args:args[3]**4 if code=='SSAG'else 0.
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMS')).request)
    assert error.value.code=='INVALID_RESULT_DATA'
    assert not t['rows']


def test_sag_table_criterion_cancellation_keeps_completed_native_queries():
    b,t=fake_sag();count=0
    def native(code,*args):
        nonlocal count
        assert code=='SSAG'
        count+=1
        return 0.
    b.system.MFE.GetOperandValue=native
    def cancel(task):
        if count==1:raise ZemaxError('TASK_CANCELLED','cancelled during sphere reconstruction')
    b._cancel_boundary=cancel
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMS')).request)
    assert error.value.code=='TASK_CANCELLED'
    assert len(t['payload']['native_query_arguments'])==1
    assert not t['rows']


def test_sag_table_auxiliary_dsag_failure_keeps_original_arguments():
    b,t=fake_sag()
    def native(code,*args):
        if code=='SSAG':return 0.
        raise RuntimeError('dsag-offset-failed')
    b.system.MFE.GetOperandValue=native
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMSWithOffset')).request)
    assert error.value.details['operand']=='DSAG'
    assert error.value.details['arguments']==[1,0,9,1,0,2,2,0.]
    assert error.value.details['native_exception']=='dsag-offset-failed'
    assert len(t['payload']['native_query_arguments'])==4 and not t['rows']


def test_sag_table_auxiliary_cancellation_keeps_completed_radius():
    b,t=fake_sag();calls=[]
    def native(code,*args):
        calls.append((code,args))
        return float('inf')if code=='DSAG'else 0.
    b.system.MFE.GetOperandValue=native
    def cancel(task):
        if len(calls)==5:raise ZemaxError('TASK_CANCELLED','cancelled before DSAG offset')
    b._cancel_boundary=cancel
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMSWithOffset')).request)
    assert error.value.code=='TASK_CANCELLED'
    assert t['payload']['native_bfs_fit']['radius']is None
    assert 'vertex_z_offset'not in t['payload']['native_bfs_fit']
    assert len(t['payload']['native_query_arguments'])==5 and not t['rows']


def test_sag_table_auxiliary_different_radius_retains_raw_offset_without_adoption():
    b,t=fake_sag()
    def native(code,*args):
        if code=='SSAG':return .0126*args[3]**2-sphere_at(.025,args[3])[0]
        if code=='DSAG':return 41. if args[2]==9 else -.0002
        return .0252*args[3]
    b.system.MFE.GetOperandValue=native
    b.system.LDE.GetSag=lambda surface,x,y:(True,.0126*(x*x+y*y),0.)
    run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMSWithOffset',samples=2)).request)
    assert not t['payload']['native_bfs_fit']['curve_radius_check']['passed']
    assert t['payload']['native_bfs_fit']['vertex_z_offset']==-.0002
    assert t['payload']['summary']['vertex_offset']is None


def test_sag_table_slope_summary_cancellation_retains_completed_sampling():
    b,t=fake_sag()
    def cancel(task):
        if task.get('payload',{}).get('statistics_sampling',{}).get('completed_nodes')==2:
            raise ZemaxError('TASK_CANCELLED','slope-summary-cancelled')
    b._cancel_boundary=cancel
    with pytest.raises(ZemaxError)as error:
        run_sag_table(b,RunAnalysis(request=dict(kind='sag_table',surface=1,best_fit_sphere='MinimumRMS',samples=2)).request)
    assert error.value.code=='TASK_CANCELLED'
    assert t['payload']['statistics_sampling']['completed_nodes']==2
    assert 'rms_slope_difference'not in t['payload']['summary']
    assert len(t['rows'])==2
