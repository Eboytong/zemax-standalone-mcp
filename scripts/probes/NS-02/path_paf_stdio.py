"""Check PAF request rejection and default reading through the real stdio client."""
import asyncio
import json
from pathlib import Path
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tests.support.native import execute

async def run(record_path):
    record=json.loads(Path(record_path).read_text(encoding='utf-8'))
    paf=next(item['path'] for item in record['generated'] if item['path'].lower().endswith('.paf'))
    model=record['close_receipt']['checkpoint']['path']
    async def work(e):
        await e.call('open_lens',dict(path=model))
        before={tool:await e.call(tool,dict(request={}) if tool=='get_nsc_objects' else {}) for tool in ('get_system_settings','get_nsc_objects','get_merit_function')}
        base=dict(kind='path_analysis',path=paf)
        for change in (dict(relative_minimum_flux=.5),dict(relative_minimum_flux=1),dict(first_ray=2),dict(last_ray=10),dict(filter='H3')):
            arguments=dict(request=base|change)
            reply=await e.client.call_tool('run_analysis',arguments)
            raw=reply.model_dump(mode='json')
            e.calls.append(dict(tool='run_analysis',arguments=arguments,raw_response=raw))
            assert reply.is_error,raw
        saved=str(e.folder/'paf_baseline.zos')
        await e.call('save_lens_as',dict(path=saved))
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=saved))
            result=await e.finish(await e.call('run_analysis',dict(request=base)))
            assert len(result['rows'])==2,result
            e.check('PAF classified power reload='+str(reload),sum(row['flux_out_w'] for row in result['rows']),record['reference_detector_w'])
            pages=[await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=start,count=1)) for start in (0,1)]
            assert [page['rows'][0] for page in pages]==result['rows']
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted'],status
        after={tool:await e.call(tool,dict(request={}) if tool=='get_nsc_objects' else {}) for tool in before}
        assert before==after
    await execute('path_paf_adoption',work)

if __name__=='__main__':asyncio.run(run(sys.argv[1]))
