import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES



def test_matrix_spot_uses_native_analysis_id():
    request = RunAnalysis(request={"kind": "matrix_spot"}).request
    assert request.kind == "matrix_spot"
    assert ANALYSES[request.kind] == "MatrixSpot"
def test_configuration_matrix_spot_typed_defaults():
    request = RunAnalysis(request={"kind": "configuration_matrix_spot"}).request
    assert request.pattern == "Hexapolar"
    assert request.reference == "Centroid"
    assert request.color_rays_by == "Config"
    assert request.ray_density == 6
    assert ANALYSES[request.kind] == "ConfigurationMatrixSpot"


@pytest.mark.parametrize("patch", [
    {"pattern": "Random"},
    {"reference": "Chief"},
    {"show_scale": "None"},
    {"color_rays_by": "Material"},
    {"ray_density": 0},
    {"ray_density": 101},
])
def test_configuration_matrix_spot_rejects_invalid_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "configuration_matrix_spot", **patch})