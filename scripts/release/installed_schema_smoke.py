import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Installed package tool/schema discovery without starting an optical application."""
import asyncio,json,sys
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def run(target,folder,version,tool_count='101',analysis_count='132'):
    target=Path(target).resolve();folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(target))
    import zemax_mcp
    assert Path(zemax_mcp.__file__).resolve().is_relative_to(target)
    assert zemax_mcp.__version__==version
    boot='import sys;sys.path.insert(0,'+repr(str(target))+');from zemax_mcp.server import main;main()'
    p=StdioServerParameters(command=sys.executable,args=['-I','-B','-c',boot],cwd=str(target),env={'PYTHONUTF8':'1','ZEMAX_OUTPUT_DIR':str(folder/'native')})
    record=dict(version=version,installed_root=str(target),native_connection_attempted=False)
    async with Client(p,read_timeout_seconds=60)as client:
        ts=await client.list_tools();record['tool_count']=len(ts.tools);assert record['tool_count']==int(tool_count)
        result=(await client.call_tool('get_capabilities',dict(topic='tool',tool_name='run_analysis'))).structured_content
        assert result['ok'];schema=result['data']['request_schema'];mapping=schema['properties']['request']['discriminator']['mapping']
        record['analysis_kind_count']=len(mapping);assert record['analysis_kind_count']==int(analysis_count)
        assert {'system_check','system_data','surface_phase_slope','surface_phase_slope_cross','rms_field_map','rms_vs_wavelength','tolerance_yield','tolerance_histogram','geometric_image','zernike_coefficients_vs_field'}<=mapping.keys()
        assert {'universal_plot_1d','universal_plot_2d','paraxial_gaussian_beam','skew_gaussian_beam'}<=mapping.keys()
        record['actual_schema']=result
        status=(await client.call_tool('get_status')).structured_content;assert status['ok'];record['status']=status
    record['stdio_closed']=True
    (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k]for k in ['version','tool_count','analysis_kind_count','stdio_closed']}))

if __name__=='__main__':asyncio.run(run(*sys.argv[1:]))
