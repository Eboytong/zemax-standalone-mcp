import numpy as np
import pytest
from tests.support.diffraction_reference import pupil_autocorrelation


def test_pupil_autocorrelation_matches_direct_complex_pair_sum():
    pupil = np.array([[1+2j, 0, 3-1j], [0, 2j, -1]], dtype=complex)
    actual = pupil_autocorrelation(pupil)
    ny, nx = pupil.shape
    power = np.sum(abs(pupil)**2)
    for dy in range(-ny, ny):
        for dx in range(-nx, nx):
            pair_sum = sum(pupil[y,x]*pupil[y+dy,x+dx].conjugate()
                for y in range(ny) for x in range(nx)
                if 0 <= y+dy < ny and 0 <= x+dx < nx)
            assert actual[dy+ny,dx+nx] == pytest.approx(abs(pair_sum)/power, abs=1e-14)


@pytest.mark.parametrize('pupil', [np.zeros((2,3)), [[float('nan')]], [1,2]])
def test_pupil_autocorrelation_rejects_unusable_reference(pupil):
    with pytest.raises(ValueError):
        pupil_autocorrelation(pupil)
