import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_fft_surface_mtf_settings_results_and_close():
    async def work(e):
        sample = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        await e.call("open_lens", {"path": str(sample)})
        task = await e.call("run_analysis", {"request": {
            "kind": "fft_surface_mtf", "field": 1, "wavelength": 1,
            "mtf_type": "MTF_Incoherent", "rotation": "Rotate_90",
            "sampling": "S_128x128", "show_as": "Contour",
            "use_polarization": False, "scale_factor": 1
        }})
        result = await e.finish(task)
        assert result.get("series") or result.get("grids") or result.get("artifacts"), result
        assert result["computation_method"] == "native_analysis"
    asyncio.run(execute("fft_surface_mtf", work))