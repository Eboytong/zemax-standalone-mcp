import asyncio
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from zemax_mcp.config import PROJECT_ROOT
from zemax_mcp.models import COMMAND_MODELS


def test_stdio_tools_and_validation_without_zemax():
    async def scenario():
        params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "zemax_mcp"], cwd=PROJECT_ROOT,
                                      env={"PYTHONPATH":str(PROJECT_ROOT/"src"),"PYTHONUTF8":"1"})
        async with Client(params) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == set(COMMAND_MODELS)
            status = await client.call_tool("get_status", {})
            assert status.structured_content["ok"]
            assert status.structured_content["data"]["connected"] is False
            bad = await client.call_tool("get_surfaces", {"count": 0})
            assert bad.structured_content["error"]["code"] == "INVALID_ARGUMENT"
            capabilities = await client.call_tool("get_capabilities", {})
            assert capabilities.structured_content["data"]["modes"]["NonSequential"] == "implemented"
    asyncio.run(scenario())
