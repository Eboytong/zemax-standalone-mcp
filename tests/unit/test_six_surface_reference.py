"""Independent-reference checks used before optical comparisons."""
import math
import pytest
from tests.support.six_surface_reference import sag,normal,conjugate_value,extended_sag,reflected
from tests.support.surface_reference import conic_sag


@pytest.mark.parametrize('radius',[30.,50.])
def test_biconic_equal_axes_matches_conic(radius):
    for x,y in [(0,0),(.5,-.7),(-1,.2)]:
        assert sag('Biconic',x,y,radius,-.3,{1:radius,2:-.3})==pytest.approx(conic_sag(x,y,radius,-.3),abs=1e-12)


@pytest.mark.parametrize('z1,z2',[(-30,-50),(-30,50),(30,50)])
def test_conjugate_vertex_and_equation(z1,z2):
    p={1:1,2:-2,3:z1,4:-2,5:1,6:z2}
    assert sag('Conjugate',0,0,0,0,p)==0
    for x,y in [(.6,.3),(-.4,.2)]:
        z=sag('Conjugate',x,y,0,0,p)
        assert abs(conjugate_value(x,y,z,p)[0])<1e-11


@pytest.mark.parametrize('kind',['ExtendedAsphere','ExtendedOddAsphere','ExtendedPolynomial'])
def test_extended_maximum_term_is_not_cell_count(kind):
    p={13:3,14:2,15:.01,21:-.02}
    x,y=(1.6,1.2) if kind=='ExtendedPolynomial' else (2,0)
    contribution=-.02*.8**2*.6 if kind=='ExtendedPolynomial' else -.02
    at=extended_sag(kind,x,y,p)
    p[13]=30
    assert extended_sag(kind,x,y,p)==pytest.approx(at+contribution,abs=1e-12)


def test_odd_cusp_and_normal_convergence():
    p={1:.001,2:-.0005,3:.0002}
    assert sag('OddAsphere',0,0,50,-.3,p)==0
    a=normal('OddAsphere',.6,-.3,50,-.3,p)
    b=normal('OddAsphere',.6,-.3,50,-.3,p,step=5e-6)
    assert max(abs(x-y) for x,y in zip(a,b))<1e-8


def test_reflection_direction_and_power_geometry():
    d=(.6,0,.8)
    assert reflected(d,(0,0,1))==pytest.approx((.6,0,-.8))
    assert sum(x*x for x in reflected(d,(0,0,1)))==pytest.approx(1)
