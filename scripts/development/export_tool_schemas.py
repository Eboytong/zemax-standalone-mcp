"""Refresh the checked-in MCP request schema reference from runtime models."""
import json
import asyncio
import os
import sys
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from mcp import Client
from mcp.client.stdio import StdioServerParameters

async def export():
    environment=os.environ.copy()
    environment["PYTHONPATH"]=str(ROOT/"src")
    parameters=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=str(ROOT),env=environment)
    async with Client(parameters) as client:
        listed=await client.list_tools()
    version=tomllib.loads((ROOT/"pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    schema={"service_version":version,"tools":{tool.name:tool.input_schema for tool in sorted(listed.tools,key=lambda value:value.name)}}
    (ROOT/"docs/reference/tool-schemas.json").write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

asyncio.run(export())
