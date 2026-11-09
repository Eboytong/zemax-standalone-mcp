import asyncio
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_yni_contributions_cooke_native_report():
    async def work(e):
        await e.call("open_lens", dict(path=str(Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        baseline = await e.call("get_system_settings")
        result = await e.finish(await e.call("run_analysis", dict(request=dict(kind="yni_contributions"))))
        assert result["computation_method"] == "native_YNIContributions_report"
        assert result["wavelength_um"] == pytest.approx(0.55)
        assert result["position_unit"] == "Millimeters"
        assert [row["surface"] for row in result["rows"]] == [1, 2, 3, 4, 5, 6]
        expected = [1.13566, -0.74972, -1.22579, 1.00110, 0.53408, -1.40214]
        for row, value in zip(result["rows"], expected):
            e.check("native YNI report value", row["value"], value, atol=1e-12, rtol=0)
        assert any(a["kind"] == "native_text" for a in result["artifacts"])
        page = await e.call("get_task_result", dict(task_id=result["task"]["task_id"],start=2,count=2))
        assert page['total'] == 6
        assert [r['surface'] for r in page['rows']] == [3,4]
        terminal = await e.call("get_task_status",dict(task_id=result["task"]["task_id"]))
        assert terminal['state'] == 'succeeded' and terminal['close_attempted']
        assert await e.call("get_system_settings") == baseline
    asyncio.run(execute("yni_contributions", work))


@pytest.mark.zemax
def test_yni_explicit_wave_operand_report_and_spherical_reference():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        original=await e.call('get_system_settings')
        report=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yni_contributions'))))
        operand=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yni_contributions',wavelength=2))))
        assert operand['computation_method']=='native_YNIP_operand'
        assert operand['actual_settings']['wavelength']==2
        assert operand['wavelength_um']==.55
        assert len(operand['rows'])==len(report['rows'])
        for row,ref in zip(operand['rows'],report['rows']):
            assert row['surface']==ref['surface']
            e.check('YNIP versus five-decimal report',row['value'],ref['value'],atol=5e-6,rtol=0)
        first=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yni_contributions',wavelength=1))))
        assert first['wavelength_um']==.48
        assert abs(first['rows'][1]['value']-operand['rows'][1]['value'])>1e-4
        page=await e.call('get_task_result',dict(task_id=operand['task']['task_id'],start=2,count=2))
        assert [r['surface'] for r in page['rows']]==[3,4]
        assert await e.call('get_system_settings')==original
        await e.model()
        for radius in (20,-20):
            await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=radius,material='N-BK7',replace_solves=True)]))
            actual=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yni_contributions',wavelength=1))))
            # Collimated air-space marginal ray: Y=5, N=1, I=Y/R.
            e.check('signed spherical Y*N*I',actual['rows'][0]['value'],25/radius,atol=1e-10,rtol=1e-10)
    asyncio.run(execute('yni_explicit_wave',work))
