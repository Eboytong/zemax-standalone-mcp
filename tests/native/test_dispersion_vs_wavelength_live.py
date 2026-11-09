"""Native dispersion curve checked against a finite difference of n(lambda)."""
import asyncio
import json
import pytest
from tests.support.native import execute
from tests.support.finite_reference import glass_coefficients, sellmeier


@pytest.mark.zemax
def test_dispersion_vs_wavelength_native_curve_and_reference():
    async def work(e):
        await e.model()
        baseline=await e.call("get_system_settings")
        index_result=await e.finish(await e.call("run_analysis",dict(request={"kind":"dispersion_diagram"})))
        dispersion_result=await e.finish(await e.call("run_analysis",dict(request={"kind":"dispersion_vs_wavelength"})))
        index_curve=index_result["series"][0]
        curve=dispersion_result["series"][0]
        assert curve["x"]==index_curve["x"]
        assert curve["labels"]==index_curve["labels"]
        assert curve["value_units"]==["1/micrometer"]*len(curve["labels"])
        assert dispersion_result["environment"]==index_result["environment"]
        assert dispersion_result["task"]["state"]=="succeeded"
        assert dispersion_result["task"]["settings"]["native"]["IsValid"] is True
        assert any(item["kind"]=="native_text" for item in dispersion_result["artifacts"])
        assert "SCHOTT" in index_result["system_settings"]["material_catalogs"]
        # Installed SCHOTT.AGF formula 2; differentiate n^2 analytically.
        # Seven-decimal native text contributes at most 5e-8 rounding error.
        coefficients = glass_coefficients("BK7G18")
        column = curve["labels"].index("BK7G18")
        derivative_diagnostics = []
        for index, wavelength in enumerate(curve["x"]):
            expected_index = sellmeier(wavelength, coefficients)
            expected_derivative = -wavelength / expected_index * sum(
                coefficients[i] * coefficients[i+1] /
                (wavelength*wavelength-coefficients[i+1])**2 for i in (0, 2, 4))
            e.check(f"SCHOTT BK7G18 Sellmeier index at {wavelength} um",
                    index_curve["y"][index][column], expected_index, atol=5.1e-8, rtol=0)
            actual = curve["y"][index][column]
            finite_step = (sellmeier(wavelength+.0001, coefficients) -
                           sellmeier(wavelength-.0001, coefficients)) / .0002
            derivative_diagnostics.append(dict(wavelength_um=wavelength, actual=actual,
                analytic=expected_derivative, analytic_error=abs(actual-expected_derivative),
                analytic_gate_passed=abs(actual-expected_derivative)<=5.1e-8,
                finite_step_1e_4=finite_step, finite_step_error=abs(actual-finite_step)))
        # Diagnostic gate remains open: native differentiation step is undocumented.
        # Persist every point; existing finite-difference acceptance below is separate.
        (e.folder / "independent-derivative-diagnostics.json").write_text(json.dumps(dict(
            catalog="SCHOTT.AGF", material="BK7G18", coefficients=coefficients,
            tolerance=5.1e-8, conclusion="Analytic derivative gate remains unresolved",
            points=derivative_diagnostics), indent=2), encoding="utf-8")
        for column,label in enumerate(curve["labels"]):
            for index in range(1,len(curve["x"])-1):
                dx=curve["x"][index+1]-curve["x"][index-1]
                finite_difference=(index_curve["y"][index+1][column]-index_curve["y"][index-1][column])/dx
                e.check(f"{label} dn/dlambda at {curve['x'][index]} um",curve["y"][index][column],finite_difference,atol=5e-5,rtol=0)
        page=await e.call("get_task_result",dict(task_id=dispersion_result["task"]["task_id"],series=0,start=0,count=3))
        assert page
        assert await e.call("get_system_settings")==baseline
    asyncio.run(execute("dispersion_vs_wavelength_native",work))
