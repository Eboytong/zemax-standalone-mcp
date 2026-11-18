import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Installed package tool/schema discovery without starting an optical application."""
import asyncio,json,sys
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def run(target,folder,version,tool_count=None,analysis_count='146',mode='compact'):
    if tool_count is None: tool_count = '11' if mode == 'compact' else '108'
    target=Path(target).resolve();folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(target))
    import zemax_mcp
    assert Path(zemax_mcp.__file__).resolve().is_relative_to(target)
    assert zemax_mcp.__version__==version
    boot='import sys;sys.path.insert(0,'+repr(str(target))+');from zemax_mcp.server import main;main()'
    p=StdioServerParameters(command=sys.executable,args=['-I','-B','-c',boot],cwd=str(target),env={'PYTHONUTF8':'1','ZEMAX_OUTPUT_DIR':str(folder/'native'),'ZEMAX_TOOL_MODE':mode})
    record=dict(version=version,mode=mode,installed_root=str(target),native_connection_attempted=False)
    session_id, task_id = '2'*32, '3'*32
    legacy = folder/'native'/session_id
    legacy.mkdir(parents=True)
    (legacy/(task_id+'.json')).write_text(json.dumps(dict(
        task=dict(task_id=task_id, kind='analysis', state='succeeded'),
        series=[dict(series=0, description='legacy', x_label='Position', labels=['Intensity'], x=[0], y=[[1]])],
    )), encoding='utf-8')
    async with Client(p,read_timeout_seconds=60)as client:
        ts=await client.list_tools();record['tool_count']=len(ts.tools);assert record['tool_count']==int(tool_count)
        expected={'search_capabilities','manage_candidates','run_candidate_evaluation','get_glass_slots','run_merit_program'} if mode=='full' else {'search_capabilities','query_capability','execute_capability'}
        assert expected <= {tool.name for tool in ts.tools}
        schema = next(tool.input_schema for tool in ts.tools if tool.name == 'execute_capability')
        assert 'request_id' in schema['properties'] and 'request_id' not in schema['required']
        overview=(await client.call_tool('get_capabilities',dict(topic='overview'))).structured_content
        assert overview['ok'] and sum(g['count'] for g in overview['data']['groups'])==overview['data']['total']
        figures=(await client.call_tool('search_capabilities',dict(query='镜头结构图、MTF 曲线、标准点列图'))).structured_content
        assert figures['ok'] and {'tool:run_layout_export','tool:run_fft_mtf','tool:run_spot_analysis','tool:export_analysis_image'} <= {item['capability_id'] for item in figures['data']['items']}
        search=(await client.call_tool('search_capabilities',dict(query='逐面能量损耗',limit=5))).structured_content
        assert search['ok'];record['offline_search']=search
        result=(await client.call_tool('get_capabilities',dict(topic='tool',tool_name='run_analysis'))).structured_content
        assert result['ok'];schema=result['data']['request_schema'];mapping=schema['properties']['request']['discriminator']['mapping']
        record['analysis_kind_count']=len(mapping);assert record['analysis_kind_count']==int(analysis_count)
        assert {'design_desensitize','sequential_energy_budget'}<=mapping.keys()
        assert {'system_check','system_data','surface_phase_slope','surface_phase_slope_cross','rms_field_map','rms_vs_wavelength','tolerance_yield','tolerance_histogram','geometric_image','zernike_coefficients_vs_field'}<=mapping.keys()
        assert {'universal_plot_1d','universal_plot_2d','paraxial_gaussian_beam','skew_gaussian_beam'}<=mapping.keys()
        record['actual_schema']=result
        status=(await client.call_tool('get_status')).structured_content;assert status['ok'];record['status']=status
        assert status['data']['server_version']==version and status['data']['tool_mode']==mode
        assert status['data']['capability_index_version']>=2
        request_id='1'*32
        payload=dict(capability_id='tool:get_status',arguments={},request_id=request_id)
        first=(await client.call_tool('execute_capability',payload)).structured_content
        second=(await client.call_tool('execute_capability',payload)).structured_content
        receipt=(await client.call_tool('get_request_status',dict(request=dict(request_id=request_id)))).structured_content
        assert first==second and first['ok'] and first['context']['request_id']==request_id
        assert receipt['data']['observed_execution_state']=='returned'
        conflict=(await client.call_tool('execute_capability', {**payload, 'capability_id':'tool:disconnect'})).structured_content
        assert conflict['error']['code']=='REQUEST_ID_CONFLICT'
        history_payload=dict(request=dict(session_id=session_id,task_id=task_id,series=0))
        if mode=='compact':
            historical=(await client.call_tool('query_capability',dict(
                capability_id='tool:get_historical_result',arguments=history_payload))).structured_content
        else:
            historical=(await client.call_tool('get_historical_result',history_payload)).structured_content
        assert historical['ok'] and historical['data']['history']['result_schema_version']==0
        assert historical['data']['provenance']['model_revision'] is None
        assert historical['data']['series'][0]['axes']['x']==dict(label='Position',unit=None)
        if mode=='compact':
            queried=(await client.call_tool('query_capability',dict(capability_id='tool:get_status',arguments={}))).structured_content
            assert queried['ok'] and not queried['data']['connected']
            rejected=(await client.call_tool('query_capability',dict(capability_id='tool:new_system',arguments={}))).structured_content
            assert rejected['error']['code']=='READ_ONLY_REQUIRED'
    async with Client(p, read_timeout_seconds=60) as restarted:
        receipt=(await restarted.call_tool('get_request_status',dict(request=dict(request_id=request_id)))).structured_content
        replay=(await restarted.call_tool('execute_capability',payload)).structured_content
        assert receipt['data']['observed_execution_state']=='returned' and replay==first
    record['stdio_closed']=True
    (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k]for k in ['version','tool_count','analysis_kind_count','stdio_closed']}))

if __name__=='__main__':asyncio.run(run(*sys.argv[1:]))
