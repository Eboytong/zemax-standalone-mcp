"""Bounded discovery of native map grid rounding; no assumed numeric acceptance."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from support.native import execute


async def work(e):
    await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
    records=[]
    for nx,ny in [(2,4),(6,8),(5,5),(10,6)]:
        task=await e.call('run_analysis',dict(request=dict(kind='rms_field_map',x_field_sampling=nx,y_field_sampling=ny,method='GaussQuad',rings=3)))
        for _ in range(500):
            if task['state']in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']in {'succeeded','failed'} and task['close_attempted']
        result=await e.call('get_task_result',dict(task_id=task['task_id']),okay=False)
        records.append(dict(requested=[nx,ny],task=task,result=result))
    (e.folder/'sampling.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':asyncio.run(execute('rmsmap078_sampling',work))
