"""Analytic checks of the independent coordinate-area transport reference."""
from pathlib import Path
import runpy

import numpy as np
import pytest


@pytest.fixture(scope='module')
def reference():
    root=Path(__file__).resolve().parents[2]
    return runpy.run_path(str(root/'scripts/probes/CV-01/fft_surface_direction_coordinates.py'))


def test_shear_and_anisotropic_scale_conserve_integrated_flux(reference):
    source=np.array([[0.,0.],[1.,0.],[0.,1.],[1.,1.]])
    triangles=np.array([[0,1,2],[1,3,2]])
    target=source@np.array([[2.,1.],[0.,3.]])+[4.,-2.]
    ratio=reference['triangle_area_ratio'](source,target,triangles)
    assert ratio==pytest.approx([6.,6.],abs=1e-12)
    source_flux=np.array([.5,1.5])
    target_area=np.array([3.,3.])
    source_area=np.array([.5,.5])
    intensity=source_flux/source_area
    assert target_area*(intensity/ratio)==pytest.approx(source_flux,abs=1e-12)


def test_coordinate_reflection_preserves_unsigned_area(reference):
    source=np.array([[0.,0.],[1.,0.],[0.,1.]])
    ratio=reference['triangle_area_ratio'](source,source*[-1.,1.],np.array([[0,1,2]]))
    assert ratio==pytest.approx([1.],abs=1e-12)


def test_singular_coordinate_mesh_has_no_flux_density(reference):
    source=np.array([[0.,0.],[1.,0.],[0.,1.]])
    with pytest.raises(ValueError,match='singular'):
        reference['triangle_area_ratio'](source,source*[1.,0.],np.array([[0,1,2]]))


def test_mixed_orientation_identifies_folded_mesh(reference):
    source=np.array([[0.,0.],[1.,0.],[0.,1.],[1.,1.]])
    target=source.copy();target[3]=[-1.,-1.]
    with pytest.raises(ValueError,match='orientation'):
        reference['triangle_area_ratio'](source,target,np.array([[0,1,2],[1,3,2]]))


def test_lattice_boundary_retains_three_corner_cells(reference):
    cells=np.array([[0,0],[0,1],[1,1]])
    triangles=reference['lattice_triangles'](cells)
    assert triangles.tolist()==[[0,1,2]]
    ratio=reference['triangle_area_ratio'](cells[:,::-1],cells[:,::-1]*[2.,3.],triangles)
    assert ratio==pytest.approx([6.])


def test_lattice_joins_square_without_bridging_missing_cells(reference):
    cells=np.array([[0,0],[0,1],[1,0],[1,1],[10,10]])
    triangles=reference['lattice_triangles'](cells)
    assert triangles.shape==(2,3)
    assert 4 not in triangles
