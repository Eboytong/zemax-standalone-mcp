"""Finite process-tolerance allocations evaluated by native tolerancing."""
import math
import time
from statistics import NormalDist
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, FiniteFloat, PositiveIndex
from .errors import ZemaxError

Positive = Annotated[FiniteFloat, Field(gt=0)]


class ProcessTolerance(Request):
    operand: PositiveIndex
    name: Annotated[str, Field(min_length=1, max_length=80)]
    unit: Annotated[str, Field(min_length=1, max_length=40)]
    minimum_half_width: Positive
    maximum_half_width: Positive
    reference_half_width: Positive
    fixed_cost: Annotated[FiniteFloat, Field(ge=0)] = 0
    variable_cost: Positive
    exponent: Annotated[FiniteFloat, Field(gt=0, le=10)] = 1

    @model_validator(mode='after')
    def bounds(self):
        if self.minimum_half_width > self.maximum_half_width:
            raise ValueError('工艺公差下界须小于或等于上界。')
        return self


class ToleranceBudget(Request):
    kind: Literal['tolerance_budget']
    processes: Annotated[list[ProcessTolerance], Field(min_length=1, max_length=8)]
    allocations: Annotated[list[list[Positive]], Field(min_length=2, max_length=50)]
    currency: Annotated[str, Field(min_length=1, max_length=20)]
    costing_unit: Annotated[str, Field(min_length=1, max_length=80)]
    criterion: str = 'RMSSpotRadius'
    criterion_unit: Annotated[str, Field(min_length=1, max_length=40)]
    threshold: FiniteFloat
    pass_when: Literal['less_equal','greater_equal'] = 'less_equal'
    compensation: str = 'None'
    target_yield: Annotated[FiniteFloat, Field(gt=0, lt=1)]
    confidence: Annotated[FiniteFloat, Field(gt=.5, lt=1)] = .95
    screening_samples: Annotated[int, Field(strict=True, ge=5, le=10000)] = 100
    validation_samples: Annotated[int, Field(strict=True, ge=5, le=10000)] = 200
    save_validation_samples: Annotated[int, Field(strict=True, ge=0, le=100)] = 0
    sampling: Annotated[int, Field(strict=True, ge=1, le=10)] = 3
    cycles: Annotated[int, Field(strict=True, ge=1, le=100)] = 2
    distribution: Literal['Normal','Uniform','Parabolic'] = 'Uniform'
    seed: Annotated[int, Field(strict=True, ge=1, le=2147483646)] = 42
    validation_seed: Annotated[int, Field(strict=True, ge=1, le=2147483646)] = 314159
    budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=3600)] = 180

    @model_validator(mode='after')
    def contract(self):
        if len({p.operand for p in self.processes}) != len(self.processes) or len({p.name for p in self.processes}) != len(self.processes):
            raise ValueError('工艺公差行与名称须唯一。')
        if self.seed == self.validation_seed:
            raise ValueError('独立验证须使用不同SEED。')
        if self.save_validation_samples > self.validation_samples:
            raise ValueError('保存样本数不得超过验证样本数。')
        if len({tuple(a) for a in self.allocations}) != len(self.allocations):
            raise ValueError('公差候选不得重复。')
        for a in self.allocations:
            if len(a) != len(self.processes):
                raise ValueError('每个候选宽度须与工艺数量相同。')
            for width,p in zip(a,self.processes):
                if not p.minimum_half_width <= width <= p.maximum_half_width:
                    raise ValueError('候选宽度超出工艺边界。')
            allocation_cost(a,self.processes)
        return self


def allocation_cost(widths, processes):
    try:
        parts=[p.fixed_cost+p.variable_cost*(p.reference_half_width/w)**p.exponent for w,p in zip(widths,processes)]
        total=math.fsum(parts)
        if not math.isfinite(total):raise ValueError('成本计算超出有限范围。')
    except (OverflowError, ZeroDivisionError):
        raise ValueError('成本计算超出有限范围。')
    return dict(total=total,components=[dict(name=p.name,cost=v,half_width=w,unit=p.unit) for p,w,v in zip(processes,widths,parts)])


def wilson(passed,n,confidence):
    if type(n) is not int or n<1 or type(passed) is not int or not 0<=passed<=n:
        raise ValueError('需要有效试验计数。')
    z=NormalDist().inv_cdf(.5+confidence/2)
    p=passed/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(lower=max(0.,center-radius),upper=min(1.,center+radius),confidence=confidence,
                method='two-sided Wilson score interval',passed=passed,samples=n,estimate=p)


def run_tolerance_budget(b,q):
    from .tolerance_models import ToleranceRange,TolerancePatch,ToleranceAnalysis,ToleranceSummary
    b._require_sequential(focused=True);b._require_work()
    def flow(task):
        deadline=time.monotonic()+q.budget_seconds
        source,work=b.source_path,b.work_path
        snapshot=b._checkpoint('tolerance_budget_baseline')
        task['baseline']=dict(path=snapshot,context=b.context())
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],
            computation_method='native sensitivity then finite allocation Monte Carlo and independent best-candidate validation',
            cost_definition='sum(fixed_cost + variable_cost * (reference_half_width / half_width) ** exponent)',
            actual_settings=q.model_dump(),currency=q.currency,costing_unit=q.costing_unit,
            criterion_unit=q.criterion_unit,independent_validation=None)
        def boundary():
            b._cancel_boundary(task)
            if time.monotonic()>=deadline:raise ZemaxError('BUDGET_EXCEEDED','公差成本预算时间已用完。')
        def native(spec):
            from .detectors import check_setting_value
            boundary()
            spec=spec.model_copy(update=dict(budget_seconds=max(.001,deadline-time.monotonic())))
            result=yield from b._child_job(task,b.run_tolerance_analysis,spec)
            boundary()
            actual=result['summary']['actual']
            expected=dict(SetupMode='Sensitivity' if spec.mode=='sensitivity' else 'SkipSensitivity',
                Criterion=str(b.native.enum(b.native.api.Tools.Tolerancing.Criterions,q.criterion)),
                CriterionComp=str(b.native.enum(b.native.api.Tools.Tolerancing.CriterionComps,q.compensation)),MonteCarloStatistic=q.distribution,
                CriterionSampling=q.sampling,CriterionCycle=q.cycles,
                NumberOfRuns=spec.samples if spec.mode=='monte_carlo' else 0,
                NumberToSave=spec.save_samples if spec.mode=='monte_carlo' else 0)
            for name,value in expected.items():check_setting_value(name,value,actual.get(name))
            return result
        try:
            original=[];start=1
            while start is not None:
                page=b.get_tolerances(ToleranceRange(start=start,count=1000));original.extend(page['rows']);start=page['next_start']
            if max(p.operand for p in q.processes)>len(original):
                raise ZemaxError('INDEX_OUT_OF_RANGE','工艺公差行越界。')
            if any(r['type']=='STAT' and not r['ignore'] for r in original):
                raise ZemaxError('UNSUPPORTED_DISTRIBUTION_SCOPE','成本分配采用统一分布；请移除活动STAT行。')
            for p in q.processes:
                r=original[p.operand-1]
                if not r['type'].startswith('T') or r['ignore'] or r['minimum'] is None or r['maximum'] is None:
                    raise ZemaxError('INVALID_PROCESS_OPERAND','工艺行须是活动的双界限原生公差。',operand=p.operand,actual=r)
            task['payload']['baseline_tolerances']=original
            def apply(widths,seed):
                operands=[dict(type='SEED',param1=seed)]
                mapping={p.operand:w for p,w in zip(q.processes,widths)}
                identities=[]
                for r in original:
                    if r['type']=='SEED':continue
                    row=dict(type=r['type'],comment=r['comment'],ignore=r['ignore'],inverse_protected=r['inverse_protected'])
                    row.update({f'param{k}':v for k,v in r['parameters'].items()})
                    for name in ['minimum','maximum']:
                        if r[name] is not None:row[name]=r[name]
                    if r['operand'] in mapping:
                        row.update(minimum=-mapping[r['operand']],maximum=mapping[r['operand']])
                        identities.append(dict(original_operand=r['operand'],native_operand=len(operands)+1,type=r['type'],half_width=mapping[r['operand']]))
                    operands.append(row)
                actual=b.update_tolerances(TolerancePatch(mode='replace',operands=operands))
                return dict(identities=identities,actual=actual)
            def spec(mode,samples=5,save=0):
                return ToleranceAnalysis(mode=mode,criterion=q.criterion,compensation=q.compensation,sampling=q.sampling,
                    cycles=q.cycles,samples=samples,save_samples=save,distribution=q.distribution)
            def statistics(result):
                columns=result['summary']['columns']
                criteria=[c['column'] for c in columns if not c['is_operand']]
                if not criteria:raise ZemaxError('INVALID_RESULT_DATA','原生公差结果缺少准则列。')
                stat=b.summarize_tolerance_results(ToleranceSummary(task_id=result['task']['task_id'],criterion_column=criteria[0],
                    threshold=q.threshold,pass_when=q.pass_when,unit=q.criterion_unit))
                if stat['nonfinite_indices'] or stat['missing']:
                    raise ZemaxError('INCOMPLETE_TOLERANCE_RESULT','Monte Carlo准则缺失或非有限。',statistics=stat)
                interval=wilson(stat['passed'],stat['requested'],q.confidence)
                return dict(statistics=stat,interval=interval,feasible=interval['lower']>=q.target_yield)
            boundary()
            prescreen_widths=[p.minimum_half_width for p in q.processes]
            actual=apply(prescreen_widths,q.seed)
            sensitivity=yield from native(spec('sensitivity'))
            task['payload']['sensitivity']=dict(task_id=sensitivity['task']['task_id'],actual_tolerances=actual,
                results=sensitivity['summary']['sensitivity'],role='native prescreen at process minimum half-widths; all supplied allocations retained for nonlinear comparison')
            for index,widths in enumerate(q.allocations):
                boundary()
                actual=apply(widths,q.seed)
                result=yield from native(spec('monte_carlo',q.screening_samples))
                stat=statistics(result)
                row=dict(index=index,state='succeeded',half_widths=widths,cost=allocation_cost(widths,q.processes),
                    task_id=result['task']['task_id'],actual_tolerances=actual,**stat)
                task['rows'].append(row)
                task['progress']=int(85*(index+1)/len(q.allocations));yield
            feasible=sorted([r for r in task['rows'] if r['feasible']],key=lambda r:(r['cost']['total'],r['index']))
            if feasible:
                best=feasible[0]
                boundary();actual=apply(best['half_widths'],q.validation_seed)
                result=yield from native(spec('monte_carlo',q.validation_samples,q.save_validation_samples))
                validation=dict(candidate_index=best['index'],task_id=result['task']['task_id'],seed=q.validation_seed,
                    actual_tolerances=actual,saved_samples=result['summary']['saved_samples'],**statistics(result))
                task['payload']['independent_validation']=validation
                if validation['feasible']:
                    path=b.directory/(task['task_id']+'_budget.zos')
                    b.system.SaveAs(str(path));b.system.SaveAs(str(work))
                    if not path.is_file():raise ZemaxError('SAVE_FAILED','公差预算模型未生成。')
                    best['path']=str(path)
                    task['payload']['artifacts']=[dict(kind='recommended_model',path=str(path))]
            task['summary']=dict(candidate_count=len(task['rows']),screening_feasible=[r['index'] for r in feasible],
                selected_index=feasible[0]['index'] if feasible else None,
                recommended_index=feasible[0]['index'] if feasible and task['payload']['independent_validation']['feasible'] else None,
                comparison_scope='minimum cost among supplied allocations passing screening; recommendation also requires independent Wilson lower bound',
                target_yield=q.target_yield,confidence=q.confidence)
        finally:
            b._restore_model(task,snapshot,source,work)
            task.setdefault('summary',{}).update(baseline_restored=task.get('restoration',{}).get('restored',False),
                budget_seconds=q.budget_seconds,processed_candidates=len(task['rows']))
            task['payload']['series']=[dict(series=0,description='Tolerance allocation cost',x_label='candidate',x_unit='index',y_unit=q.currency+'/'+q.costing_unit,
                labels=['cost'],x=[r['index'] for r in task['rows']],y=[[r['cost']['total']] for r in task['rows']])]
    return b._composite(q.kind,q.model_dump(),flow)
