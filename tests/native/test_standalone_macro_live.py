import asyncio
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_standalone_macro_arguments_output_and_process_close():
    async def scenario():
        folder = run_dir("standalone_macro")
        macro = folder / "acceptance.ZPL"
        output = folder / "macro_result.txt"
        macro.write_text(
            f'OUTPUT "{output}"\n'
            'Value$ = $GETARG("Value")\n'
            'PRINT "ARGUMENT=", Value$\n'
            'CLOSE\n',
            encoding="ascii",
        )
        params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "zemax_mcp"],
                                       cwd=PROJECT_ROOT, env={"PYTHONUTF8": "1", "ZEMAX_OUTPUT_DIR": str(folder)})
        async with Client(params, read_timeout_seconds=120) as client:
            async def call(name, arguments=None):
                response = (await client.call_tool(name, arguments or {})).structured_content
                assert response and response["ok"], response
                return response["data"]

            task = await call("run_standalone_macro", {"request": {
                "macro_path": str(macro), "timeout_seconds": 90,
            }})
            for _ in range(1200):
                status = await call("get_task_status", {"task_id": task["task_id"]})
                if status["state"] in {"succeeded", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.1)
            result = await call("get_task_result", {"task_id": task["task_id"]})
            assert status["state"] == "succeeded", result
            assert result["exit_code"] == 0
            assert result["macro_path"] == str(macro.resolve())
            assert "ARGUMENT=" in output.read_text(encoding="utf-8")
            assert status["close_attempted"] is True
            assert Path(result["process_log"]).is_file()

    asyncio.run(scenario())
