"""Finite native compensation settings, saved trials and soft-bound auditing."""
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute

CASES=[(mode,width,5)for mode in ('None','ParaxialFocus','OptimizeAll_DLS','OptimizeAll_OD')for width in (.0001,.01)]
CASES += [(mode,.0001,cycles)for mode in ('OptimizeAll_DLS','OptimizeAll_OD')for cycles in (10,30)]


@pytest.mark.zemax
@pytest.mark.parametrize('mode,width,cycles',CASES)
def test_finite_compensation_saved_trials_native(mode,width,cycles):
    async def work(e):
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(lens)))
        nominal=(await e.call('get_surfaces',dict(start=6,count=1)))['surfaces'][0]['cells']['thickness']['value']
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[dict(type='SEED',param1=42),
            dict(type='TTHI',param1=1,param2=0,minimum=-.1,maximum=.1),
            dict(type='COMP',param1=6,param2=0,minimum=-width,maximum=width)])))
        result=await e.finish(await e.call('run_tolerance_analysis',dict(request=dict(mode='monte_carlo',samples=8,save_samples=8,
            compensation=mode,sampling=1,cycles=cycles,distribution='Uniform'))),timeout_seconds=600)
        paths=result['summary']['saved_samples'];assert len(paths)==8,result['summary']
        records=[];lower,upper=nominal-width,nominal+width
        for path in paths:
            await e.call('open_lens',dict(path=path))
            surfaces=(await e.call('get_surfaces',dict(start=1,count=6)))['surfaces']
            value=surfaces[-1]['cells']['thickness']['value'];assert math.isfinite(value)
            merit=await e.call('evaluate_merit_function')
            operands=merit['operands']['operands']
            constraints=[r for r in operands if r['type']in('CTLT','CTGT')]
            if mode.startswith('OptimizeAll'):
                assert any(r['type']=='CTLT'and abs(r['target']-upper)<1e-7 for r in constraints)
                assert any(r['type']=='CTGT'and abs(r['target']-lower)<1e-7 for r in constraints)
            records.append(dict(path=path,compensator_thickness_mm=value,lower_mm=lower,upper_mm=upper,
                distance_to_bound_mm=min(abs(value-lower),abs(value-upper)),outside_mm=max(0,lower-value,value-upper),
                constraint_operands=constraints,recomputed_merit=merit['merit_function'],
                native_trial_values=result['rows'][len(records)]['values'],
                criterion_scope='saved optimization merit and native tolerancing RMS criterion retained separately'))
        statistics=await e.call('summarize_tolerance_results',dict(request=dict(task_id=result['task']['task_id'],criterion_column=0,
            threshold=.01,unit='native RMS criterion; native text defines scale')))
        assert statistics['requested']==8,statistics
        (e.folder/'compensation-reference.json').write_text(json.dumps(dict(mode=mode,cycles=cycles,seed=42,
            nominal_mm=nominal,offset_range_mm=[-width,width],rows=records,statistics=statistics,
            verified_scope='native settings, saved-trial parameters, absolute soft-bound targets and requested-sample denominator',
            remaining='independent optical RMS criterion and deterministic seven-point stress matrix'),indent=2),encoding='utf-8')
    asyncio.run(execute(f'finite_comp_{mode}_{width}_{cycles}',work,role='fixture'))


@pytest.mark.zemax
@pytest.mark.parametrize('mode',['None','ParaxialFocus','OptimizeAll_DLS','OptimizeAll_OD'])
@pytest.mark.parametrize('width',[.0001,.01])
def test_finite_deterministic_compensation_stress_native(mode,width):
    async def work(e):
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        records=[]
        for delta in (0,-.01,.01,-.1,.1,-.5,.5):
            await e.call('open_lens',dict(path=str(lens)))
            baseline=(await e.call('get_surfaces',dict(start=1,count=6)))['surfaces']
            thickness=baseline[0]['cells']['thickness']['value']
            center=baseline[-1]['cells']['thickness']['value']
            await e.call('update_tolerances',dict(request=dict(mode='replace',operands=[
                dict(type='SEED',param1=42),
                dict(type='TTHI',param1=1,param2=0,minimum=delta,maximum=delta),
                dict(type='COMP',param1=6,param2=0,minimum=-width,maximum=width)])))
            result=await e.finish(await e.call('run_tolerance_analysis',dict(request=dict(mode='monte_carlo',
                samples=1,save_samples=1,compensation=mode,sampling=1,cycles=5,distribution='Uniform'))),timeout_seconds=600)
            paths=result['summary']['saved_samples']
            assert len(paths)==1,result['summary']
            await e.call('open_lens',dict(path=paths[0]))
            actual=(await e.call('get_surfaces',dict(start=1,count=6)))['surfaces']
            e.check('deterministic TTHI trial mm',actual[0]['cells']['thickness']['value'],thickness+delta)
            value=actual[-1]['cells']['thickness']['value'];lo,hi=center-width,center+width
            merit=await e.call('evaluate_merit_function')
            constraints=[r for r in merit['operands']['operands']if r['type']in('CTLT','CTGT')]
            if mode.startswith('OptimizeAll'):
                assert any(r['type']=='CTLT'and abs(r['target']-hi)<1e-7 for r in constraints)
                assert any(r['type']=='CTGT'and abs(r['target']-lo)<1e-7 for r in constraints)
            records.append(dict(perturbation_mm=delta,model=paths[0],compensator_mm=value,
                lower_mm=lo,upper_mm=hi,distance_to_bound_mm=min(abs(value-lo),abs(value-hi)),
                outside_mm=max(0,lo-value,value-hi),native_trial=result['rows'],
                constraints=constraints,merit=merit['merit_function']))
        (e.folder/'deterministic-stress-reference.json').write_text(json.dumps(dict(mode=mode,
            half_range_mm=width,cycles=5,rows=records,
            verified_scope='explicit TTHI, saved-trial readback and native soft compensation targets',
            remaining='independent optical RMS criterion'),indent=2),encoding='utf-8')
    asyncio.run(execute(f'finite_stress_{mode}_{width}',work,role='fixture'))
