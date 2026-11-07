import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_foucault_native_settings_result_and_close():
    async def work(e):
        sample = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        await e.call("open_lens", {"path": str(sample)})
        task = await e.call("run_analysis", {"request": {
            "kind": "foucault", "field": 1, "wavelength": 1,
            "sampling": "S_128x128", "intensity_scale": "Linear",
            "show_as": "GreyScale", "knife": "Horiz_Above",
            "data": "Computed", "row_column": 64
        }})
        result = await e.finish(task)
        assert result.get("series") or result.get("grids") or result.get("artifacts"), result
        assert result["computation_method"] == "native_analysis"
    asyncio.run(execute("foucault", work))