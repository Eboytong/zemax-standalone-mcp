from types import SimpleNamespace as N
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.models import SystemPatch
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize("returned,count",[(None,1),(N(Wavelength=.65,Weight=1.),1)])
def test_wavelength_native_add_must_create_a_row(returned,count):
    waves=N(NumberOfWavelengths=1,GetWavelength=lambda _:N(Wavelength=.55,Weight=1.),AddWavelength=lambda *args:returned)
    b=N(system=N(Mode="Sequential",SystemData=N(Wavelengths=waves,Units=N(),Aperture=N())),
        _validate_settings_extension=lambda _:None,_mutate=lambda _:None,_apply_settings_extension=lambda _:None)
    with pytest.raises(ZemaxError)as caught:
        Backend.update_system_settings(b,SystemPatch(wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)]))
    assert caught.value.code=="SETTING_REJECTED"
    assert caught.value.details["wavelength_number"]==2
    assert caught.value.details["actual_count"]==count


def test_wavelength_silent_rejection_is_reported():
    class Ignored:
        Wavelength=property(lambda _: .55,lambda *_:None)
        Weight=property(lambda _: 1.,lambda *_:None)
    b=N(system=N(Mode="Sequential",SystemData=N(Wavelengths=N(NumberOfWavelengths=1,GetWavelength=lambda _:Ignored()),Units=N(),Aperture=N())),
        _validate_settings_extension=lambda _:None,_mutate=lambda _:None,_apply_settings_extension=lambda _:None)
    with pytest.raises(ZemaxError)as caught:Backend.update_system_settings(b,SystemPatch(wavelengths=[dict(wavelength_um=.65)]))
    assert caught.value.code=="SETTING_REJECTED"
