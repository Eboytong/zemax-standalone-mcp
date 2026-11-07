import numpy as np
import pytest

from support.foucault_reference import pupil, returned_amplitude, shadowgram


@pytest.mark.parametrize("pair", [("Horiz_Above", "Horiz_Below"), ("Vert_Right", "Vert_Left")])
def test_complementary_complex_fields_reconstruct_pupil(pair):
    np.testing.assert_allclose(returned_amplitude(pair[0])+returned_amplitude(pair[1]),
                               pupil(), atol=1e-14, rtol=0)


def test_orthogonal_shadowgrams_transpose():
    np.testing.assert_allclose(shadowgram("Horiz_Above").T, shadowgram("Vert_Right"),
                               atol=1e-14, rtol=0)
    assert pupil().sum() == 3001
    assert shadowgram("Horiz_Above").max() == 1
