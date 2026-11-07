import asyncio
import json
import os
import subprocess
import sys
import uuid
from .errors import ZemaxError


class Bridge:
    def __init__(self):
        self.process = None
        self.reader_task = None
        self.pending = {}
        self.inflight_metadata = {}
        self.start_lock = asyncio.Lock()

    async def start(self):
        async with self.start_lock:
            if self.process is not None and self.process.returncode is None:
                return
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, "-B", "-u", "-m", "zemax_mcp.worker",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=sys.stderr, creationflags=subprocess.CREATE_NO_WINDOW,
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                limit=16 * 1024 * 1024,
            )
            self.reader_task = asyncio.create_task(self._read())

    async def _read(self):
        process = self.process
        try:
            while line := await process.stdout.readline():
                prefix, separator, payload = line.partition(b"@zemax-ipc ")
                if prefix.strip():
                    print(prefix.decode("utf-8", errors="replace").rstrip(), file=sys.stderr, flush=True)
                if not separator:
                    continue
                frame = json.loads(payload)
                future = self.pending.pop(frame["id"], None)
                self.inflight_metadata.pop(frame["id"], None)
                if future is not None and not future.done():
                    future.set_result(frame["response"])
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(ConnectionError("Zemax worker exited; native execution state is unknown."))
            self.pending.clear()
            self.inflight_metadata.clear()

    async def request(self, command, arguments=None, timeout=60):
        try:
            lookup=(arguments or {}).get("request_id")
            if command == "get_request_status" and lookup in self.pending:
                from .config import Config
                from .history import REQUEST_ID, read_json
                if isinstance(lookup,str) and REQUEST_ID.fullmatch(lookup):
                    root=Config.from_env().output_dir.resolve()
                    path=(root/"_requests"/(lookup+".json")).resolve()
                    if path.is_relative_to(root):
                        if path.is_file():
                            record=read_json(path)
                            record["observed_execution_state"]=record.get("state","dispatching")
                        else:
                            record={"request_id":lookup,"observed_execution_state":"queued_or_dispatching",**self.inflight_metadata.get(lookup,{})}
                        return {"ok":True,"data":record,"error":None,"context":{"request_id":lookup},"warnings":[],"artifacts":[]}
            await self.start()
            request_id = uuid.uuid4().hex
            future = asyncio.get_running_loop().create_future()
            # Consume late exceptions after a timed-out or cancelled MCP request.
            future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
            self.pending[request_id] = future
            self.inflight_metadata[request_id] = {"command":command,"worker_pid":self.process.pid}
            frame = {"id": request_id, "command": command, "arguments": arguments or {}}
            self.process.stdin.write((json.dumps(frame, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
            await self.process.stdin.drain()
            try:
                return await asyncio.wait_for(asyncio.shield(future), timeout)
            except TimeoutError:
                return {"ok": False, "data": None, "context": {}, "warnings": [], "artifacts": [],
                        "error": {"code": "REQUEST_TIMEOUT", "message": "请求等待超时；原生操作可能仍在执行，请勿直接重试修改。",
                                  "details": {"request_id": request_id, "execution_state": "unknown"}}}
        except ZemaxError as exc:
            return {"ok":False,"data":None,"context":{},"warnings":[],"artifacts":[],"error":exc.as_dict()}
        except (ConnectionError, BrokenPipeError, OSError) as exc:
            return {"ok": False, "data": None, "context": {}, "warnings": [], "artifacts": [],
                    "error": {"code": "WORKER_UNAVAILABLE", "message": str(exc), "details": {"execution_state": "unknown"}}}

    async def close(self):
        if self.process is None:
            return
        if self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 40)
            except TimeoutError:
                print("Zemax worker 未在关闭期限内退出，原生任务停止状态未确认。", file=sys.stderr, flush=True)
                self.process.terminate()
                await self.process.wait()
        if self.reader_task:
            await self.reader_task
        self.process = None
