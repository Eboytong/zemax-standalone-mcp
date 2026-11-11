"""Native weighted-merit candidates and target-distance Pareto ranking."""
import math
import time
from typing import Annotated
from pydantic import Field, model_validator
from .schema import FiniteFloat, PositiveIndex, Request
from .errors import ZemaxError
from .detectors import check_setting_value


class ParetoObjective(Request):
    operand: PositiveIndex
    target: FiniteFloat
    scale: Annotated[FiniteFloat,Field(gt=0)]
    name: Annotated[str,Field(min_length=1,max_length=80)]
    maximum_error: Annotated[FiniteFloat,Field(ge=0)] | None = None


class ParetoSettings(Request):
    objectives: Annotated[list[ParetoObjective],Field(min_length=2,max_length=8)]
    weight_grid: Annotated[list[list[Annotated[FiniteFloat,Field(gt=0)]]],Field(min_length=2,max_length=50)]
    budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 120

    @model_validator(mode='after')
    def contract(self):
        if len({v.operand for v in self.objectives})!=len(self.objectives):
            raise ValueError('Pareto目标使用不同操作数行。')
        if len({v.name for v in self.objectives})!=len(self.objectives):
            raise ValueError('Pareto目标名称不得重复。')
        for weights in self.weight_grid:
            if len(weights)!=len(self.objectives):raise ValueError('每个权重组合须与目标数量相同。')
            try:
                invalid=any(not math.isfinite(w/o.scale**2) or w/o.scale**2==0 for w,o in zip(weights,self.objectives))
            except (OverflowError,ZeroDivisionError):invalid=True
            if invalid:raise ValueError('原生缩放权重超出有限正数范围。')
        return self


def rank_candidates(rows):
    valid=[r for r in rows if r.get('state')=='succeeded' and r.get('feasible')]
    for row in rows:
        row['dominated_by']=[]
        row['pareto_optimal']=False
        if row not in valid:continue
        vector=row['normalized_errors']
        for other in valid:
            if other is row:continue
            candidate=other['normalized_errors']
            if all(a<=b for a,b in zip(candidate,vector)) and any(a<b for a,b in zip(candidate,vector)):
                row['dominated_by'].append(other['index'])
        row['pareto_optimal']=not row['dominated_by']
    return [r['index'] for r in valid if r['pareto_optimal']]


def run_pareto(b,req):
    from .models import UpdateSurfaces
    from .evaluation import Cancelled
    q=req.pareto
    b._require_sequential()
    if len(req.starts)*len(q.weight_grid)>200:
        raise ZemaxError('INVALID_ARGUMENT','起点与权重组合的乘积须不大于200。')
    def flow(task):
        deadline=time.monotonic()+q.budget_seconds
        source,work=b.source_path,b.work_path
        snapshot=b._checkpoint('pareto_baseline')
        task['baseline']=dict(path=snapshot,context=b.context())
        task['payload']=dict(objectives=[v.model_dump() for v in q.objectives],
            search_definition='finite starts × positive weight grid; native target-distance scalar optimization',
            objective_direction='minimize abs(native value - target) / scale',series=[],grids=[])
        try:
            for start_index,changes in enumerate(req.starts):
                for weight_index,weights in enumerate(q.weight_grid):
                    b._cancel_boundary(task)
                    if time.monotonic()>=deadline:raise ZemaxError('BUDGET_EXCEEDED','Pareto搜索时间预算已用完。')
                    b._restore_model(task,snapshot,source,work)
                    row=dict(index=len(task['rows']),start_index=start_index,weight_index=weight_index,weights=weights)
                    try:
                        b.update_surfaces(UpdateSurfaces(changes=changes))
                        mfe=b.system.MFE
                        if max(o.operand for o in q.objectives)>int(mfe.NumberOfOperands):
                            raise ZemaxError('INDEX_OUT_OF_RANGE','Pareto目标操作数行越界。')
                        native=[]
                        for spec,weight in zip(q.objectives,weights):
                            op=mfe.GetOperandAt(spec.operand)
                            op.Target=spec.target;op.Weight=weight/spec.scale**2
                            check_setting_value('Target',spec.target,float(op.Target))
                            check_setting_value('Weight',weight/spec.scale**2,float(op.Weight))
                            native.append(dict(operand=spec.operand,type=str(op.Type),target=float(op.Target),weight=float(op.Weight)))
                        row['actual_objectives']=native
                        def start(spec):
                            view=b.run_local_optimization(spec)
                            child=b.tasks[view['task_id']]
                            child['budget_seconds']=max(.001,deadline-child['started_monotonic'])
                            child['budget_deadline']=deadline
                            return view
                        optimized=yield from b._child_job(task,start,req.optimization)
                        row['optimization_task']=optimized['task']['task_id']
                        row['evaluation']=yield from b._evaluate(task,req.evaluation)
                        mfe.CalculateMeritFunction()
                        values=[float(mfe.GetOperandAt(o.operand).Value) for o in q.objectives]
                        for spec,actual in zip(q.objectives,row['actual_objectives']):
                            op=mfe.GetOperandAt(spec.operand)
                            check_setting_value('OperandType',actual['type'],str(op.Type))
                            check_setting_value('Target',spec.target,float(op.Target))
                            check_setting_value('Weight',actual['weight'],float(op.Weight))
                        if any(not math.isfinite(v) for v in values):
                            raise ZemaxError('INVALID_METRIC_VALUE','Pareto目标返回非有限值。')
                        errors=[abs(v-o.target) for v,o in zip(values,q.objectives)]
                        normalized=[v/o.scale for v,o in zip(errors,q.objectives)]
                        if any(not math.isfinite(v) for v in normalized):
                            raise ZemaxError('INVALID_METRIC_VALUE','Pareto归一化误差返回非有限值。')
                        violations=[max(0,e-o.maximum_error)/o.scale if o.maximum_error is not None else 0 for e,o in zip(errors,q.objectives)]
                        path=b.directory/(task['task_id']+f'_pareto_{row["index"]}.zos')
                        b.system.SaveAs(str(path));b.system.SaveAs(str(work))
                        row.update(state='succeeded',values=values,absolute_errors=errors,normalized_errors=normalized,
                            constraint_violations=violations,feasible=all(v==0 for v in violations),path=str(path))
                    except Cancelled:raise
                    except Exception as exc:
                        row.update(state='failed',error=b._evaluation_error(exc))
                        if b.requires_reconnect:raise
                    task['rows'].append(row)
                    task['progress']=int(100*len(task['rows'])/(len(req.starts)*len(q.weight_grid)))
                    yield
            if not any(r['state']=='succeeded' for r in task['rows']):
                raise ZemaxError('NO_VALID_CANDIDATE','全部Pareto候选执行失败。')
        finally:
            b._restore_model(task,snapshot,source,work)
            front=rank_candidates(task['rows'])
            task['summary']=dict(candidate_count=len(task['rows']),pareto_indices=front,
                succeeded=sum(r['state']=='succeeded' for r in task['rows']),
                feasible=sum(bool(r.get('feasible')) for r in task['rows']),retained_best=False,
                frontier_scope='evaluated feasible candidates',baseline_restored=task.get('restoration',{}).get('restored',False),
                budget_seconds=q.budget_seconds,budget_expired=time.monotonic()>=deadline)
            valid=[r for r in task['rows'] if r['state']=='succeeded']
            task['payload']['series']=[dict(series=0,description='Candidate normalized target errors',x_label='candidate',x_unit='index',y_unit='dimensionless',
                labels=[o.name for o in q.objectives],x=[r['index'] for r in valid],y=[r['normalized_errors'] for r in valid])]
    return b._composite('pareto_optimization',req.model_dump(),flow)
