import asyncio
import json
import time
from pathlib import Path
import pytest
from mcp import Client
from zemax_mcp.analyses import ANALYSES
from tests.support.paths import run_dir
from tests.support.native import server_parameters
from tests.support.analysis_scenarios import SPECIALIZED, EXPECTED_LIMITATIONS, cooke_request

@pytest.mark.zemax
def test_analysis_families_over_stdio():
    async def scenario():
        folder=run_dir("analyses")
        events=[]; failures=[]; coefficients={}
        params=server_parameters(folder)
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    raw=await client.call_tool(name,args or {})
                    r=raw.structured_content
                    events.append(dict(tool=name,arguments=args,response=r,raw_response=raw.model_dump(mode='json') if r is None else None))
                    assert isinstance(r,dict),events[-1]
                    return r
                assert (await call("connect"))["ok"]
                try:
                    await analyses(call,failures,coefficients,folder)
                finally:
                    assert (await call("disconnect"))["ok"]
        finally:
            (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            (folder/"failures.json").write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding="utf-8")
            (folder/"coverage.json").write_text(json.dumps(dict(cooke_kinds=[k for k in ANALYSES if k not in SPECIALIZED],specialized_routes=SPECIALIZED,expected_limitations=EXPECTED_LIMITATIONS),ensure_ascii=False,indent=2),encoding="utf-8")
            print("Analysis evidence:",folder,flush=True)
        assert not failures,failures

    async def analyses(call,failures,coefficients,folder):
        assert (await call("open_lens",{"path":str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")}))["ok"]
        for kind in ANALYSES:
            if kind in SPECIALIZED:continue
            request=cooke_request(kind)
            r=await call("run_analysis",{"request":request})
            if r["ok"]:
                task=r["data"]
                deadline=time.monotonic()+180
                while task["state"] not in {"succeeded","failed","cancelled"}:
                    assert time.monotonic()<deadline,task
                    await asyncio.sleep(.05)
                    task=(await call("get_task_status",{"task_id":task["task_id"]}))["data"]
                r=await call("get_task_result",{"task_id":task["task_id"]})
                assert not task.get('cleanup_warnings'),task
                if 'close_attempted' in task:assert task['close_attempted'],task
                if kind in EXPECTED_LIMITATIONS:
                    assert task['state']=='failed' and task['error']['code']==EXPECTED_LIMITATIONS[kind],task
                    assert task['close_attempted'] and not task.get('cleanup_warnings'),task
                elif task["state"]!="succeeded": failures.append((kind,task))
                elif r["ok"]:
                    assert r["data"]["artifacts"]
                    if kind.startswith('universal_plot_'):
                        page=dict(series=0,count=2) if kind.endswith('1d') else dict(grid=0,width=2,height=2)
                        assert (await call('get_task_result',dict(task_id=task['task_id'],**page)))['ok']
                        assert (await call('export_analysis_image',dict(request=dict(task_id=task['task_id'],path=str(folder/(kind+'.png'))))))['ok']
                    if kind in {"zernike_standard","zernike_fringe","zernike_annular"}:
                        assert len(r["data"]["rows"])==request.get("maximum_terms",22),r
                        coefficients[kind]=r["data"]["rows"]
                    if kind in {"geometric_mtf","huygens_mtf"}:
                        full=json.loads(Path(next(a["path"] for a in r["data"]["artifacts"] if a["kind"]=="json")).read_text(encoding="utf-8"))
                        for s in full["series"]:
                            assert s["x"][0]==pytest.approx(0,abs=1e-8)
                            assert all(v==pytest.approx(1,abs=1e-7) for v in s["y"][0])
            else: failures.append((kind,r["error"]))
            print(kind,"confirmed native output limitation" if kind in EXPECTED_LIMITATIONS else "okay" if r["ok"] else r["error"],flush=True)
        for kind,rows in coefficients.items():
            ztype={"zernike_fringe":0,"zernike_standard":1,"zernike_annular":2}[kind]
            operands=[dict(type="ZERN",parameters={"2":i,"3":1,"4":2,"5":1,"6":ztype,"7":0,"8":0})for i in range(1,len(rows)+1)]
            assert (await call("update_merit_function",dict(mode="replace",operands=operands)))["ok"]
            assert (await call("evaluate_merit_function"))["ok"]
            reference=await call("get_merit_function",dict(count=50))
            assert reference["ok"],reference
            for row,operand in zip(rows,reference["data"]["operands"]):
                assert row["value"]==pytest.approx(operand["value"],rel=1e-7,abs=1e-8),(kind,row,operand)
    asyncio.run(scenario())
