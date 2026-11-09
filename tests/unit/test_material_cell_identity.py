"""Native material names may be returned in upper case."""
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError

class UppercaseCell:
    DataType='String'
    Header='Material'
    IsReadOnly=False
    IsActive=True
    def __init__(self, substitute=None):
        self.substitute=substitute
        self._value=''
    @property
    def Value(self): return self._value
    @Value.setter
    def Value(self,value): self._value=self.substitute or value.upper()


def test_material_readback_accepts_native_uppercase():
    cell=UppercaseCell()
    Backend._write_cell(cell,'F2HTi',material_name=True)
    assert cell.Value=='F2HTI'


def test_material_readback_rejects_different_material():
    with pytest.raises(ZemaxError) as error:
        Backend._write_cell(UppercaseCell('N-BK7'),'F2HTi',material_name=True)
    assert error.value.code=='SETTING_REJECTED'


def test_other_string_cells_keep_exact_readback():
    with pytest.raises(ZemaxError):
        Backend._write_cell(UppercaseCell(),'Mixed Case')
