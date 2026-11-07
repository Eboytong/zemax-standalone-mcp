"""Inspect actual ASAT/ASAB declarations without assuming SAT/SAB framing."""
import asyncio
import json
from pathlib import Path
import time

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_native_advanced_acis_format_declarations():
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',material='N-BK7',thickness=2,semi_diameter=2,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=3,semi_diameter=2,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        records=[]
        for fmt in ['ASAT','ASAB']:
            q=dict(path=str(e.folder/('current.'+fmt.lower())),format=fmt,end=2,file_version='Current')
            task=await e.call('run_cad_export',dict(request=q),okay=False)
            start_failure=None
            if task.get('ok') is False:
                start_failure=task
                task=await e.call('get_task_status',dict(task_id=task['error']['details']['task_id']))
            deadline=time.monotonic()+90
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02)
                task=await e.call('get_task_status',dict(task_id=task['task_id']))
            result=await e.call('get_task_result',dict(task_id=task['task_id']))
            item=dict(request=q,task=task,result=result,start_failure=start_failure)
            records.append(item)
            if task['state']=='succeeded':
                path=Path(q['path'])
                with path.open('rb')as stream:prefix=stream.read(256)
                item.update(size_bytes=path.stat().st_size,prefix_hex=prefix.hex(),
                    prefix_text=prefix.decode('ascii',errors='replace'))
            assert task['close_attempted'] and not task.get('cleanup_warnings')
            (e.folder/'declarations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('cad521_advanced_acis',work))
