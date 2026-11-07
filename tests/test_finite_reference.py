import math
import pytest
from support.finite_reference import snell, sphere_intersection, singlet_ray, normalized_otf, polychromatic_otf, radial_grin_ray


def test_independent_snell_reference():
    direction = snell((.5, 0, math.sqrt(.75)), (0, 0, -1), 1, 1.5)
    assert direction[0] == pytest.approx(1/3)
    assert sum(v*v for v in direction) == pytest.approx(1)
    assert snell(direction, (0, 0, -1), 1.5, 1)[0] == pytest.approx(.5)
    with pytest.raises(ValueError, match="reflection"):
        snell((.9, 0, math.sqrt(.19)), (0, 0, -1), 1.5, 1)


def test_independent_sphere_reference():
    point, normal = sphere_intersection((0, 0, -1), (0, 0, 1), 0, 50)
    assert point == pytest.approx((0, 0, 0))
    assert normal == pytest.approx((0, 0, -1))
    row = singlet_ray(1, 0, 0, 1.5)
    assert row['front'][2] == pytest.approx(1+50-math.sqrt(2499))
    assert row['back'][2] == pytest.approx(6)
    assert row['outside'][0] < 0


def test_complex_otf_combination_retains_phase():
    import numpy as np
    image = np.zeros((32, 32)); image[16, 16] = 1
    _, _, a = normalized_otf(image, .001, .001)
    shifted = np.roll(image, 1, axis=1)
    _, _, b = normalized_otf(shifted, .001, .001)
    combined = polychromatic_otf([a, b], [.5, .5])
    assert abs(combined[16, 0]) < 1e-12
    assert (abs(a[16, 0])+abs(b[16, 0]))/2 == pytest.approx(1)


@pytest.mark.parametrize('values', [[[0, 0]], [[float('nan'), 1]]])
def test_invalid_psf_reference_rejected(values):
    with pytest.raises(ValueError):
        normalized_otf(values, .1, .1)


def test_grin_constant_index_limit_and_refinement():
    position,direction=radial_grin_ray(.1,-.2,4,1.5,0)
    assert position==pytest.approx((.1,-.2,0))
    assert direction==pytest.approx((0,0,1))
    a=radial_grin_ray(.1,.05,4,1.5,-.083,512)
    b=radial_grin_ray(.1,.05,4,1.5,-.083,1024)
    for v,w in zip(a,b):assert v==pytest.approx(w,abs=1e-10)
    assert b[1][0]<0


@pytest.mark.parametrize('odd',[False,True])
def test_ince_fourier_solution_matches_closed_order_two(odd):
    import numpy as np
    from support.ince_reference import field
    x=np.array([.05,-.05,.1,.05]);y=np.array([.05,.05,.05,-.05]);f0=.05;w=.1
    epsilon=2*(f0/w)**2;a=2+2*math.sqrt(1+epsilon*epsilon);c=2*epsilon/a
    reference=(x*y if odd else(c*c-1)+2*(c+1)*x*x/f0**2+2*(c-1)*y*y/f0**2)*np.exp(-(x*x+y*y)/w**2)
    actual=field(x,y,2,2,odd,w,f0)
    anchor=int(np.argmax(abs(reference)))
    assert actual/actual[anchor]==pytest.approx(reference/reference[anchor],abs=1e-10)


def test_independent_scatter_forward_poisson_limit():
    import numpy as np
    from support.scatter_reference import sphere_transport
    events,length=sphere_transport(0,rays=20000,seed=42)
    assert length==pytest.approx(np.full(20000,3.),abs=1e-12)
    assert events.mean()==pytest.approx(1.5,abs=6*math.sqrt(1.5/20000))


def test_thermal_reference_equal_temperature_and_cap_branches():
    from support.finite_reference import thermal_edge_gap
    length,state=thermal_edge_gap(10,50,-70,3,50,7.1,0)
    assert length==pytest.approx(10)
    assert state['branch']=='equal'
    assert thermal_edge_gap(10,50,-70,3,50,7.1,40)[1]['branch']=='lens'
    assert thermal_edge_gap(10,50,-70,3,50,7.1,-40)[1]['branch']=='mount'


@pytest.mark.parametrize('index',[14,18,20])
def test_chebyshev_even_terms_keep_local_vertex(index):
    from support.surface_reference import sag
    p={1:2,2:2,3:5,4:4,index:.001}
    assert sag('ChebyShv',0,0,parameters=p)==pytest.approx(0,abs=1e-15)
    # c20, c02 and c22 have known values at half-normalization coordinates.
    expected={14:.01,18:.01,20:-.015}[index]
    assert sag('ChebyShv',2.5,2,radius=None,parameters=p)==pytest.approx(expected)
