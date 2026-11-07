"""Formal sequential DLL selection and native DiffEfficiency compatibility discovery."""
import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_hologram_dll_analysis_compatibility_probe():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path(r'C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Samples\Sequential\Diffractive components\Transmission hologram.zos'))))
        await e.call('update_system_settings',dict(settings=dict(field_type='Angle')))
        resources=await e.call('get_system_resources',dict(request=dict(kind='surface_files',surface=1,surface_type='UserDefined')))
        names=resources['items']
        selected=next(x for x in names if 'us_hologram_kogelnik' in x.lower())
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='UserDefined',surface_file=selected,replace_solves=True)]))
        await e.call('get_surfaces',dict(start=1,count=1))
        task=await e.call('run_analysis',dict(request=dict(kind='diff_efficiency_angular',surface=1,min_angle=-5,max_angle=5)))
        for _ in range(1000):
            if task['state'] in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state'] in {'succeeded','failed'} and task['close_attempted'],task
        await e.call('get_task_result',dict(task_id=task['task_id']))
    asyncio.run(execute('hologram_dll059',work))
