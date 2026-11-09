import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_athermal_glass_map_native_report_page_plot_and_lifecycle():
    async def work(e):
        await e.model()
        baseline=await e.call("get_system_settings")
        result=await e.finish(await e.call("run_analysis",dict(request={"kind":"athermal_glass_map"})))
        assert result["analysis_kind"]=="athermal_glass_map"
        assert result["task"]["state"]=="succeeded"
        assert result["task"]["settings"]["native"]["IsValid"] is True
        assert result["task"]["settings"]["native"]["IsActiveWindow"] is True
        assert result["sample_count"]==len(result["rows"])==len(result["scatter"][0]["points"])
        assert result["sample_count"]>0
        assert result["native_display_scales"]==dict(chromatic_power="1e-3",thermal_power="1e-6")
        assert result["coordinate_units"]==dict(chromatic_power="dimensionless",thermal_power="1/°C")
        assert result["wavelength_conditions"]==dict(minimum=.55,center=.55,maximum=.55)
        assert "BK7G18" in {row["material"] for row in result["rows"]}
        page=await e.call("get_task_result",dict(task_id=result["task"]["task_id"],start=0,count=3))
        assert page["total"]==result["sample_count"] and len(page["rows"])==min(3,page["total"])
        image=await e.call("export_analysis_image",dict(request=dict(task_id=result["task"]["task_id"],path=str(e.folder/"athermal-glass-map.png"))))
        assert Path(image["artifacts"][0]["path"]).is_file()
        assert await e.call("get_system_settings")==baseline
    asyncio.run(execute("athermal_glass_map_native",work))
