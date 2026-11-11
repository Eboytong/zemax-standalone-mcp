"""Measure the 1.3.0 tool surface over stdio without starting OpticStudio."""
import asyncio
import json
from importlib.metadata import version
import os
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.capability_index import build_index, search


def size(value):
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return dict(utf8_bytes=len(text.encode('utf-8')), characters=len(text))


def reachable_schema(schema, root_schema=None):
    definitions = (schema if root_schema is None else root_schema).get('$defs', {})
    body = {key: value for key, value in schema.items() if key != '$defs'}
    used, pending = {}, [body]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            reference = value.get('$ref', '')
            if reference.startswith('#/$defs/'):
                name = reference.rsplit('/', 1)[-1]
                if name not in used and name in definitions:
                    used[name] = definitions[name]
                    pending.append(definitions[name])
            pending.extend(item for key, item in value.items() if key != '$ref')
        elif isinstance(value, list):
            pending.extend(value)
    return dict(body, **({'$defs': used} if used else {}))


async def main():
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'src')
    parameters = StdioServerParameters(command=sys.executable,
        args=['-B', '-m', 'zemax_mcp'], cwd=str(ROOT), env=environment)
    async with Client(parameters) as client:
        listed = await client.list_tools()
        tools = [tool.model_dump(mode='json', by_alias=True, exclude_none=True)
                 for tool in listed.tools]
    measurements = [dict(name=tool['name'], descriptor=size(tool),
        input=size(tool.get('inputSchema', {})), output=size(tool.get('outputSchema', {})))
        for tool in tools]
    measurements.sort(key=lambda item: -item['input']['utf8_bytes'])
    analysis = next(tool['inputSchema'] for tool in tools if tool['name'] == 'run_analysis')
    mapping = analysis['properties']['request']['discriminator']['mapping']
    variants = []
    for kind, reference in mapping.items():
        wrapper = dict(type='object', properties=dict(request={'$ref': reference}), required=['request'])
        variants.append(dict(kind=kind, reachable_schema=size(reachable_schema(wrapper, analysis))))
    details = []
    for kind in ['wavefront', 'glass_trials', 'design_desensitize', 'sequential_energy_budget']:
        entry = next(item for item in build_index() if item['capability_id'] == 'analysis:' + kind)
        details.append(dict(kind=kind, detail_current=size(entry),
            detail_reachable=size(dict(entry, request_schema=reachable_schema(entry['request_schema'])))))
    bootstrap = ['connect', 'disconnect', 'get_status', 'search_capabilities', 'get_capabilities',
                 'get_task_status', 'get_task_result', 'cancel_task', 'get_request_status']
    report = dict(date='2026-11-11', version=tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version'],
        python=sys.version, python_executable=sys.executable, mcp_sdk_version=version('mcp'),
        import_path=__import__('zemax_mcp').__file__,
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        method='Actual stdio tools/list; compact JSON, ensure_ascii=False; bytes are not model token usage',
        tools=len(tools), analysis_kinds=len(mapping), all_descriptors=size(tools),
        all_inputs=size({tool['name']: tool.get('inputSchema', {}) for tool in tools}),
        largest_inputs=measurements[:15], run_analysis_variants=variants, detail_samples=details,
        search_sample=size(search('计算波前和泽尼克像差', limit=5)),
        bootstrap_existing=dict(requested_names=bootstrap,
            found_names=[tool['name'] for tool in tools if tool['name'] in bootstrap],
            descriptors=size([tool for tool in tools if tool['name'] in bootstrap])), native_started=False)
    directory = ROOT / '.local/evidence/development/PLAN-20261111-DISCLOSURE'
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (directory / 'tools-list.json').write_text(json.dumps(tools, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(evidence=str(directory), tools=len(tools), analysis_kinds=len(mapping),
                         all_descriptors=report['all_descriptors']), ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
