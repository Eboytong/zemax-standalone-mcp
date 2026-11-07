import asyncio
import json
from pathlib import Path
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_histogram_tails_reload_and_failed_sample_distribution():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='SEED',param1=42),dict(type='TTHI',param1=1,param2=2,minimum=-.01,maximum=.01)])))
        data=await e.finish(await e.call('run_tolerance_analysis',dict(request=dict(mode='monte_carlo',samples=16,compensation='None',sampling=1,distribution='Uniform'))))
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        request=dict(kind='tolerance_histogram',operand=1,tolerance_file=Path(data['summary']['tolerance_data']).name,minimum=-.002,maximum=.002,bins=5)
        result=await e.finish(await e.call('run_analysis',dict(request=request)))
        (e.folder/'tails.json').write_text(json.dumps(dict(data=data,result=result),ensure_ascii=False,indent=2),encoding='utf-8')
        values=[r['values'][1]for r in data['rows']]
        e.check('histogram underflow',result['distribution']['underflow'],sum(v<request['minimum']for v in values))
        e.check('histogram overflow',result['distribution']['overflow'],sum(v>request['maximum']for v in values))
        assert result['distribution']['sample_count']==16
        ordered=sorted(values)
        mixed={**request,'minimum':(ordered[3]+ordered[4])/2,'maximum':(ordered[11]+ordered[12])/2}
        middle=await e.finish(await e.call('run_analysis',dict(request=mixed)))
        e.check('mixed underflow',middle['distribution']['underflow'],4)
        e.check('mixed overflow',middle['distribution']['overflow'],4)
        e.check('mixed in-range',middle['distribution']['in_range_count'],8)
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='SEED',param1=42),dict(type='TTHI',param1=1,param2=2,minimum=-200,maximum=200)])))
        failed=await e.finish(await e.call('run_tolerance_analysis',dict(request=dict(mode='monte_carlo',samples=8,save_samples=8,compensation='None',sampling=1,cycles=1,distribution='Uniform'))))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces')
        assert sum(row['state']=='failed'for row in failed['rows'])==5
        records=[]
        for kind in ['tolerance_yield','tolerance_histogram']:
            q=dict(kind=kind,operand=0,tolerance_file=Path(failed['summary']['tolerance_data']).name)
            if kind=='tolerance_histogram':q.update(minimum=0,maximum=1,bins=5)
            r=await e.finish(await e.call('run_analysis',dict(request=q)))
            records.append(r)
            assert r['distribution']['sample_count']==8
            if kind=='tolerance_yield':
                for row in r['series'][0]['y'][1:-1]:e.check('failure yield denominator8',row[0],100*3/8,atol=1e-8,rtol=1e-7)
            else:
                assert r['distribution']['overflow']==8
            status=await e.call('get_task_status',dict(task_id=r['task']['task_id']))
            assert status['close_attempted'] and status['state']=='succeeded'
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
        (e.folder/'failed-distribution.json').write_text(json.dumps(dict(data=failed,results=records),ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('tolerance_edges085',work))
