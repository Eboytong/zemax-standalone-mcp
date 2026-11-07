import asyncio,json,sys
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from tests.support.paths import run_dir

@pytest.mark.zemax
def test_direct_and_polarized_rays_over_stdio():
    async def scenario():
        folder=run_dir("extended_rays");events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(folder)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    r=(await client.call_tool(name,args or {})).structured_content;events.append(dict(tool=name,arguments=args,response=r));assert r and r["ok"],r
                    return r["data"]
                async def complete(t):
                    for _ in range(2000):
                        if t["state"] in {"succeeded","failed","cancelled"}:break
                        await asyncio.sleep(.02);t=await call("get_task_status",dict(task_id=t["task_id"]))
                    r=await call("get_task_result",dict(task_id=t["task_id"]));assert t["state"]=="succeeded",r
                    return r
                await call("connect");await call("new_system");await call("insert_surfaces",dict(at=1))
                await call("update_surfaces",{"changes":[{"surface":1,"thickness":10,"semi_diameter":10,"replace_solves":True}]})
                for pol in (None,{"jx":1,"jy":0}):
                    for mode in ("Direct","Normalized"):
                        if mode=="Normalized"and pol is None:continue
                        ray=dict(x=.2,y=.3,z=0,l=0,m=0,n=1)if mode=="Direct"else dict(hx=0,hy=0,px=0,py=0)
                        result=await complete(await call("run_batch_ray_trace",{"request":{"input_mode":mode,"start_surface":1,"target_surface":2,"rays":[ray],"polarization":pol}}))
                        r=result["rows"][0]
                        assert r["error_code"]==0,r
                        assert r["position"]==pytest.approx([.2,.3,0]if mode=="Direct"else[0,0,0],rel=1e-7,abs=1e-8)
                        assert r["direction"]==pytest.approx([0,0,1],rel=1e-7,abs=1e-8)
                        assert r["intensity"]==pytest.approx(1,rel=1e-7,abs=1e-8)
                        if mode=="Normalized":assert r["vignette_code"]is None
                await call("disconnect")
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("Extended ray evidence:",folder,flush=True)
    asyncio.run(scenario())
