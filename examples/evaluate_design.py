"""Evaluate an official local lens through the public MCP stdio interface."""
import asyncio
import sys
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "zemax_mcp"], cwd=PROJECT_ROOT)
    async with Client(params, read_timeout_seconds=120) as client:
        async def call(tool, args=None):
            result = (await client.call_tool(tool, args or {})).structured_content
            if not result or not result["ok"]:
                raise RuntimeError(result)
            return result["data"]
        await call("connect")
        try:
            source = str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
            model = await call("open_lens", {"path": source})
            surface = model["surface_count"]-2
            row = (await call("get_surfaces", {"start": surface, "count": 1}))["surfaces"][0]
            value = row["cells"]["thickness"]["value"]
            task = await call("run_parameter_scan", {"request": {
                "surface": surface, "cell": "thickness", "values": [value-.1,value,value+.1],
                "evaluation": {"spot": {"reference": "Centroid"}}}})
            while task["state"] not in {"succeeded", "failed", "cancelled"}:
                await asyncio.sleep(.1)
                task = await call("get_task_status", {"task_id": task["task_id"]})
            if task["state"] != "succeeded":
                raise RuntimeError(task)
            result = await call("get_task_result", {"task_id": task["task_id"]})
            print(result["summary"])
            print(await call("export_evaluation_report", {"task_ids": [task["task_id"]]}))
        finally:
            await call("disconnect")


if __name__ == "__main__":
    asyncio.run(main())
