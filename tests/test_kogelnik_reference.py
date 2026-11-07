import math
import pytest
from support.kogelnik import unslanted_transmission


@pytest.mark.parametrize('polarization',['S','P'])
def test_bragg_efficiency_matches_closed_form(polarization):
    angle=math.degrees(math.atan(.5));theta=math.asin(math.sin(math.radians(angle))/1.5)
    nu=math.pi*.02*10/(.55*math.cos(theta))
    if polarization=='P':nu*=math.cos(2*theta)
    assert unslanted_transmission(angle,.55,polarization)==pytest.approx(math.sin(nu)**2,abs=1e-14)


@pytest.mark.parametrize('angle',[0,10,26,35])
def test_zero_modulation_has_zero_diffraction(angle):
    assert unslanted_transmission(angle,.55,modulation=0)==0


def test_normal_degenerate_case_matches_normal_incidence_formula():
    assert unslanted_transmission(0,.55,construction_angle_degrees=0)==pytest.approx(math.sin(math.pi*.02*10/.55)**2,abs=1e-14)
