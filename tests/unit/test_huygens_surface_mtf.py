import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES


def test_huygens_surface_mtf_typed_defaults():
    request = RunAnalysis(request={"kind": "huygens_surface_mtf"}).request
    assert request.field == 1
    assert request.wavelength == 1
    assert request.sampling == "S_64x64"
    assert request.image_sampling == "S_64x64"
    assert request.mtf_type == "MTF_Incoherent"
    assert ANALYSES[request.kind] == "HuygensSurfaceMtf"


@pytest.mark.parametrize("patch", [
    {"mtf_type": "MTF"},
    {"show_as": "Surface"},
    {"image_delta": -1},
    {"sampling": "S_16x16"},
    {"image_sampling": "S_16x16"},
    {"field": -1},
    {"wavelength": -1},
])
def test_huygens_surface_mtf_rejects_invalid_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "huygens_surface_mtf", **patch})
