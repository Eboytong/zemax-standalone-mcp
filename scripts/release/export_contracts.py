"""Export user-facing schemas from the actual stdio tool catalogs."""
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp import __version__


async def main():
    for mode,name in [('full','tool-schemas.json'),('compact','compact-tool-schemas.json')]:
        params=StdioServerParameters(command=sys.executable,args=['-B','-m','zemax_mcp'],cwd=str(ROOT),
            env=os.environ|{'PYTHONPATH':str(ROOT/'src'),'ZEMAX_TOOL_MODE':mode})
        async with Client(params) as client:
            tools=(await client.list_tools()).tools
        document=dict(service_version=__version__,mode=mode,tools={t.name:t.input_schema for t in sorted(tools,key=lambda t:t.name)})
        (ROOT/'docs/reference'/name).write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(mode,len(tools))

if __name__=='__main__':asyncio.run(main())
