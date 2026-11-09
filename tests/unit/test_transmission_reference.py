import math
import pytest
from tests.support.transmission_reference import interface_power, spherical_plano_power


def test_normal_interface_and_two_surface_limit():
    assert interface_power(1, 1.5, 0) == pytest.approx((.96, .96))
    assert spherical_plano_power(0, 0) == pytest.approx(.9216)


def test_brewster_p_has_no_reflection():
    assert interface_power(1, 1.5, math.atan(1.5))[1] == pytest.approx(1)


def test_rotated_position_and_jones_preserve_throughput():
    assert spherical_plano_power(4, 0, jx=1, jy=0) == pytest.approx(
        spherical_plano_power(0, 4, jx=0, jy=1))
    assert spherical_plano_power(4, 0, jx=1, jy=0) != pytest.approx(
        spherical_plano_power(4, 0, jx=0, jy=1), abs=1e-4)
