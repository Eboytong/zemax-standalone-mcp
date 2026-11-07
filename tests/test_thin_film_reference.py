import math
import pytest
from support.thin_film import single_layer,bk7_index


@pytest.mark.parametrize('angle',[0,30,60,70])
def test_zero_thickness_film_matches_bare_fresnel(angle):
    a=math.radians(angle);c=math.cos(a);n=1.5;ct=math.sqrt(1-(math.sin(a)/n)**2)
    rs=((c-n*ct)/(c+n*ct))**2;rp=((n*c-ct)/(n*c+ct))**2
    result=single_layer(angle,.55,n,thickness_um=0)
    assert result['reflection']==pytest.approx([rs,rp,(rs+rp)/2],abs=1e-14)
    assert result['transmission']==pytest.approx([1-rs,1-rp,1-(rs+rp)/2],abs=1e-14)
    assert result['phase']==pytest.approx([0,0],abs=1e-14)


def test_quarter_wave_normal_incidence_admittance():
    n=1.38;substrate=1.52
    expected=((1-n*n/substrate)/(1+n*n/substrate))**2
    result=single_layer(0,.55,substrate,thickness_um=.55/(4*n),index=n)
    assert result['reflection']==pytest.approx([expected]*3,abs=1e-14)
    assert result['phase']==pytest.approx([-90,-90],abs=1e-12)


def test_bk7_d_line_index():
    assert bk7_index(.5875618)==pytest.approx(1.5168,abs=1e-6)
