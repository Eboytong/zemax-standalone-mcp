"""Material-side manufacturing depth uses original local coordinates."""
import math
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.sag_table import removal_orientation, run_sag_table, sphere_at, slope_query_system
from zemax_mcp.analysis_models import RunAnalysis


@pytest.mark.parametrize('direction', [1, -1])
def test_signed_depth_direction(direction):
    summary = dict(curvature=.025, vertex_offset=.002, maximum_removal_depth=.003)
    samples = [(y, sphere_at(.025, y)[0] + .002 + direction * .001 * y) for y in (1., 2., 3.)]
    result = removal_orientation(summary, samples)
    assert result['direction'] == direction
    assert [w['signed_depth'] for w in result['witnesses']] == pytest.approx([direction * .001 * y for y in (1., 2., 3.)])


def test_plane_zero_depth_is_neutral():
    result = removal_orientation(dict(curvature=0., vertex_offset=0., maximum_removal_depth=0.), [(0., 0.), (3., 0.)])
    assert result['direction'] == 1 and result['zero_depth_state']


def test_crossing_blank_is_explicit_failure():
    with pytest.raises(ZemaxError) as info:
        removal_orientation(dict(curvature=0., vertex_offset=0., maximum_removal_depth=.1), [(1., -.01), (2., .01)])
    assert info.value.code == 'INVALID_RESULT_DATA'
    assert len(info.value.details['witnesses']) == 2


@pytest.mark.parametrize('samples', [[], [(1., math.nan)], [(1., math.inf)]])
def test_invalid_witnesses(samples):
    with pytest.raises(ZemaxError):
        removal_orientation(dict(curvature=0., vertex_offset=0., maximum_removal_depth=.1), samples)


@pytest.mark.parametrize('direction', [1, -1])
def test_result_rows_preserve_signed_deviation_and_positive_removal(direction):
    task = dict(context=dict(lens_units='Millimeters', configuration=1), rows=[])
    def composite(kind, settings, flow):
        for _ in flow(task):
            pass
        return task
    backend = NS(_require_sequential=lambda: None, _require_work=lambda: None,
        _row=lambda n: NS(SemiDiameter=5., Type='Standard', ApertureData=NS(CurrentType='None', IsPickedUp=False)),
        native=NS(api=NS(Editors=NS(MFE=NS(MeritOperandType=object()))), enum=lambda owner,name: name),
        system=NS(MFE=NS(GetOperandValue=lambda *args: 0.),
                  LDE=NS(GetSag=lambda surface,x,y: (True, direction*.001*(x*x+y*y), 0.))),
        _cancel_boundary=lambda t: None, _composite=composite)
    run_sag_table(backend, RunAnalysis(request=dict(kind='sag_table', surface=1, samples=3)).request)
    assert task['payload']['manufacturing_direction']['direction'] == direction
    for row in task['rows']:
        assert row['removal_depth'] == pytest.approx(.001*row['y']**2)
        assert row['signed_vertex_deviation'] == pytest.approx(direction*row['removal_depth'])
        assert row['deviation'] == pytest.approx(row['signed_vertex_deviation'])


def floating_copy(*, adopt=True, wrong_radius=False):
    events = []
    aperture = NS(CurrentType='FloatingAperture', SetPickupNone=lambda: events.append('pickup'))
    aperture.CreateApertureTypeSettings = lambda kind: NS(kind=kind, _S_CircularAperture=NS())
    def change(setting):
        events.append(setting.kind)
        if setting.kind == 'CircularAperture':
            if not adopt:
                return False
            aperture.CurrentType = 'CircularAperture'
            aperture.CurrentTypeSettings = setting
            if wrong_radius:
                setting._S_CircularAperture.MaximumRadius = 2.
        return True
    aperture.ChangeApertureTypeSettings = change
    copy = NS(SystemID=2, MCE=NS(CurrentConfiguration=1),
              LDE=NS(GetSurfaceAt=lambda n: NS(ApertureData=aperture)), Close=lambda save: events.append('close') or True)
    backend = NS(system=NS(SystemID=1, MCE=NS(CurrentConfiguration=1), CopySystem=lambda: copy),
                 native=NS(api=NS(Editors=NS(LDE=NS(SurfaceApertureTypes=object()))), enum=lambda owner,name: name),
                 _release_owned=lambda owned: owned.Close(), requires_reconnect=False)
    task = dict(payload=dict(actual_settings=dict(effective_radius_range=[0., 5.])))
    return backend, task, dict(aperture=dict(type='FloatingAperture')), events


def test_floating_stop_uses_adopted_enclosing_circle_and_closes():
    backend, task, context, events = floating_copy()
    with slope_query_system(backend, 2, task, context):
        result = task['payload']['slope_query_copy']
        assert result['actual_copy_circle'] == dict(minimum_radius=0., maximum_radius=5.000005, x_decenter=0., y_decenter=0.)
        assert result['queried_radius_range'] == [0., 5.]
    assert events == ['pickup', 'None', 'CircularAperture', 'close']
    assert task['payload']['slope_query_copy']['closed']


@pytest.mark.parametrize('patch', [dict(adopt=False), dict(wrong_radius=True)])
def test_floating_fallback_refusal_preserves_close(patch):
    backend, task, context, events = floating_copy(**patch)
    with pytest.raises(ZemaxError) as info:
        with slope_query_system(backend, 2, task, context):
            pytest.fail('unadopted aperture reached query')
    assert info.value.code == 'SETTING_REJECTED'
    assert events[-1] == 'close'
    assert task['payload']['slope_query_copy']['closed']


def test_floating_stop_cancel_closes_copy():
    backend, task, context, events = floating_copy()
    original = ZemaxError('TASK_CANCELLED', 'cancelled')
    with pytest.raises(ZemaxError) as info:
        with slope_query_system(backend, 2, task, context):
            raise original
    assert info.value is original and events[-1] == 'close'
