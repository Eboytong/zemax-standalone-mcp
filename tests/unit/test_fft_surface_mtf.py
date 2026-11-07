import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES


def test_fft_surface_mtf_typed_defaults():
    request = RunAnalysis(request={"kind": "fft_surface_mtf"}).request
    assert request.field == 1
    assert request.wavelength == 1
    assert request.mtf_type == "MTF_Incoherent"
    assert request.sampling == "S_64x64"
    assert request.scale_factor == 1
    assert ANALYSES[request.kind] == "FftSurfaceMtf"


@pytest.mark.parametrize("patch", [
    {"mtf_type": "bad"},
    {"rotation": "Rotate_45"},
    {"sampling": "S_4096x4096"},
    {"show_as": "Image"},
    {"scale_factor": 0},
    {"scale_factor": float("inf")},
])
def test_fft_surface_mtf_rejects_invalid_typed_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "fft_surface_mtf", **patch})