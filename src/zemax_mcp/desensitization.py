"""Native manufacturing-yield optimization with fixed-tolerance comparisons."""
import math
import time
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .errors import ZemaxError
from .glass_trials import GlassVariable
from .merit_program import MeritProgram, build, native_rows
from .schema import Request, FiniteFloat
from .tolerance_budget import wilson


class DesignDesensitize(Request):
    kind: Literal['design_desensitize']
    variables: Annotated[list[GlassVariable], Field(min_length=1, max_length=50)]
    merit: MeritProgram
    criterion: str = 'RMSSpotRadius'
    criterion_unit: str = 'lens units'
    compensation: str = 'None'
    threshold: Annotated[FiniteFloat, Field(gt=0)]
    maximum_nominal: Annotated[FiniteFloat, Field(ge=0)]
    minimum_sensitivity_reduction: Annotated[FiniteFloat, Field(ge=0, lt=1)] = .1
    screening_samples: Annotated[int, Field(strict=True, ge=5, le=10000)] = 64
    validation_samples: Annotated[int, Field(strict=True, ge=5, le=10000)] = 256
    seed: Annotated[int, Field(strict=True, ge=1, le=2147483646)] = 42
    validation_seed: Annotated[int, Field(strict=True, ge=1, le=2147483646)] = 314159
    distribution: Literal['Uniform', 'Normal', 'Parabolic'] = 'Uniform'
    sampling: Annotated[int, Field(strict=True, ge=1, le=10)] = 3
    cycles: Literal['Fixed_1_Cycle','Fixed_5_Cycles','Fixed_10_Cycles','Fixed_50_Cycles'] = 'Fixed_10_Cycles'
    optimization_budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=3600)] = 120
    budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=14400)] = 600

    @model_validator(mode='after')
    def fixed_contract(self):
        if self.seed == self.validation_seed:raise ValueError('独立验证需要不同随机种子。')
        if not self.merit.wizard or self.merit.wizard.optimize_for_manufacturing_yield is not True:
            raise ValueError('需要启用原生制造良率向导。')
        if self.merit.targets:raise ValueError('制造良率采用原生向导采样；附加边界通过constraints设置。')
        if len({(v.surface,v.cell) for v in self.variables}) != len(self.variables):raise ValueError('设计变量不得重复。')
        return self


def sensitivity_norm(result):
    criteria=result['summary']['sensitivity']
    if not criteria:raise ZemaxError('INVALID_RESULT_DATA', '原生灵敏度结果为空。')
    data=criteria[0]
    effects=[max(abs(float(e['minimum'])),abs(float(e['maximum']))) for e in data['effects']]
    if not effects or any(not math.isfinite(x) for x in effects):
        raise ZemaxError('INVALID_RESULT_DATA','灵敏度效应缺失或非有限。')
    return dict(nominal=float(data['nominal']),rss=math.sqrt(math.fsum(x*x for x in effects)),
                definition='RSS of max absolute native estimated criterion changes per tolerance operand',native=data)


def run_desensitize(b,q):
    from .data import unwrap
    from .coating_optimization import operand
    from .tolerance_models import ToleranceRange,TolerancePatch,ToleranceAnalysis,ToleranceSummary
    b._require_sequential(focused=True);b._require_work()
    wizard=unwrap(b.system.MFE.SEQOptimizationWizard2)
    if not wizard.IsHighManufacturingYieldAvailable:
        raise ZemaxError('CAPABILITY_UNAVAILABLE','当前系统未开放原生制造良率优化。',route='SEQOptimizationWizard2')
    def flow(task):
        snapshot=b._checkpoint('desensitization_baseline');source,work=b.source_path,b.work_path
        deadline=time.monotonic()+q.budget_seconds
        task['payload']=dict(analysis_kind=q.kind,route='native manufacturing yield wizard',series=[],grids=[],
            actual_request=q.model_dump(),baseline_path=snapshot)
        def boundary():
            b._cancel_boundary(task)
            if time.monotonic()>=deadline:raise ZemaxError('BUDGET_EXCEEDED','设计去敏感化时间预算已用完。')
        def set_seed(seed,original):
            rows=[dict(type='SEED',param1=seed)]
            for row in original:
                if row['type']=='SEED':continue
                values=dict(type=row['type'],comment=row['comment'],ignore=row['ignore'],inverse_protected=row['inverse_protected'])
                values.update({f'param{k}':v for k,v in row['parameters'].items()})
                values.update({k:row[k] for k in ['minimum','maximum'] if row[k] is not None})
                rows.append(values)
            b.update_tolerances(TolerancePatch(mode='replace',operands=rows))
        def native(mode,samples=1):
            boundary()
            return ToleranceAnalysis(mode=mode,criterion=q.criterion,compensation=q.compensation,sampling=q.sampling,
                samples=samples,distribution=q.distribution,budget_seconds=max(.001,deadline-time.monotonic()))
        def mc(label,phase,samples,seed,original):
            boundary();set_seed(seed,original)
            result=yield from b._child_job(task,b.run_tolerance_analysis,native('monte_carlo',samples))
            columns=[c['column'] for c in result['summary']['columns'] if not c['is_operand']]
            if not columns:raise ZemaxError('INVALID_RESULT_DATA','Monte Carlo缺少准则列。')
            stat=b.summarize_tolerance_results(ToleranceSummary(task_id=result['task']['task_id'],criterion_column=columns[0],
                threshold=q.threshold,unit=q.criterion_unit))
            if stat['missing'] or stat['nonfinite_indices']:raise ZemaxError('INVALID_RESULT_DATA','Monte Carlo结果不完整。',statistics=stat)
            record=dict(design=label,phase=phase,seed=seed,statistics=stat,interval=wilson(stat['passed'],samples,.95),
                task_id=result['task']['task_id'],samples=result['rows'],actual=result['summary']['actual'])
            task['rows'].append(record)
            return record
        try:
            yield;boundary()
            original=[];start=1
            while start is not None:
                page=b.get_tolerances(ToleranceRange(start=start,count=1000));original.extend(page['rows']);start=page['next_start']
            if not any(r['type'].startswith('T') and not r['ignore'] for r in original):
                raise ZemaxError('INVALID_ARGUMENT','需要活动的固定制造公差。')
            if any(r['type']=='STAT' and not r['ignore'] for r in original):
                raise ZemaxError('UNSUPPORTED_DISTRIBUTION_SCOPE','此流程采用请求的统一分布。')
            task['payload']['fixed_tolerances']=original
            before=yield from b._child_job(task,b.run_tolerance_analysis,native('sensitivity'))
            before_norm=sensitivity_norm(before);task['payload']['sensitivity_before']=before_norm
            yield from mc('baseline','screening',q.screening_samples,q.seed,original)
            yield from mc('baseline','validation',q.validation_samples,q.validation_seed,original)
            boundary();b._restore_model(task,snapshot,source,work)
            b._mutate('desensitization_merit')
            settings,_,constraints=build(b,b.system,q.merit)
            task['payload']['wizard_settings']=settings
            for surface in range(int(b.system.LDE.NumberOfSurfaces)):
                row=b.system.LDE.GetSurfaceAt(surface)
                for cell in [row.RadiusCell,row.ThicknessCell]:
                    if str(cell.Solve)=='Variable':b._set_variable_mode(cell,False)
            for v in q.variables:
                row=b._row(v.surface);cell=b._cell(row,v.cell);b._guard_cell(cell,False)
                actual=float(cell.DoubleValue)
                if not v.minimum<=actual<=v.maximum:raise ZemaxError('INVALID_ARGUMENT','变量起点超出边界。',variable=v.model_dump(),actual=actual)
                b._set_variable_mode(cell,True)
                codes=('CVGT','CVLT') if v.cell=='radius' else ('CTGT','CTLT')
                bounds=sorted([1/v.minimum,1/v.maximum]) if v.cell=='radius' else [v.minimum,v.maximum]
                for code,value in zip(codes,bounds):operand(b,b.system.MFE,code,{2:v.surface},value,1e6)
            task['payload']['merit_operands']=native_rows(b,b.system)
            def launch(_):
                diagnostics=b._optimization_preflight()
                b._mutate('desensitization_optimization')
                tool=b.system.Tools.OpenLocalOptimization()
                try:
                    b.native.set_enum(tool,'Algorithm','DampedLeastSquares')
                    b.native.set_enum(tool,'Cycles',q.cycles)
                    tool.NumberOfCores=1
                    return b._start_task('local_optimization',tool,
                        dict(algorithm=str(tool.Algorithm),cycles=str(tool.Cycles),number_of_cores=int(tool.NumberOfCores)),
                        before=dict(merit_function=diagnostics['merit_function'],variables=diagnostics['variables']),
                        budget_seconds=min(q.optimization_budget_seconds,max(.001,deadline-time.monotonic())))
                except Exception:
                    b._release_owned(tool)
                    raise
            optimized=yield from b._child_job(task,launch,None)
            task['payload']['optimization']=optimized
            for v in q.variables:
                actual=float(b._cell(b._row(v.surface),v.cell).DoubleValue)
                if not v.minimum-1e-8<=actual<=v.maximum+1e-8:
                    raise ZemaxError('DESIGN_BOUNDS_VIOLATED','优化后变量超出边界。',actual=actual,variable=v.model_dump())
            path=Path(b.directory)/(task['task_id']+'_optimized.zos');b.system.SaveAs(str(path));b.system.SaveAs(str(work))
            # Load the saved native design before final sensitivity and Monte Carlo.
            b._restore_model(task,str(path),source,work)
            after=yield from b._child_job(task,b.run_tolerance_analysis,native('sensitivity'))
            after_norm=sensitivity_norm(after);task['payload']['sensitivity_after']=after_norm
            yield from mc('optimized','screening',q.screening_samples,q.seed,original)
            yield from mc('optimized','validation',q.validation_samples,q.validation_seed,original)
            reduction=1-after_norm['rss']/before_norm['rss'] if before_norm['rss']>0 else None
            task['summary']=dict(saved_model=str(path),sensitivity_reduction=reduction,nominal=after_norm['nominal'],
                nominal_passed=after_norm['nominal']<=q.maximum_nominal,
                sensitivity_passed=reduction is not None and reduction>=q.minimum_sensitivity_reduction,
                validation_samples=q.validation_samples,fixed_tolerance_ranges=True)
            task['payload']['series']=[dict(series=0,description='Fixed-tolerance sensitivity',x_label='design',x_unit='index',
                y_unit=q.criterion_unit,labels=['native sensitivity RSS'],x=[0,1],y=[[before_norm['rss']],[after_norm['rss']]])]
        finally:
            b._restore_model(task,snapshot,source,work)
    return b._composite(q.kind,q.model_dump(),flow)
