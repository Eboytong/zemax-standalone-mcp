"""Controlled option differences after the default conversion startup failure."""
import asyncio,json
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_conversion_option_discovery():
    async def work(e):
        records=[]
        for label,options in [('no_stop',dict(convert_stop_to_nsc_aperture=False)),('ignore_errors',dict(ignore_errors=True)),('pure',dict(mode='pure',convert_stop_to_nsc_aperture=False))]:
            await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
            response=await e.call('run_nsc_conversion',dict(request=options),okay=False)
            records.append(dict(label=label,response=response))
            if response.get('ok') is not False:
                task=response
                for _ in range(1000):
                    if task['state'] in {'succeeded','failed','cancelled'}:break
                    await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
                records[-1]['terminal']=task
            await e.call('get_system_summary')
        (e.folder/'option-results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('conversion_options062',work))
