import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("kind,operand",[("tolerance_yield",0),("tolerance_yield",1),("tolerance_histogram",0),("tolerance_histogram",1)])
def test_native_tolerance_yield_and_histogram(kind,operand):
    async def work(e):
        await e.call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        await e.call("update_tolerances", {"request": {"mode": "replace", "operands": [
            {"type": "TTHI", "param1": 1, "param2": 0, "minimum": -0.01, "maximum": 0.01}
        ]}})
        data=await e.finish(await e.call("run_tolerance_analysis", {"request": {"mode": "monte_carlo", "samples": 10, "compensation": "None"}}),timeout_seconds=180)
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        request=dict(kind=kind,operand=operand)
        if kind=="tolerance_histogram":request.update(minimum=-.02,maximum=.02,bins=20)
        request["tolerance_file"]=Path(data["summary"]["tolerance_data"]).name
        task = await e.call("run_analysis", {"request": request})
        result = await e.finish(task)
        assert data["summary"]["tolerance_data_file_exists"]
        assert result.get("native_header") or result.get("series") or result.get("grids"), result
        curve=result['series'][0]
        values=[row['values'][operand]for row in data['rows']]
        if kind=='tolerance_yield':
            for x,y in zip(curve['x'][1:-1],curve['y'][1:-1]):
                e.check('empirical cumulative percent',y[0],100*sum(v<=x for v in values)/len(values),atol=1e-8,rtol=1e-7)
        else:
            width=(request['maximum']-request['minimum'])/request['bins']
            counts=[0]*request['bins']
            for v in values:
                if request['minimum']<=v<request['maximum']:counts[int((v-request['minimum'])/width)]+=1
            for i,(x,y)in enumerate(zip(curve['x'],curve['y'])):
                e.check('histogram bin center',x,request['minimum']+(i+.5)*width,atol=1e-10,rtol=1e-10)
                e.check('histogram count',y[0],counts[i],atol=1e-8,rtol=1e-7)
        status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert status['state']=='succeeded' and status['close_attempted']
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=2,count=4))
        assert page['series'][0]['y']==curve['y'][2:6]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'curve.png'))))
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
        rejected=await e.call('run_analysis',dict(request={**request,'operand':999}),okay=False)
        assert rejected['error']['code']=='INDEX_OUT_OF_RANGE'
        await e.finish(await e.call('run_analysis',dict(request=request)))
        e.checks.append({"analysis": kind, "task_state": "succeeded",
                         "native_settings": task.get("settings"),
                         "result_shapes": {"series": len(result.get("series", [])),
                                           "grids": len(result.get("grids", [])),
                                           "artifacts": len(result.get("artifacts", []))}})

    asyncio.run(execute("tolerance-special-analyses", work))
