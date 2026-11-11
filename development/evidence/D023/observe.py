"""Six cold stdio discovery trials and a frozen retrieval corpus."""
import asyncio
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import io
import zipfile
from importlib.metadata import version

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.capability_index import build_index, search


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


async def main():
    folder = ROOT / '.local/evidence/development/D023'
    folder.mkdir(parents=True, exist_ok=True)
    cases = json.loads((Path(__file__).parent / 'tasks.json').read_text(encoding='utf-8'))
    baseline = ROOT / '.local/builds/disclosure-baseline130'
    if not (baseline/'src/zemax_mcp/server.py').is_file():
        baseline.mkdir(parents=True,exist_ok=True)
        archive = subprocess.check_output(['git','archive','--format=zip','83b5ea783efa7dec5f57c225bda01e422ab881b0','src'],cwd=ROOT)
        zipfile.ZipFile(io.BytesIO(archive)).extractall(baseline)
    ids = {e['capability_id'] for e in build_index()}
    assert all(set(c['expected']) <= ids for c in cases)
    trials = []
    for case in cases[:6]:
        start = time.perf_counter()
        parameters = StdioServerParameters(command=sys.executable, args=['-B', '-m', 'zemax_mcp'],
            cwd=str(baseline), env=os.environ | {'PYTHONPATH': str(baseline/'src'), 'ZEMAX_TOOL_MODE':'full'})
        async with Client(parameters) as client:
            tools = (await client.list_tools()).tools
            response = (await client.call_tool('search_capabilities', {'query': case['query']})).structured_content
            assert response['ok'], response
            status = (await client.call_tool('get_status')).structured_content
            assert status['ok'] and not status['data']['connected']
        trials.append(dict(task=case['id'], baseline_commit='83b5ea783efa7dec5f57c225bda01e422ab881b0', source=str(baseline/'src'), tools=len(tools), descriptors_bytes=size([t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools]),
            response_bytes=size(response), elapsed_seconds=time.perf_counter()-start, disconnected=True,
            usage=None, usage_source='MCP transport has no model usage field'))
    results = []
    for c in cases:
        found = [e['capability_id'] for e in search(c['query'])['items']]
        results.append(dict(id=c['id'], found=found, expected=c['expected'], passed=bool(set(found)&set(c['expected'])) if c['expected'] else not found))
    report = dict(python=sys.version, executable=sys.executable, mcp=version('mcp'), platform=platform.platform(),
        source=str(__import__('zemax_mcp').__file__), cli=subprocess.check_output(['codex','--version'],text=True).strip(),
        trials=trials, retrieval=results, passed=sum(c['passed'] for c in results), total=len(cases),
        host_observation={'catalog':'This Codex session exposes mcp__zemax through deferred tool metadata, available via tool discovery.',
            'definition_injection':'Host internal prompt assembly unavailable via MCP; actual injected token count unobservable.',
            'cache_hits':None,'usage':None,'native_discovery':'Available in current host; no per-server defer_loading configuration asserted.',
            'API_search':'No independent Responses API inference session configured for this benchmark.'})
    (folder/'observations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],total=len(cases),trials=len(trials),evidence=str(folder))))

if __name__ == '__main__': asyncio.run(main())
