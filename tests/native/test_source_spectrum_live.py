import asyncio
import json
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_source_spectrum_viewer_stdio():
    async def work(e):
        await e.call("open_lens", dict(path=str(Path.home() / "Documents/Zemax/Samples/Non-sequential/Colorimetry/Example 1  Two-color mixing gives white.zos")))
        baseline=await e.call('get_system_settings')
        objects=await e.call('get_nsc_objects',dict(request={}))
        result = await e.finish(await e.call("run_analysis", dict(request=dict(kind="source_spectrum_viewer"))))
        assert result["computation_method"] == "native_SourceSpectrumViewer_text"
        assert result["spectral_unit"] == "micrometers"
        assert result["weight_unit"] == "dimensionless relative weight"
        assert len(result["rows"]) == 20
        assert result["rows"][0]["wavelength_um"] == pytest.approx(0.44)
        assert result["rows"][-1]["wavelength_um"] == pytest.approx(0.64)
        assert max(row["relative_weight"] for row in result["rows"]) == pytest.approx(1.0)
        assert result["input_xyz"] == [1.0, 1.0, 1.0]
        assert result["fitted_xyz"] == [1.0, 1.0, 1.0]
        assert result["cri"] == pytest.approx(70.1766)
        assert result["cct_kelvin"] == pytest.approx(5188)
        assert any(a["kind"] == "native_text" for a in result["artifacts"])
        assert result['input_definition']=='native XYZ tristimulus fitting input'
        assert result['source_object_binding']=='not exposed by installed analysis settings'
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=3,count=2))
        assert page['total']==20 and [r['index'] for r in page['rows']]==[3,4]
        status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert status['state']=='succeeded' and status['close_attempted']
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_nsc_objects',dict(request={}))==objects
        image=e.folder/'spectrum.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(image))))
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        await e.call('new_system',dict(mode='NonSequential'))
        empty_baseline=await e.call('get_system_settings')
        task=await e.call('run_analysis',dict(request=dict(kind='source_spectrum_viewer')))
        for _ in range(1500):
            if task['state'] in ('succeeded','failed','cancelled'):
                break
            await asyncio.sleep(.02)
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state'] in ('succeeded','failed'),task
        empty=await e.call('get_task_result',dict(task_id=task['task_id']))
        assert await e.call('get_system_settings')==empty_baseline
        selected_keys=('input_xyz','fitted_xyz','cri','cct_kelvin','series')
        (e.folder/'input-identity.json').write_text(json.dumps(dict(
            sample={k:result[k] for k in selected_keys},empty_system=empty,
            empty_task=task,identical=all(result[k]==empty.get(k) for k in selected_keys)),indent=2),encoding='utf-8')
    asyncio.run(execute("source_spectrum", work))
