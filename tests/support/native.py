"""Serial stdio sessions and numerical evidence; importing creates no native instance."""
import asyncio,json,math,os,sys,time
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from .paths import fixture_dir,run_dir

class Evidence:
    def __init__(self,client,folder):self.client=client;self.folder=folder;self.calls=[];self.checks=[]
    async def call(self,name,args=None,okay=True):
        if os.environ.get('ZEMAX_TEST_TOOL_MODE') == 'compact':
            from zemax_mcp.disclosure import BOOTSTRAP, READ_ONLY
            if name not in BOOTSTRAP:
                args=dict(capability_id='tool:'+name,arguments=args or {})
                name='query_capability' if name in READ_ONLY else 'execute_capability'
        r=(await self.client.call_tool(name,args or {})).structured_content
        self.calls.append(dict(tool=name,arguments=args,response=r))
        if okay:assert r and r["ok"],r
        return r["data"]if r and r["ok"]else r
    async def finish(self,t,timeout_seconds=90):
        deadline=time.monotonic()+timeout_seconds
        while t["state"]not in {"succeeded","failed","cancelled"}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);t=await self.call("get_task_status",dict(task_id=t["task_id"]))
        r=await self.call("get_task_result",dict(task_id=t["task_id"]))
        assert t["state"]=="succeeded",r
        if r.get("artifacts"):
            files=[a["path"]for a in r["artifacts"]if a["kind"]=="json"and Path(a["path"]).stem==t["task_id"]]
            if files:return json.loads(Path(files[0]).read_text(encoding="utf-8"))
        return r
    def check(self,label,actual,expected,atol=1e-8,rtol=1e-7):
        passed=math.isfinite(actual)and abs(actual-expected)<=atol+rtol*abs(expected)
        self.checks.append(dict(label=label,actual=actual,expected=expected,atol=atol,rtol=rtol,passed=passed))
        assert passed,self.checks[-1]
    async def model(self):
        await self.call("new_system")
        await self.call("insert_surfaces",dict(at=1))
        await self.call("update_system_settings",dict(settings=dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)])))
        await self.call("update_surfaces",dict(changes=[dict(surface=1,thickness=0,semi_diameter=5,replace_solves=True)]))


def server_parameters(folder):
    environment={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder),"ZEMAX_STATE_DIR":str(Path(folder)/"state")}
    environment['ZEMAX_TOOL_MODE']=os.environ.get('ZEMAX_TEST_TOOL_MODE','full')
    # The MCP stdio client forwards only a fixed allowlist of variables to the server
    # process, so a CLR assembly-load switch set by the caller would be dropped.
    # Forward it verbatim only when the caller already set it; never default it here.
    switch=os.environ.get("COMPLUS_LoadFromRemoteSources")
    if switch is not None:
        environment["COMPLUS_LoadFromRemoteSources"]=switch
    installed=os.environ.get("ZEMAX_TEST_WHEEL_DIR")
    if not installed:
        return StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env=environment|{"PYTHONPATH":str(PROJECT_ROOT/"src")})
    root=Path(installed).resolve(strict=True)
    if not (root/"zemax_mcp"/"__init__.py").is_file():
        raise ValueError("ZEMAX_TEST_WHEEL_DIR must contain the independently installed zemax_mcp package")
    boot=("import sys;from pathlib import Path;sys.path.insert(0,"+repr(str(root))+");import zemax_mcp;"
          "assert Path(zemax_mcp.__file__).resolve().is_relative_to(Path("+repr(str(root))+"));"
          "from zemax_mcp.server import main;main()")
    return StdioServerParameters(command=sys.executable,args=["-I","-B","-c",boot],cwd=str(root),env=environment|{"PYTHONPATH":str(root)})


async def execute(kind,work,role="run"):
    """role="fixture" keeps the folder under outputs/fixtures/ for other tests; see tests/fixtures.json."""
    folder=(fixture_dir if role=="fixture" else run_dir)(kind)
    params=server_parameters(folder)
    e=None
    try:
        async with Client(params,read_timeout_seconds=180)as client:
            e=Evidence(client,folder);await e.call("connect")
            await work(e)
            await e.call("disconnect")
    finally:
        if e:
            (folder/"calls.json").write_text(json.dumps(e.calls,ensure_ascii=False,indent=2),encoding="utf-8")
            (folder/"checks.json").write_text(json.dumps(e.checks,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Condition evidence:",folder,flush=True)

