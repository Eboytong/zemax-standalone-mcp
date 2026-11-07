"""Optional mapping preserves native waves, supports regular primary displays and rejects unverified wavelengths."""
import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_optional_pupil_mapping_native():
    async def work(e):
        await e.call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        for exit_pupil in (False,True):
            for remove_tilt in (False,True):
                q=dict(kind="wavefront",field=2,wavelength=2,remove_tilt=remove_tilt,use_exit_pupil=exit_pupil)
                raw=(await e.finish(await e.call("run_analysis",dict(request=q))))["grids"][0]
                mapped=(await e.finish(await e.call("run_analysis",dict(request=dict(q,include_pupil_mapping=True)))))["grids"][0]
                for iy,ix in ((32,32),(24,32),(32,24)):
                    e.check("mapping preserves wavefront waves",mapped["values"][iy][ix],raw["values"][iy][ix])
                mapping=mapped["pupil_mapping"]
                if exit_pupil:
                    assert mapping['status']=='verified_regular_display_mapping'
                    assert mapping['points'][32][32]['valid']
                    e.check('exit display center entrance Px',mapping['points'][32][32]['px'],0)
                    assert mapping['points'][32][32]['coordinate_error']<=1e-8
                    assert 'reported separately'in mapped['coordinate_validation']
                else:
                    assert mapping["points"][32][32]["valid"]and not mapping["points"][0][0]["valid"]
                    e.check("entrance mapping Px",mapping["points"][24][32]["px"],0)
                    e.check("entrance mapping Py",mapping["points"][24][32]["py"],-8/31)
                    # Keep a mapped task explicitly for public region/report checks.
                    task=await e.call("run_analysis",dict(request=dict(q,include_pupil_mapping=True)))
                    saved=await e.finish(task);task_id=task["task_id"]
                    page=await e.call("get_task_result",dict(task_id=task_id,grid=0,x_start=32,y_start=24,width=1,height=1))
                    assert len(page["grid"]["pupil_mapping"]["points"])==1
                    e.check("mapping region Py",page["grid"]["pupil_mapping"]["points"][0][0]["py"],-8/31)
                    report=await e.call("export_evaluation_report",dict(task_ids=[task_id]))
                    assert any(a["path"].endswith("pupil_mapping.csv")for a in report["artifacts"])
        unsupported=await e.finish(await e.call('run_analysis',dict(request=dict(kind='wavefront',field=2,wavelength=1,
            remove_tilt=False,use_exit_pupil=True,include_pupil_mapping=True))))
        mapping=unsupported['grids'][0]['pupil_mapping']
        assert mapping['status']=='unsupported_regular_reference'and 'non-primary'in mapping['error_status']
        assert all(p['px']is None and not p['valid']for row in mapping['points']for p in row)
    asyncio.run(execute("optional_pupil_mapping",work))
