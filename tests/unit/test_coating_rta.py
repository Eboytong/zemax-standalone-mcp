from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.coating_models import CoatingRta
from zemax_mcp.coatings import CoatingsMixin
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize("patch", [dict(surface=0), dict(surface=1, conditions=[]),
    dict(surface=1, conditions=[{}]*121), dict(surface=1, conditions=[dict(wavelength=1, wavelength_um=.55)]),
    dict(surface=1, conditions=[dict(angle_deg=90)]), dict(surface=1, conditions=[dict(wavelength_um=0)]),
    dict(surface=1, conditions=[dict(angle_deg=float('nan'))]),
    dict(surface=1, conditions=[dict(wavelength=None)])])
def test_request_rejects_invalid_conditions(patch):
    with pytest.raises(ValidationError):
        CoatingRta(**patch)


def adapter():
    called = []
    data = NS(SurfaceNumber=1, Reflection=NS(S=.2, P=.1), Transmission=NS(S=.7, P=.8),
              Absorption=NS(S=.1, P=.1), GetCoatingPerformance=lambda *args: called.append(args))
    row = NS(Material='N-BK7', Coating='FILM', GetCoatingPerformanceData=lambda: data)
    b = NS(_require_sequential=lambda: None, _row=lambda i: row if i else NS(Material=''),
           system=NS(SystemData=NS(Wavelengths=NS(NumberOfWavelengths=2,
                     GetWavelength=lambda i: NS(Wavelength=.5+.05*i, IsPrimary=i==2))),
                     MCE=NS(CurrentConfiguration=1)),
           native=NS(api=NS(Editors=NS(DirectionOfRayTravel='enum')), enum=lambda _, value: value), version='24.2')
    return b, data, called


def test_primary_explicit_wavelength_direction_and_energy():
    b, _, called = adapter()
    result = CoatingsMixin.get_coating_rta(b, CoatingRta(surface=1, conditions=[{},
        dict(wavelength=1, angle_deg=30, direction='outward'), dict(wavelength_um=.65)]))
    assert called == [(0, .6, 'inward'), (30, .55, 'outward'), (0, .65, 'inward')]
    assert result['samples'][2]['wavelength'] is None
    assert result['samples'][0]['reflection']['unpolarized'] == pytest.approx(.15)
    assert result['samples'][0]['energy_residual']['s'] == pytest.approx(0)


def test_bad_wavelength_rejected_before_native_execution():
    b, _, called = adapter()
    with pytest.raises(ZemaxError) as error:
        CoatingsMixin.get_coating_rta(b, CoatingRta(surface=1, conditions=[dict(wavelength=3)]))
    assert error.value.code == 'INDEX_OUT_OF_RANGE'
    assert called == []


def test_native_failure_preserves_completed_samples_and_exception():
    b, data, called = adapter()
    def calculate(*args):
        called.append(args)
        if len(called) == 2:
            raise RuntimeError('native calculation detail')
    data.GetCoatingPerformance = calculate
    with pytest.raises(ZemaxError) as error:
        CoatingsMixin.get_coating_rta(b, CoatingRta(surface=1, conditions=[{}, {}]))
    assert str(error.value) == 'native calculation detail'
    assert len(error.value.details['completed_samples']) == 1


def test_missing_api_and_wrong_identity():
    b, data, _ = adapter()
    data.SurfaceNumber = 2
    with pytest.raises(ZemaxError) as error:
        CoatingsMixin.get_coating_rta(b, CoatingRta(surface=1))
    assert error.value.code == 'RESULT_IDENTITY_MISMATCH'
    delattr(b._row(1), 'GetCoatingPerformanceData')
    with pytest.raises(ZemaxError) as error:
        CoatingsMixin.get_coating_rta(b, CoatingRta(surface=1))
    assert error.value.code == 'UNSUPPORTED_INTERFACE'
