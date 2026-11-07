"""MCE numeric getter rounding must not hide a different adopted value."""
from types import SimpleNamespace

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.configurations import write_configuration_cell
from zemax_mcp.errors import ZemaxError


class RoundedCell:
    IsReadOnly=False
    IsActive=True
    DataType='Double'
    Header='Configuration 2'
    def __init__(self,ignored=None):self.stored=0.;self.ignored=ignored
    @property
    def DoubleValue(self):return float(format(self.stored,'.9g'))
    @DoubleValue.setter
    def DoubleValue(self,value):self.stored=value if self.ignored is None else self.ignored


@pytest.mark.parametrize('value',[1/60,-1/60,1/3,1.234567891234e-9,12345678912.34,0.])
def test_mce_write_checks_confirmed_numeric_getter_precision(value):
    cell=RoundedCell()
    write_configuration_cell(SimpleNamespace(_write_cell=Backend._write_cell),cell,value)
    assert cell.stored==value


def test_mce_rejected_value_retains_original_request_and_actual():
    cell=RoundedCell(ignored=.016666668)
    with pytest.raises(ZemaxError)as error:
        write_configuration_cell(SimpleNamespace(_write_cell=Backend._write_cell),cell,1/60)
    assert error.value.code=='SETTING_REJECTED'
    assert error.value.details['requested']==1/60
    assert error.value.details['actual']==str(.016666668)


@pytest.mark.parametrize('code',['CELL_NOT_WRITABLE','NATIVE_ERROR'])
def test_mce_other_write_failure_is_not_reinterpreted(code):
    original=ZemaxError(code,'original native failure')
    def fail(*args):raise original
    with pytest.raises(ZemaxError)as error:
        write_configuration_cell(SimpleNamespace(_write_cell=fail),RoundedCell(),1/60)
    assert error.value is original


def test_mce_secondary_getter_failure_retains_original_rejection():
    original=ZemaxError('SETTING_REJECTED','original write mismatch',requested=1/60)
    def fail(*args):raise original
    class Unreadable(RoundedCell):
        @property
        def DoubleValue(self):raise RuntimeError('secondary getter failure')
    with pytest.raises(ZemaxError)as error:
        write_configuration_cell(SimpleNamespace(_write_cell=fail),Unreadable(),1/60)
    assert error.value is original
