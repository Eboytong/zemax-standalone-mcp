"""Regression: active configuration numbers are not IAS_Spot selector values."""
from types import SimpleNamespace as NS

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import Spot


def backend(configuration, rejected=False):
    class Selection:
        def SetFieldNumber(self,value):self.value=value
        def SetWavelengthNumber(self,value):self.value=value
        def GetFieldNumber(self):return self.value
        def GetWavelengthNumber(self):return self.value

    class Settings:
        Field=Selection()
        Wavelength=Selection()

        @property
        def Configuration(self):return 2 if rejected else self.selection

        @Configuration.setter
        def Configuration(self,value):self.selection=value

    settings=Settings();analysis=NS(GetSettings=lambda:settings)
    closes=[]
    return NS(
        _analysis_selection=lambda req:None,
        system=NS(MCE=NS(CurrentConfiguration=configuration),Analyses=NS(New_Analysis_SettingsFirst=lambda code:analysis,New_Analysis=lambda code:analysis)),
        native=NS(api=NS(Analysis=NS(AnalysisIDM=NS(StandardSpot='StandardSpot'))),set_enum=lambda obj,key,value:setattr(obj,key,value)),
        _start_task=lambda kind,native,actual,analysis:actual,
        _close_task_native=lambda owner:closes.append(owner) or True),closes


@pytest.mark.parametrize('configuration',[1,2,3])
def test_standard_spot_evaluates_active_configuration_without_reinterpreting_its_number(configuration):
    b,closes=backend(configuration)
    actual=Backend.run_spot_analysis(b,Spot(reference='Centroid',field=3,wavelength=1))
    assert actual['configuration']==configuration
    assert actual['native_configuration_selector']==1
    assert actual['field']==3 and actual['wavelength']==1
    assert not closes


def test_rejected_current_configuration_selector_closes_analysis():
    b,closes=backend(2,rejected=True)
    with pytest.raises(ZemaxError) as error:
        Backend.run_spot_analysis(b,Spot(reference='Centroid'))
    assert error.value.code=='SETTING_REJECTED'
    assert len(closes)==1
