from types import SimpleNamespace as NS
import math
import pytest
from zemax_mcp.models import Capabilities
from zemax_mcp.errors import ZemaxError
from tests.unit.test_merit_edit_safety import setup, Row


def diagnostic_backend(tmp_path, merit=12.5, variables=True):
    backend, editor=setup(tmp_path,[Row("EFFL")])
    editor.CalculateMeritFunction=lambda: merit
    backend.get_variables=lambda _: {"variables":[{"surface":1}] if variables else []}
    return backend,editor


def test_targeted_contract_works_without_connection(tmp_path):
    backend,_=diagnostic_backend(tmp_path)
    result=backend.get_capabilities(Capabilities(topic="tool",tool_name="update_merit_function"))
    assert result["request_schema"]["properties"]["operands"]
    assert "implemented_tools" not in result


def test_merit_evaluation_keeps_native_single_condition_snapshot(tmp_path):
    backend, _ = diagnostic_backend(tmp_path, 0.000003)
    backend.get_system_settings = lambda _: {
        "configuration": 2, "temperature_c": 25, "field_type": "Angle",
        "fields": [{"x": 0, "y": -7}],
        "wavelengths": [{"wavelength_um": 0.63}],
    }
    result = backend.evaluate_merit_function(None)
    assert result["merit_function"] == 0.000003
    assert result["analysis_conditions"] == {
        "configuration": 2, "temperature_c": 25,
        "wavelength_um": 0.63, "field_deg": -7,
    }
    assert result["system_settings"]["fields"][0]["y"] == -7


def test_merit_snapshot_does_not_claim_multifield_or_multiwave_coverage(tmp_path):
    backend, _ = diagnostic_backend(tmp_path)
    backend.get_system_settings = lambda _: {
        "configuration": 1, "temperature_c": 20, "field_type": "Angle",
        "fields": [{"x": 0, "y": 0}, {"x": 0, "y": 12}],
        "wavelengths": [{"wavelength_um": 0.55}, {"wavelength_um": 0.65}],
    }
    result = backend.evaluate_merit_function(None)
    assert "field_deg" not in result["analysis_conditions"]
    assert "wavelength_um" not in result["analysis_conditions"]
    backend.get_system_settings = lambda _: {
        "field_type": "ObjectHeight", "fields": [{"x": 0, "y": 5}], "wavelengths": [],
    }
    assert "field_deg" not in backend.evaluate_merit_function(None)["analysis_conditions"]


def test_merit_value_survives_snapshot_read_failure(tmp_path):
    backend, _ = diagnostic_backend(tmp_path, 0.25)
    def failed(_):
        raise RuntimeError("snapshot unavailable")
    backend.get_system_settings = failed
    result = backend.evaluate_merit_function(None)
    assert result["merit_function"] == 0.25
    assert result["analysis_conditions"] == {}
    assert result["settings_error"] == "snapshot unavailable"


def test_configuration_switching_merit_keeps_context_without_claiming_one_condition(tmp_path):
    backend, editor = diagnostic_backend(tmp_path)
    editor.rows = [Row("CONF")]
    backend.get_system_settings = lambda _: {"configuration": 2, "temperature_c": 30,
        "field_type": "Angle", "fields": [{"x": 0, "y": 0}], "wavelengths": [{"wavelength_um": 0.55}]}
    result = backend.evaluate_merit_function(None)
    assert result["system_settings"]["configuration"] == 2
    assert result["analysis_conditions"] == {}


def test_merit_cells_expose_writable_native_columns(tmp_path):
    backend,editor=diagnostic_backend(tmp_path)
    result=backend.get_merit_function(None)
    assert result["operands"][0]["cells"]["2"]["active"] is False
    assert result["operands"][0]["cells"]["2"]["writable"] is False


@pytest.mark.parametrize("merit",[0,12.950418741254,9e9,1e30])
def test_large_finite_merit_is_retained_without_operand_blacklist(tmp_path,merit):
    backend,editor=diagnostic_backend(tmp_path,merit)
    result=backend.optimization_diagnostics()
    assert result["ready"] and result["merit_function"]==merit
    assert result["rows"][0]["type"]=="EFFL"


def test_diagnostic_rejects_nonfinite_and_no_variables_before_mutation(tmp_path):
    backend,editor=diagnostic_backend(tmp_path,math.inf)
    with pytest.raises(ZemaxError) as exc: backend._optimization_preflight()
    assert exc.value.code=="INVALID_MERIT_FUNCTION"
    assert backend.revision==0
    backend,editor=diagnostic_backend(tmp_path,variables=False)
    with pytest.raises(ZemaxError) as exc: backend._optimization_preflight()
    assert exc.value.code=="NO_VARIABLES"


def test_native_validity_and_read_failure_keep_optimizer_closed(tmp_path):
    backend,_=diagnostic_backend(tmp_path)
    backend.system.GetCurrentStatus=lambda: "Cannot trace reference ray"
    result=backend.optimization_diagnostics()
    assert result["ready"] is False
    assert result["issues"][0]["code"]=="INVALID_NATIVE_SYSTEM"
    assert result["merit_function"]==12.5


def test_native_inactive_merit_cells_keep_wizard_control_values_without_blocking(tmp_path):
    backend,editor=diagnostic_backend(tmp_path)
    control=Row("DMFS",target=math.inf,weight=math.inf)
    control.Value=control.Contribution=math.inf
    blank=Row("BLNK",target=math.nan,weight=math.nan)
    blank.Value=blank.Contribution=math.nan
    for row in (control,blank):
        row.IsActive=True
        row.WeightCell=NS(IsActive=False)
    editor.rows=[control,blank,*editor.rows]
    result=backend.optimization_diagnostics()
    assert result["ready"]
    assert math.isinf(result["rows"][0]["value"])
    assert math.isnan(result["rows"][1]["weight"])
    editor.rows.pop()
    assert backend.optimization_diagnostics()["issues"][0]["code"]=="NO_MERIT_FUNCTION"


def test_nonfinite_active_operand_still_blocks_even_when_total_merit_is_finite(tmp_path):
    backend,editor=diagnostic_backend(tmp_path)
    editor.rows[0].WeightCell=NS(IsActive=True)
    editor.rows[0].Value=math.inf
    result=backend.optimization_diagnostics()
    assert not result["ready"]
    assert any(issue.get("reason")=="nonfinite_operand" for issue in result["issues"])


def test_invalid_argument_paths_include_targeted_contract(tmp_path):
    backend,_=diagnostic_backend(tmp_path)
    from pydantic import ValidationError
    try:
        Capabilities(topic="wrong")
    except ValidationError as error:
        result=backend._argument_errors("get_capabilities",error)
    assert result["fields"][0]["field_path"]=="topic"
    assert "settings" in result["fields"][0]["allowed_values"]
    assert result["execution_stage"]=="parameter_validation"
