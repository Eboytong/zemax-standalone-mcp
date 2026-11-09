import math

import pytest

from tests.support.fiber_reference import circular_pupil_coupling


def test_uniform_disk_against_independent_radial_quadrature():
    # Midpoint quadrature of the normalized 2D overlap, independent of the
    # closed-form antiderivative in the reference function.
    radius, distance, na = .5, 100., .005
    count = 20000
    dr = radius / count
    overlap = math.fsum(2 * math.pi * (i + .5) * dr * math.exp(-((i + .5) * dr / (distance * na)) ** 2) * dr for i in range(count))
    expected = overlap ** 2 / (math.pi * radius ** 2 * math.pi * (distance * na) ** 2 / 2)
    assert circular_pupil_coupling(radius, distance, na) == pytest.approx(expected, abs=2e-9)


def test_matched_source_receiver_and_aperture_loss():
    actual = circular_pupil_coupling(.5, 200., .0025, object_distance=200., source_na=.0025)
    assert actual == pytest.approx((1 - math.exp(-2)) ** 2)


@pytest.mark.parametrize('kwargs', [dict(source_na=.1), dict(object_distance=2), dict(source_na=0, object_distance=2)])
def test_incomplete_or_invalid_source(kwargs):
    with pytest.raises(ValueError):
        circular_pupil_coupling(.5, 100, .005, **kwargs)
