import numpy as np
from support.zernike_reference import standard15,pupil_points,fit_standard15


def test_standard15_reference_recovers_all_coefficients():
    x,y=pupil_points(96)
    coefficients=np.arange(15)*.013-.08
    fitted=fit_standard15(x,y,standard15(x,y)@coefficients)
    np.testing.assert_allclose(fitted,coefficients,atol=1e-12,rtol=0)


def test_standard15_unit_disk_orthonormality():
    x,y=pupil_points(512)
    basis=standard15(x,y)
    np.testing.assert_allclose(basis.T@basis/len(x),np.eye(15),atol=.001,rtol=0)
