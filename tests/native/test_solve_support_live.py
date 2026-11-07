"""Individually selectable, serial stdio acceptance for 49 solves and 10 native controls."""
import asyncio,json,math,os,subprocess,sys,threading
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.native import Evidence
from tests.support.solve_fixtures import CASES,spec,SOLVES
from tests.support.paths import fixture_dir

class SerialClient:
    def __init__(self,folder):
        self.folder=folder;self.ready=threading.Event();self.error=None
        self.thread=threading.Thread(target=lambda:asyncio.run(self.lifetime()),daemon=True)
        self.thread.start()
        if not self.ready.wait(60):raise RuntimeError("stdio startup timed out")
        if self.error:raise RuntimeError(self.error)
    async def lifetime(self):
        try:
            self.loop=asyncio.get_running_loop();self.stop=asyncio.Event()
            p=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(self.folder/"mcp")})
            async with Client(p,read_timeout_seconds=120)as self.client:
                r=(await self.client.call_tool("connect",{})).structured_content
                assert r["ok"],r
                self.ready.set();await self.stop.wait()
                r=(await self.client.call_tool("disconnect",{})).structured_content
                assert r["ok"],r
        except BaseException as exc:self.error=repr(exc);self.ready.set()
    def run(self,coro):return asyncio.run_coroutine_threadsafe(coro,self.loop).result(timeout=180)
    def close(self):
        self.loop.call_soon_threadsafe(self.stop.set);self.thread.join(60)
        assert not self.thread.is_alive()and self.error is None,self.error

@pytest.fixture(scope="module")
def session():
    folder=fixture_dir("solve_acceptance")
    # Direct native control closes before the MCP service creates its instance.
    with (folder/"direct-native.log").open("w",encoding="utf-8")as log:
        result=subprocess.run([sys.executable,"-B",str(PROJECT_ROOT/"tests/support/solve_fixtures.py"),str(folder)],stdout=log,stderr=subprocess.STDOUT,timeout=180)
    assert result.returncode==0
    rows=json.loads((folder/"direct-native.json").read_text(encoding="utf-8"))
    client=SerialClient(folder)
    try:yield client,{r["id"]:r for r in rows}
    finally:
        client.close()
        records=[json.loads(p.read_text(encoding="utf-8"))for p in folder.glob("*/record.json")]
        (folder/"matrix.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Solve acceptance:",folder,flush=True)

async def exercise(e,row):
    case=row;folder=e.folder;target=row["fixture"]["target"];cell=case["cell"]
    async def load():await e.call("open_lens",dict(path=row["fixture"]["path"]))
    async def read():return(await e.call("get_surfaces",dict(start=target,count=1)))["surfaces"][0]["cells"][cell]
    async def trace(ray_type="Real",hy=0,px=0,py=0,target_surface=None):
        r=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(ray_type=ray_type,target_surface=target_surface or target+1,rays=[dict(hy=hy,px=px,py=py,wavelength=2)]))))
        ray=r["rows"][0];assert ray["error_code"]==0,ray
        return ray
    async def verify(s):
        mode=case["mode"]
        if mode=="f_number":
            ray=await trace("Paraxial",py=1,target_surface=target)
            e.check("F-number Y paraxial slope",ray["direction"][1]/ray["direction"][2],-1/(2*s["f_number"]))
            if case["surface_type"]in ("Toroidal","Biconic"):
                other=await trace("Paraxial",px=1,target_surface=target)
                e.checks[-1]["x_direction"]=other["direction"]
                e.checks[-1]["y_direction"]=ray["direction"]
        elif mode=="marginal_ray_height":
            zone=s["pupil_zone"];r=await trace("Paraxial"if zone==0 else"Real",py=zone or 1)
            e.check("marginal height mm",r["position"][1],s["height"])
        elif mode=="chief_ray_height":
            r=await trace("Paraxial",hy=1);e.check("chief height mm",r["position"][1],s["height"])
        elif mode=="edge_thickness":
            a=(await e.call("get_surface_geometry",dict(request=dict(surface=target,points=[dict(x=0,y=1)]))))["rows"][0]["sag"]
            b=(await e.call("get_surface_geometry",dict(request=dict(surface=target+1,points=[dict(x=0,y=1)]))))["rows"][0]["sag"]
            e.check("edge thickness mm",(await read())["value"]+b-a,s["thickness"])
        elif mode=="position":
            data=(await e.call("get_surfaces",dict(start=1,count=7)))["surfaces"]
            src=s["source_surface"];lo,hi=(src,target+1)if src<=target else(target,src)
            e.check("position interval mm",sum(r["cells"]["thickness"]["value"]for r in data if lo<=r["surface"]<hi),s["length"])
        elif mode=="pickup_chief_ray":
            ray=await trace(hy=.7,target_surface=target);i=int(cell.split("_")[1])
            value=ray["position"][i-1]if i<3 else ray["direction"][1 if i==3 else 0]
            e.check("chief ray local target",value,0)
    assert "preparation_error"not in row,row
    await load()
    s=spec(case)
    changes=[dict(surface=target,replace_solves=True,solves={cell:s})]
    later=1 if target==2 else 2
    if case.get("audit"):changes.append(dict(surface=later,comment="must_not_apply"))
    response=await e.call("update_surfaces",dict(changes=changes),okay=False)
    if isinstance(response,dict)and response.get("ok")is False:
        assert not row["direct_native"]["adopted"],(response,row["direct_native"])
        assert response["error"]["details"]["partial_changes_possible"]
        assert Path(response["context"]["checkpoint"]).is_file()
        if case.get("audit"):
            later_row=(await e.call("get_surfaces",dict(start=later,count=1)))["surfaces"][0]
            assert later_row["comment"]!="must_not_apply"
            assert response["error"]["details"]["completed_surfaces"]==[]
            assert response["error"]["details"]["cause"]["code"]=="SOLVE_UPDATE_FAILED"
            await load()
            variable=cell!="semi_diameter"
            r=await e.call("set_variables",dict(variables=[dict(surface=target,cell=cell,variable=variable,replace_solve=True),
                dict(surface=later,cell="thickness",variable=True)]),okay=False)
            assert not r["ok"]and r["error"]["code"]=="SOLVE_UPDATE_FAILED",r
            assert r["error"]["details"]["failed_index"]==0
            assert r["error"]["details"]["completed_count"]==0
            assert r["error"]["details"]["partial_changes_possible"]
            after=(await e.call("get_surfaces",dict(start=later,count=1)))["surfaces"][0]
            assert after["cells"]["thickness"]["solve"]["type"]=="Fixed"
        return "native_rejected"
    assert row["direct_native"]["adopted"],row["direct_native"]
    assert not case.get("audit"),"Previously ignored case now adopts; add numerical reference before closing."
    for variant in range(3 if case["mode"]in ("marginal_ray_height","position")else 1):
        await load();s=spec(case,variant)
        await e.call("update_surfaces",dict(changes=[dict(surface=target,replace_solves=True,solves={cell:s})]))
        before=await read();assert before["solve"]["type"]==SOLVES[case["mode"]]
        for key,value in s.items():
            if key!="mode":assert before["solve"][key]==value,(key,before,s)
        rejected=await e.call("update_surfaces",dict(changes=[dict(surface=target,solves={cell:dict(mode="fixed")})]),okay=False)
        assert not rejected["ok"]and rejected["error"]["code"]=="SOLVE_PROTECTED",rejected
        assert not rejected["error"]["details"]["partial_changes_possible"]
        await verify(s)
        path=folder/f"solved_{variant}.zos"
        await e.call("save_lens_as",dict(path=str(path)))
        await e.call("open_lens",dict(path=str(path)))
        after=await read();assert before["solve"]==after["solve"],(before,after)
        await verify(s)
    return "numeric_passed"

@pytest.mark.zemax
@pytest.mark.parametrize("case",CASES,ids=lambda r:r["id"])
def test_solve_case(session,case):
    client,rows=session;row=rows[case["id"]];folder=client.folder/case["id"]
    folder.mkdir(exist_ok=True);e=Evidence(client.client,folder);record=dict(id=case["id"],surface_type=case["surface_type"],cell=case["cell"],mode=case["mode"],direct_control=row,status="failed")
    try:
        assert "preparation_error"not in row,row
        record["status"]=client.run(exercise(e,row))
    except BaseException as exc:
        record["error"]=str(exc);raise
    finally:
        record["checks"]=e.checks
        (folder/"calls.json").write_text(json.dumps(e.calls,ensure_ascii=False,indent=2),encoding="utf-8")
        (folder/"record.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")

