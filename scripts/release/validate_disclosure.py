"""Measure discovery budgets and compare native full/compact wavefront results."""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--installed',type=Path)
parser.add_argument('--output',type=Path,default=ROOT/'.local/v141-disclosure')
OPTIONS=parser.parse_args()
OUT=OPTIONS.output.resolve()
OUT.mkdir(parents=True,exist_ok=True)
PACKAGE=OPTIONS.installed.resolve() if OPTIONS.installed else ROOT/'src'
sys.path.insert(0,str(PACKAGE))
import zemax_mcp
assert Path(zemax_mcp.__file__).resolve().is_relative_to(PACKAGE)
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.capability_index import search,describe,build_index
from zemax_mcp.models import Capabilities

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def size(value):
    return len(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf-8'))

def recall(cases):
    rows=[]
    for case in cases:
        expected=set(case['expected'])
        items=search(case['query'],limit=5)['items']
        got=[x['capability_id'] for x in items]
        rows.append(dict(query=case['query'],expected=sorted(expected),returned=got,
            top1=bool(expected.intersection(got[:1])) if expected else not got,
            top5=bool(expected.intersection(got)) if expected else not got))
    return dict(count=len(rows),top1=sum(x['top1'] for x in rows),top5=sum(x['top5'] for x in rows),
        failures=[x for x in rows if not x['top5']],rows=rows)

def discovery_metrics():
    index=build_index()
    datasets={
        'existing_30':json.loads((ROOT/'tests/fixtures/capability_queries.json').read_text(encoding='utf-8')),
        'existing_60':json.loads((ROOT/'development/evidence/D023/tasks.json').read_text(encoding='utf-8')),
        'additional_12':[
            dict(query='检查镜头的波前像差',expected=['analysis:wavefront']),
            dict(query='计算调制传递函数评价成像清晰度',expected=['tool:run_fft_mtf']),
            dict(query='查询光学材料的折射率与色散',expected=['tool:get_material_properties']),
            dict(query='求镀膜的反射透射和吸收',expected=['tool:get_coating_rta']),
            dict(query='寻找最佳焦点使光斑最小',expected=['tool:run_quick_focus','analysis:rms_vs_focus']),
            dict(query='导出三维光路布局图',expected=['tool:run_layout_export']),
            dict(query='分析加工误差引起的成像合格率',expected=['tool:run_tolerance_analysis','analysis:design_desensitize']),
            dict(query='把镜片中心厚度改成五毫米',expected=['tool:update_surfaces']),
            dict(query='这个镜头看东西有多清楚',expected=['tool:run_fft_mtf','tool:run_spot_analysis']),
            dict(query='追踪杂散光到光电接收面的能量分布',expected=['tool:run_nsc_ray_trace','tool:get_detector_data']),
            dict(query='读取先前算过的结果',expected=['tool:get_historical_result','tool:list_task_history','tool:get_task_result']),
            dict(query='计算高斯光束经过系统后的复振幅',expected=['tool:run_pop']),
        ],
    }
    wave=describe(Capabilities(topic='detail',capability_id='analysis:wavefront'))
    batch=describe(Capabilities(topic='detail',capability_id='tool:run_batch_evaluation',analysis_kinds=['wavefront']))
    return dict(capabilities=len(index),categories={kind:sum(x['category']==kind for x in index)
        for kind in ['tool','analysis','action']},search={k:recall(v) for k,v in datasets.items()},
        wavefront_detail_bytes=size(wave),wavefront_definitions=list(wave['request_schema'].get('$defs',{})),
        batch_selected_definitions=list(batch['request_schema'].get('$defs',{})))

async def run_mode(mode):
    requested_mode=mode
    mode=mode or 'compact'
    folder=OUT/(requested_mode or 'default')
    folder.mkdir(exist_ok=True)
    boot='import sys;from pathlib import Path;sys.path.insert(0,'+repr(str(PACKAGE))+');import zemax_mcp;assert Path(zemax_mcp.__file__).resolve().is_relative_to(Path('+repr(str(PACKAGE))+'));from zemax_mcp.server import main;main()'
    params=StdioServerParameters(command=sys.executable,args=['-I','-B','-c',boot],cwd=str(PACKAGE),env={
        **os.environ,'PYTHONPATH':str(PACKAGE),'ZEMAX_TOOL_MODE':mode,'PYTHONUTF8':'1',
        'ZEMAX_INSTALL_DIR':r'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio',
        'ZEMAX_OUTPUT_DIR':str(folder/'runs'),'ZEMAX_STATE_DIR':str(folder/'state')})
    if requested_mode is None: params.env.pop('ZEMAX_TOOL_MODE',None)
    record=dict(mode=mode,requested_mode=requested_mode,version=zemax_mcp.__version__,package=str(PACKAGE),calls=[],checks={})
    async with Client(params,read_timeout_seconds=180) as client:
        async def raw(name,args=None):
            t=time.perf_counter()
            response=(await client.call_tool(name,args or {})).structured_content
            record['calls'].append(dict(tool=name,arguments=args or {},seconds=time.perf_counter()-t,response=response))
            return response
        async def call(name,args=None):
            response=await raw(name,args)
            assert response and response['ok'],response
            return response['data']
        async def operation(name,args=None,readonly=False):
            if mode=='full':return await call(name,args)
            return await call('query_capability' if readonly else 'execute_capability',
                dict(capability_id='tool:'+name,arguments=args or {}))
        try:
            tools=(await client.list_tools()).tools
            tool_names=[x.name for x in tools]
            record['tools']=tool_names
            record['tools_list_bytes']=size([t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools])
            record['input_schema_bytes']=sum(size(t.input_schema) for t in tools)
            assert len(tools)==(107 if mode=='full' else 11)
            if mode=='compact': assert record['tools_list_bytes']<=20000
            found=await call('search_capabilities',dict(query='OPD wavefront',limit=5))
            selected=next(x for x in found['items'] if x['capability_id']=='analysis:wavefront')
            detail=await call('get_capabilities',selected['detail_request'])
            assert set(detail['request_schema']['$defs'])=={'WavefrontAnalysis'}
            record['search_data_bytes']=size(found)
            record['detail_data_bytes']=size(detail)
            assert record['search_data_bytes']<=8000
            assert record['detail_data_bytes']<=2000
            assert not (await call('get_status'))['connected']
            record['checks']['offline_discovery']=True
            connected=await call('connect',dict(install_dir=r'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio'))
            record['connect']=connected
            lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
            await operation('open_lens',dict(path=str(lens)))
            settings=await operation('get_system_settings',readonly=True)
            record['checks']['readonly_query']=bool(settings['wavelengths'])
            if mode=='compact':
                before=(await call('get_status'))['model_revision']
                for name,args,expected in [
                    ('query_capability',dict(capability_id='tool:new_system',arguments={}), 'READ_ONLY_REQUIRED'),
                    ('execute_capability',dict(capability_id='analysis:wavefront',arguments={'request':{'kind':'spot'}}),'CAPABILITY_MISMATCH'),
                    ('execute_capability',dict(capability_id='tool:get_status',arguments={'unknown':1}),'INVALID_ARGUMENT'),
                    ('execute_capability',dict(capability_id='tool:missing',arguments={}), 'UNKNOWN_CAPABILITY')]:
                    bad=await raw(name,args)
                    assert not bad['ok'] and bad['error']['code']==expected,bad
                    record['checks'][expected]=True
                assert (await call('get_status'))['model_revision']==before
                record['checks']['rejected_calls_preserved_revision']=True
            request=dict(field=1,wavelength=1,sampling='S_64x64')
            if mode=='compact':
                task=await call('execute_capability',dict(capability_id=selected['capability_id'],arguments={'request':request}))
            else:task=await call('run_analysis',dict(request=dict(kind='wavefront',**request)))
            request_id=task['request_id']
            deadline=time.monotonic()+120
            while task['state'] not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline,'wavefront timeout'
                await asyncio.sleep(.05)
                task=await call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='succeeded',task
            result=await call('get_task_result',dict(task_id=task['task_id']))
            record['request_receipt']=await call('get_request_status',dict(request=dict(request_id=request_id)))
            artifacts=result.get('artifacts') or []
            payload=result
            for artifact in artifacts:
                if artifact.get('kind')=='json' and Path(artifact['path']).stem==task['task_id']:
                    payload=json.loads(Path(artifact['path']).read_text(encoding='utf-8'));break
            grid=payload['grids'][0]
            record['grid']=grid
            assert grid['nx']>0 and grid['ny']>0
            record['checks']['analysis_completed']=True
            record['checks']['directory_stable']=[x.name for x in (await client.list_tools()).tools]==tool_names
            assert record['checks']['directory_stable']
        finally:
            try:await call('disconnect')
            finally:dump(folder/'evidence.json',record)
    return record

async def main():
    result={'version':zemax_mcp.__version__,'discovery':discovery_metrics()}
    for data in result['discovery']['search'].values(): assert data['top5']==data['count'],data['failures']
    compound=search('读取波前再保存候选设计')
    assert {'analysis:wavefront','tool:manage_candidates'} <= {item['capability_id'] for item in compound['items']}
    assert size(compound)<=8000
    result['compound']=compound
    modes=[]
    for mode in ['full','compact',None]:
        print('START',mode,flush=True)
        modes.append(await run_mode(mode))
        print('DONE',mode,flush=True)
    full,compact=modes[:2]
    a,b=full['grid'],compact['grid']
    assert (a['nx'],a['ny'])==(b['nx'],b['ny'])
    finite=[];nan_pairs=0
    for ra,rb in zip(a['values'],b['values'],strict=True):
        for va,vb in zip(ra,rb,strict=True):
            if va is None or vb is None:
                assert va is vb;nan_pairs+=1
            elif math.isfinite(va) and math.isfinite(vb):finite.append(abs(va-vb))
            else:assert not math.isfinite(va) and not math.isfinite(vb)
    assert finite and max(finite)<=1e-12
    result['native_equivalence']=dict(nx=a['nx'],ny=a['ny'],finite_points=len(finite),null_points=nan_pairs,
        maximum_absolute_difference=max(finite),tolerance=1e-12)
    result['modes']=[{k:r[k] for k in ['mode','requested_mode','tools','tools_list_bytes','input_schema_bytes',
        'search_data_bytes','detail_data_bytes','checks']} for r in modes]
    result['initial_bytes_reduction_percent']=100*(1-compact['tools_list_bytes']/full['tools_list_bytes'])
    dump(OUT/'summary.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='discovery'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':asyncio.run(main())
