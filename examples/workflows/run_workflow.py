"""Run an explicit local example through the real stdio MCP client."""
import argparse,asyncio,json,sys,time,uuid
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT

async def run(name,lens,timeout):
    workflows=json.loads(PROJECT_ROOT/"examples/requests/extended_workflows.json".read_text(encoding="utf-8"))
    output=PROJECT_ROOT/".local"/"runs"/("workflow_"+name+"_"+uuid.uuid4().hex[:10]);output.mkdir(parents=True)
    events=[];tasks={}
    def resolve(value):
        if isinstance(value,dict):return {k:resolve(v)for k,v in value.items()}
        if isinstance(value,list):return [resolve(v)for v in value]
        if isinstance(value,str):
            if value.startswith("$TASK:"):return tasks[value[6:]]
            return value.replace("$OUTPUT",str(output)).replace("$LENS",str(lens))
        return value
    params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(output)})
    try:
        async with Client(params,read_timeout_seconds=120)as client:
            async def call(tool,arguments=None):
                response=(await client.call_tool(tool,arguments or {})).structured_content
                events.append(dict(tool=tool,arguments=arguments,response=response))
                if not response or not response["ok"]:raise RuntimeError(str(response))
                return response["data"]
            try:
                for step in workflows[name]:
                    data=await call(step["tool"],resolve(step.get("arguments",{})))
                    if "task_id"in data and "state"in data:
                        task_id=data["task_id"];deadline=time.monotonic()+timeout
                        if step.get("id"):tasks[step["id"]]=task_id
                        while data["state"]not in {"succeeded","failed","cancelled"}:
                            if time.monotonic()>deadline:
                                await call("cancel_task",dict(task_id=task_id))
                                raise TimeoutError("已请求取消；详细状态见调用记录。")
                            await asyncio.sleep(.1);data=await call("get_task_status",dict(task_id=task_id))
                        result=await call("get_task_result",dict(task_id=task_id))
                        if data["state"]!="succeeded":raise RuntimeError(str(result))
                    print(step["tool"],"完成",flush=True)
            finally:
                # Preserve the original failure while recording cleanup state.
                original_error=sys.exc_info()[0]
                try:
                    status=await call("get_status")
                    active=status.get("active_task")
                    if active:
                        active=await call("cancel_task",dict(task_id=active["task_id"]))
                        deadline=time.monotonic()+60
                        while active["state"]not in {"succeeded","failed","cancelled"}and time.monotonic()<deadline:
                            await asyncio.sleep(.1);active=await call("get_task_status",dict(task_id=active["task_id"]))
                        if active["state"]not in {"succeeded","failed","cancelled"}:raise RuntimeError("取消尚未确认，服务关闭时继续执行资源清理。")
                    await call("disconnect")
                except Exception as exc:
                    events.append(dict(cleanup_error=str(exc)))
                    if original_error is None:raise
    finally:
        (output/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
        print("结果目录：",output,flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow",choices=list(json.loads(PROJECT_ROOT/"examples/requests/extended_workflows.json".read_text(encoding="utf-8"))))
    parser.add_argument("--lens",type=Path,default=Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
    parser.add_argument("--timeout",type=float,default=300)
    args=parser.parse_args()
    if args.timeout<=0:parser.error("timeout 必须为正数。")
    asyncio.run(run(args.workflow,args.lens.resolve(),args.timeout))
