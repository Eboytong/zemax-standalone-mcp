"""Private JSON-lines process. Only this process owns native API objects."""

import json
import queue
import sys
import threading

from .backend import Backend
from .config import Config
from .history import RequestJournal
from .errors import ZemaxError


def handle_frame(backend, journal, frame):
    command = frame.get('command', '')
    arguments = frame.get('arguments', {})
    supplied = frame.get('request_id')
    request_id = supplied if supplied is not None else frame.get('id')
    record = None
    journal_error = None
    try:
        if supplied is not None:
            record, replay = journal.reserve(request_id, command, arguments)
            if replay is not None:
                return replay
        else:
            record = journal.begin(request_id, command, arguments)
    except Exception as exc:
        if supplied is not None:
            error = exc.as_dict() if isinstance(exc, ZemaxError) else dict(
                code='REQUEST_RECEIPT_FAILED', message='请求回执未确认，操作未派发。', details={'reason': str(exc)})
            return dict(ok=False, data=None, context={'request_id': request_id}, error=error, warnings=[], artifacts=[])
        journal_error = str(exc)
    response = backend.dispatch(command, arguments, request_id=request_id)
    response.setdefault('context', {})['request_id'] = request_id
    try:
        journal.finish(record, response)
    except Exception as exc:
        journal_error = str(exc)
    if journal_error:
        response.setdefault('warnings', []).append('请求回执写入失败：' + journal_error)
    return response


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    inbox = queue.Queue()
    config = Config.from_env()
    backend = Backend(config)
    journal = RequestJournal(config.output_dir, backend.worker_instance_id)

    def read_commands():
        try:
            for line in sys.stdin:
                try:
                    frame = json.loads(line)
                    if not isinstance(frame, dict):
                        raise ValueError("A request must be an object")
                    inbox.put(frame)
                except (ValueError, TypeError) as exc:
                    print(f"Invalid private request: {exc}", file=sys.stderr, flush=True)
        finally:
            inbox.put(None)

    threading.Thread(target=read_commands, daemon=True).start()
    try:
        while True:
            backend.tick()
            try:
                frame = inbox.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is None:
                break
            response = handle_frame(backend, journal, frame)
            sys.stdout.write("@zemax-ipc " + json.dumps({"id": frame.get("id"), "response": response}, ensure_ascii=False, allow_nan=False) + "\n")
    except BrokenPipeError:
        pass
    finally:
        backend.shutdown()


if __name__ == "__main__":
    main()
