"""Run the frozen protocol/native scenarios through full and compact serially."""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from tests.support.native import Evidence
from tests.support.disclosure_cases import run_case
from zemax_mcp.disclosure import BOOTSTRAP,READ_ONLY


def signatures(calls):
    output=[]
    for item in calls:
        name=item['tool'];args=item.get('arguments') or {}
        if name in {'execute_capability','query_capability'}:
            name=args['capability_id'].removeprefix('tool:')
        data=item['response'].get('data') or {}
        if name=='get_task_result':
            value={key:data[key] for key in ['series','grids','grid','metrics'] if key in data}
            if 'rows' in data:
                value['rows']=[{k:r[k] for k in ['x','y','z','l','m','n','values','after'] if k in r} for r in data['rows']]
            if value:output.append(dict(tool=name,values=value))
        elif name=='get_detector_data':
            output.append(dict(tool=name,values={k:data[k] for k in ['values','total_flux','nx','ny'] if k in data}))
        elif name=='evaluate_merit_function':
            output.append(dict(tool=name,values=data['merit_function']))
    return output


class Routed(Evidence):
    def __init__(self,client,folder,mode):
        super().__init__(client,folder);self.mode=mode
    async def call(self,name,args=None,okay=True):
        if self.mode=='compact' and name not in BOOTSTRAP:
            args=dict(capability_id='tool:'+name,arguments=args or {})
            name='query_capability' if name in READ_ONLY else 'execute_capability'
        return await super().call(name,args,okay)


async def main():
    folder=ROOT/'.local/evidence/development/D027'
    folder.mkdir(parents=True,exist_ok=True)
    cases=json.loads((ROOT/'development/evidence/D023/end_to_end.json').read_text(encoding='utf-8'))
    selected=set(sys.argv[1:])
    records=[]
    path=folder/'comparison.json'
    if path.exists():records=json.loads(path.read_text(encoding='utf-8'))['cases']
    for i,case in enumerate(cases):
        if selected and case['id'] not in selected:continue
        for mode in (['full','compact'] if i%2==0 else ['compact','full']):
            if any(r['case']==case['id'] and r['mode']==mode and r['passed'] for r in records):continue
            owned=folder/(case['id']+'-'+mode);owned.mkdir(exist_ok=True)
            env=os.environ|{'PYTHONPATH':str(ROOT/'src'),'ZEMAX_TOOL_MODE':mode,
                'ZEMAX_OUTPUT_DIR':str(owned),'ZEMAX_STATE_DIR':str(owned/'state')}
            params=StdioServerParameters(command=sys.executable,args=['-B','-m','zemax_mcp'],cwd=str(ROOT),env=env)
            e=None;started=time.perf_counter();record=dict(case=case['id'],mode=mode,passed=False,usage=None)
            try:
                async with Client(params,read_timeout_seconds=180) as client:
                    e=Routed(client,owned,mode)
                    tools=(await client.list_tools()).tools
                    record['catalog_bytes']=len(json.dumps([t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools],ensure_ascii=False,separators=(',',':')).encode())
                    await e.call('connect')
                    try:
                        await run_case(e,case['id'])
                    finally:
                        await e.call('disconnect')
                record.update(passed=True,closed=True)
            except BaseException as exc:
                record['error']=str(exc)
                (owned/'error.txt').write_text(''.join(traceback.format_exception(exc)),encoding='utf-8')
            finally:
                record['elapsed_seconds']=time.perf_counter()-started
                if e:
                    (owned/'calls.json').write_text(json.dumps(e.calls,ensure_ascii=False,indent=2),encoding='utf-8')
                    (owned/'checks.json').write_text(json.dumps(e.checks,ensure_ascii=False,indent=2),encoding='utf-8')
                    (owned/'signature.json').write_text(json.dumps(signatures(e.calls),ensure_ascii=False,indent=2),encoding='utf-8')
                records=[r for r in records if not(r['case']==case['id'] and r['mode']==mode)]+[record]
                path.write_text(json.dumps(dict(method='Deterministic MCP/native integration; no model inference or token usage',cases=records),ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(record,ensure_ascii=False),flush=True)

if __name__=='__main__':asyncio.run(main())
