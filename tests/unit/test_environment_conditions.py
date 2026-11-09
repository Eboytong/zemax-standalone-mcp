from types import SimpleNamespace

import pytest

from zemax_mcp.errors import ZemaxError
from zemax_mcp.modeling import validate_environment_patch
from zemax_mcp.models import SystemPatch


@pytest.mark.parametrize('current,patch', [
    (False, dict(temperature_c=10)), (False, dict(pressure_atm=0)),
    (True, dict(adjust_index_to_environment=False, temperature_c=10)),
    (True, dict(adjust_index_to_environment=False, pressure_atm=0)),
])
def test_environment_rejects_nonreference_values_when_final_adjustment_is_off(current, patch):
    environment = SimpleNamespace(AdjustIndexToEnvironment=current)
    with pytest.raises(ZemaxError) as error:
        validate_environment_patch(environment, SystemPatch(**patch))
    assert error.value.code == 'SETTING_INACTIVE'
    assert error.value.details['required_setting'] == 'adjust_index_to_environment=true'


@pytest.mark.parametrize('current,patch', [
    (False, dict(temperature_c=20, pressure_atm=1)),
    (False, dict(adjust_index_to_environment=True, temperature_c=10, pressure_atm=0)),
    (True, dict(temperature_c=10, pressure_atm=0)),
    (True, dict(adjust_index_to_environment=False)),
    (False, dict(title='No environment changes')),
])
def test_environment_validates_final_condition_without_changing_omitted_fields(current, patch):
    environment = SimpleNamespace(AdjustIndexToEnvironment=current)
    validate_environment_patch(environment, SystemPatch(**patch))
    assert environment.AdjustIndexToEnvironment is current
