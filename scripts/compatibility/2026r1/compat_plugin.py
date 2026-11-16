"""OpticStudio 2026 R1 test environment and per-call execution records."""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
INSTALL = Path(r'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio')
current_test = None
poll_states = {}

def append(name, data):
    with (OUT/name).open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(data, ensure_ascii=False, default=str)+'\n')

def record(channel, name, args, response, seconds):
    if not isinstance(response, dict):
        response = {'ok': False, 'error': {'message': str(response)}}
    data = response.get('data') or {}
    context = response.get('context') or {}
    if name=='get_task_status' and isinstance(data,dict):
        key = (current_test,data.get('task_id'))
        state = data.get('state')
        previous = poll_states.get(key)
        if previous and previous[0]==state and time.monotonic()-previous[1]<10:
            return
        poll_states[key] = (state,time.monotonic())
    append('native-calls.jsonl', dict(test=current_test, channel=channel, tool=name,
        arguments=args, ok=response.get('ok'), error=response.get('error'),
        warnings=response.get('warnings'), seconds=seconds,
        task_error=data.get('error') if isinstance(data,dict) else None,
        version=context.get('opticstudio_version'), state=data.get('state') if isinstance(data,dict) else None,
        task_id=data.get('task_id') if isinstance(data,dict) else None))

def pytest_configure(config):
    import sys
    sys.path.insert(0, str(ROOT/'src'))
    os.environ['ZEMAX_INSTALL_DIR'] = str(INSTALL)
    os.environ['PYTHONUTF8'] = '1'
    os.environ['MPLCONFIGDIR'] = str(OUT/'matplotlib')
    os.environ['ZEMAX_STATE_DIR'] = str(OUT/'state')
    # The historical stdio tests exercise direct tools; mode-specific tests override this.
    os.environ['ZEMAX_TOOL_MODE'] = 'full'
    import zemax_mcp.config as cfg
    cfg.DEFAULT_INSTALL = INSTALL
    import mcp.client.stdio as stdio
    for key in ('ZEMAX_INSTALL_DIR','ZEMAX_STATE_DIR','MPLCONFIGDIR','PYTHONUTF8','ZEMAX_TOOL_MODE'):
        if key not in stdio.DEFAULT_INHERITED_ENV_VARS:
            stdio.DEFAULT_INHERITED_ENV_VARS.append(key)
    if config.getoption('collectonly'):
        return
    from mcp import Client
    original_call = Client.call_tool
    async def call_tool(self, name, arguments=None, *args, **kwargs):
        started = time.monotonic()
        result = await original_call(self, name, arguments, *args, **kwargs)
        raw = result.structured_content
        if raw is None:
            raw = {'ok':False,'error':result.model_dump(mode='json')}
        record('stdio',name,arguments or {},raw,time.monotonic()-started)
        return result
    Client.call_tool = call_tool
    from zemax_mcp.backend import Backend
    original_dispatch = Backend.dispatch
    def dispatch(self, command, arguments=None, *args, **kwargs):
        started = time.monotonic()
        result = original_dispatch(self, command, arguments, *args, **kwargs)
        record('direct',command,arguments or {},result,time.monotonic()-started)
        return result
    Backend.dispatch = dispatch

def pytest_runtest_setup(item):
    global current_test
    current_test = item.nodeid
    append('progress.jsonl',dict(event='started',test=current_test,time=time.time()))

def pytest_runtest_logreport(report):
    if report.when=='call' or report.failed or report.skipped:
        append('test-results.jsonl',dict(test=report.nodeid,phase=report.when,
            outcome=report.outcome,duration=report.duration,
            reason=str(report.longrepr) if report.failed or report.skipped else None,
            wasxfail=getattr(report,'wasxfail',None)))
        append('progress.jsonl',dict(event='finished',test=report.nodeid,
            outcome=report.outcome,time=time.time()))

def pytest_collection_finish(session):
    if session.config.getoption('collectonly'):
        (OUT/'collected-tests.json').write_text(json.dumps([item.nodeid for item in session.items],indent=2),encoding='utf-8')
