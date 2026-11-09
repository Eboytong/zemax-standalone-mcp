import cmath
import importlib.util
import math
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[2] / 'scripts/probes/PO-01/phase_propagation_reference.py'
spec = importlib.util.spec_from_file_location('phase_propagation_reference', path)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_path_reference_uses_incident_wavefront_and_each_preceding_medium():
    positions = [[[0, 0, .2], [0, 0, 0]], [[0, 0, 1.2], [0, 0, 2]]]
    assert probe.propagation_differences(positions, [1, 1.5]) == pytest.approx([1.7, 3])
    assert probe.global_position([1, 0, 0, 0, 1, 0, 0, 0, 1, 3, 4, 5], [1, 2, 3]) == [4, 6, 8]


def test_propagation_reference_recovers_known_polarization_phase_across_wrapping():
    points = [dict(section='sagittal', pupil=p, x_phase=0, y_phase=v)
              for p, v in [(-1, .02), (0, 0), (1, -.03)]]
    paths = [.101, .1, .102]
    wave = .00055
    rows = []
    for point, path_length in zip(points, paths):
        field = cmath.exp(2j * math.pi * (path_length / wave + point['y_phase']))
        rows.append(dict(electric_field=dict(ex_real=0, ex_imag=0, ey_real=field.real, ey_imag=field.imag)))
    result = probe.compare_phase(points, rows, paths, wave, count_per_section=3)
    assert result[0]['indeterminate'] == 3
    assert result[0]['passed']['-1'] is False
    assert result[1]['passed']['-1'] is True
    assert result[1]['passed']['1'] is False
    assert result[1]['maximum_errors_waves']['-1'] < 1e-12


def test_path_reference_rejects_incomplete_surface_rows():
    with pytest.raises(ValueError):
        probe.propagation_differences([[[0, 0, 0]], []], [1, 1.5])


def test_oblique_plane_wave_uses_projection_on_incident_direction():
    angle = math.radians(30)
    direction = (0, math.sin(angle), math.cos(angle))
    positions = [[[0, 2, 1]], [[0, 2, 3]]]
    assert probe.propagation_differences(positions, [1, 1.5], direction) == pytest.approx(
        [2 * math.sin(angle) + math.cos(angle) + 3])


def test_launch_plane_travel_differs_by_known_incident_transverse_phase():
    direction=(0, .6, .8)
    positions=[[[0,2,1],[0,0,0]],[[0,2,3],[0,0,2]]]
    wave_paths=probe.propagation_differences(positions,[1,1.5],direction)
    launch_paths=probe.propagation_differences(positions,[1,1.5],direction,
                                               initial_reference='local_z_launch')
    assert launch_paths==pytest.approx([1/.8+3,3])
    assert wave_paths[0]-launch_paths[0]==pytest.approx(2*.6+1*.8-1/.8)


@pytest.mark.parametrize('direction,mode', [((0,1,0),'local_z_launch'),((0,0,1),'unknown')])
def test_initial_reference_rejects_undefined_planes(direction,mode):
    with pytest.raises(ValueError):
        probe.propagation_differences([[[0,0,0]]],[1],direction,initial_reference=mode)


@pytest.mark.parametrize('direction', [(0,0,2), (0,0), (0,0,float('nan'))])
def test_incident_direction_requires_finite_unit_cosines(direction):
    with pytest.raises(ValueError):
        probe.propagation_differences([[[0,0,0]]],[1],direction)
