import importlib.util
import math
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[2] / 'scripts/probes/PO-01/phase_reference_diagnostics.py'
spec = importlib.util.spec_from_file_location('phase_reference_diagnostics', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def control():
    pupils = [-1., -.005, 0., .005, 1.]
    phase = lambda p: .01 * p * p
    offset = phase(.005)
    return dict(section='sagittal', component='y', indeterminate=0,
                points=[dict(pupil=p, raw=phase(p) - 2 * p * p,
                             propagation_waves=2 * p * p,
                             native=0. if p == 0 else -(phase(p) - offset))
                        for p in pupils])


def test_interpolated_reference_explains_offset_without_changing_tolerance():
    result = probe.diagnose(control())
    assert result['neighbor_reference_waves'] == pytest.approx(2.5e-7, abs=1e-16)
    assert result['chief_maximum_error_waves'] > probe.TOLERANCE_WAVES
    assert result['neighbor_maximum_error_waves'] < 1e-15
    assert result['neighbor_candidate_passed']
    assert result['compared'] == 4
    assert result['chief_marker'] == dict(pupil=0., native=0., is_zero=True,
                                          included_in_nonchief_error=False)


def test_reference_does_not_fit_native_values_or_hide_residual_error():
    data = control()
    baseline = probe.diagnose(data)['neighbor_reference_waves']
    data['points'][0]['native'] += 1e-5
    result = probe.diagnose(data)
    assert result['neighbor_reference_waves'] == baseline
    assert result['neighbor_maximum_error_waves'] == pytest.approx(1e-5)
    assert not result['neighbor_candidate_passed']


def test_zero_amplitude_component_keeps_indeterminate_status():
    result = probe.diagnose(dict(section='sagittal', component='x',
                                 points=[], indeterminate=401))
    assert result['status'] == 'indeterminate'
    assert result['indeterminate'] == 401
    assert 'neighbor_candidate_passed' not in result


def test_reference_interpolation_wraps_at_half_wave():
    data = control()
    for point in data['points']:
        point['propagation_waves'] = 0
        point['raw'] = .499 if point['pupil'] < 0 else -.499
        point['native'] = 0 if point['pupil'] == 0 else math.remainder(.5 - point['raw'], 1.)
    result = probe.diagnose(data)
    assert abs(result['neighbor_reference_waves']) == pytest.approx(.5)
    assert result['neighbor_candidate_passed']


@pytest.mark.parametrize('change', ['missing_chief', 'asymmetric', 'unordered', 'nan', 'opposite'])
def test_invalid_reference_geometry_or_phase_is_rejected(change):
    data = control()
    if change == 'missing_chief':
        del data['points'][2]
    elif change == 'asymmetric':
        data['points'][1]['pupil'] = -.006
    elif change == 'unordered':
        data['points'].reverse()
    elif change == 'nan':
        data['points'][0]['native'] = float('nan')
    else:
        data['points'][1]['raw'] = -data['points'][1]['propagation_waves']
        data['points'][3]['raw'] = .5 - data['points'][3]['propagation_waves']
    with pytest.raises(ValueError):
        probe.diagnose(data)
