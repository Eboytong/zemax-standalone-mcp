import pytest
from pydantic import ValidationError

from zemax_mcp.grin import grin_definition, validate_grin_patch
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import SurfacePatch


@pytest.mark.parametrize("kind,quantity,last,unit", [
    ("Gradient2", "index_squared", "nr12", "lens_unit^-12"),
    ("Gradient3", "index", "nz3", "lens_unit^-3"),
])
def test_grin_definition_preserves_native_coefficient_identity(kind, quantity, last, unit):
    definition = grin_definition(kind)
    assert definition["polynomial_quantity"] == quantity
    assert definition["parameters"][-1] == dict(parameter=8, cell="parameter_8", name=last, unit=unit)
    patch = SurfacePatch(surface=1, parameters={3: -.02})
    assert patch.model_dump(exclude_unset=True) == {"surface": 1, "parameters": {3: -.02}}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_grin_coefficients_must_be_finite(value):
    with pytest.raises(ValidationError):
        SurfacePatch(surface=1, surface_type="Gradient2", parameters={3: value})


@pytest.mark.parametrize("patch", [{"parameters": {1: 0}}, {"parameters": {2: -1}},
                                   {"parameters": {9: .1}}, {"solves": {"parameter_9": {"mode": "variable"}}}])
def test_grin_invalid_step_index_or_other_type_parameters_rejected(patch):
    for kind in ("Gradient2", "Gradient3"):
        with pytest.raises(ZemaxError) as error:
            validate_grin_patch(kind, SurfacePatch(surface=1, **patch))
        assert error.value.code == "INVALID_ARGUMENT"
