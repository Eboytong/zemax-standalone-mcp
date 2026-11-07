import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES


def test_foucault_typed_defaults_and_analysis_id():
    request = RunAnalysis(request={"kind": "foucault"}).request
    assert request.field == 1
    assert request.wavelength == 1
    assert request.sampling == "S_64x64"
    assert request.intensity_scale == "Linear"
    assert ANALYSES[request.kind] == "Foucault"


@pytest.mark.parametrize("patch", [
    {"intensity_scale": "Log"},
    {"show_as": "Bitmap"},
    {"knife": "Diagonal"},
    {"data": "Measured"},
    {"row_column": -1},
    {"scale_x": 0},
])
def test_foucault_rejects_invalid_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "foucault", **patch})


@pytest.mark.parametrize('data', ['Reference', 'Difference'])
def test_foucault_requires_reference_source(data):
    with pytest.raises(ValidationError, match='source'):
        RunAnalysis(request=dict(kind='foucault',data=data))
    q=RunAnalysis(request=dict(kind='foucault',data=data,source='C:/test.bmp')).request
    assert q.source=='C:/test.bmp'


@pytest.mark.parametrize('filename,code',[('missing.bmp','FILE_NOT_FOUND'),('wrong.png','INVALID_ARGUMENT')])
def test_foucault_source_preflight_precedes_native_factory(tmp_path,filename,code):
    from types import SimpleNamespace as NS
    from zemax_mcp.analyses import AnalysesMixin
    from zemax_mcp.errors import ZemaxError
    backend=NS(_require_sequential=lambda **kw:None,
               system=NS(SystemData=NS(Fields=NS(NumberOfFields=1),Wavelengths=NS(NumberOfWavelengths=1))))
    q=RunAnalysis(request=dict(kind='foucault',source=str(tmp_path/filename))).request
    with pytest.raises(ZemaxError) as error:
        AnalysesMixin._run_general_analysis(backend,q)
    assert error.value.code==code
