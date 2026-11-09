"""Native DispersionDiagram text result adaptation and lifecycle."""
import asyncio
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_dispersion_diagram_native_curve_and_lifecycle():
    async def work(e):
        await e.model()
        baseline=await e.call("get_system_settings")
        result=await e.finish(await e.call("run_analysis",dict(request={"kind":"dispersion_diagram"})))
        assert result["analysis_kind"]=="dispersion_diagram",result
        assert result["series"],result
        curve=result["series"][0]
        assert len(curve["x"])>=2 and curve["labels"]
        assert len(curve["x"])==len(curve["y"])
        assert curve["x_unit"]=="micrometers"
        assert all(unit=="dimensionless" for unit in curve["value_units"])
        assert "BK7G18" in curve["labels"]
        assert result["sample_count"]==len(curve["x"])
        assert result["environment"]["temperature_c"]==20
        assert result["environment"]["pressure_atm"]==1
        assert any(item["kind"]=="native_text" for item in result["artifacts"])
        page=await e.call("get_task_result",dict(task_id=result["task"]["task_id"],series=0,start=0,count=3))
        assert page
        assert await e.call("get_system_settings")==baseline
    asyncio.run(execute("dispersion_diagram_native",work))
