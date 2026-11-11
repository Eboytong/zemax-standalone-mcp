"""Native POP receiver-pose scans, bounded pattern search and loss crossings."""
import itertools
import json
import math
import time
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .errors import ZemaxError
from .pop_models import Pop
from .schema import FiniteFloat, Request

AXES = ('x','y','z','tilt_x','tilt_y')
AxisName = Literal['x','y','z','tilt_x','tilt_y']


class AlignmentAxis(Request):
    axis: AxisName
    values: Annotated[list[FiniteFloat], Field(min_length=2,max_length=101)]

    @model_validator(mode='after')
    def increasing(self):
        if any(b<=a for a,b in zip(self.values,self.values[1:])):
            raise ValueError('扫描坐标必须严格递增。')
        return self


class AlignmentBound(Request):
    axis: AxisName
    minimum: FiniteFloat
    maximum: FiniteFloat

    @model_validator(mode='after')
    def interval(self):
        if self.minimum>=self.maximum:
            raise ValueError('寻优下界必须小于上界。')
        return self


class AlignmentSearch(Request):
    bounds: Annotated[list[AlignmentBound],Field(min_length=1,max_length=5)]
    max_iterations: Annotated[int,Field(strict=True,ge=1,le=100)] = 30
    relative_step_tolerance: Annotated[FiniteFloat,Field(gt=0,le=.1)] = .001

    @model_validator(mode='after')
    def unique(self):
        if len({v.axis for v in self.bounds})!=len(self.bounds):
            raise ValueError('寻优轴不得重复。')
        return self


class FiberAlignment(Request):
    kind: Literal['fiber_alignment']
    settings: Pop
    axes: Annotated[list[AlignmentAxis],Field(min_length=1,max_length=2)]
    optimization: AlignmentSearch | None = None
    tolerance_axes: Annotated[list[AlignmentAxis],Field(max_length=5)] | None = None
    refine: bool = True
    max_evaluations: Annotated[int,Field(strict=True,ge=2,le=2000)] = 500
    budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 600
    save_best: bool = True

    @model_validator(mode='after')
    def contract(self):
        s = self.settings
        if s.fiber_type!='AstigmaticGaussian' or s.fiber_file is not None:
            raise ValueError('对准工作流使用AstigmaticGaussian原生接收模式。')
        if not s.save_output_beam or s.data_type!='Irradiance':
            raise ValueError('耦合评价需要Irradiance及save_output_beam=true。')
        if any(i not in range(6) for i in s.fiber_parameters):
            raise ValueError('AstigmaticGaussian接收参数编号为0—5。')
        if any(s.fiber_parameters.get(i,0)<=0 for i in (0,1)):
            raise ValueError('必须明确指定两个正的接收束腰半径。')
        for axes in (self.axes,self.tolerance_axes or []):
            if len({a.axis for a in axes})!=len(axes):
                raise ValueError('扫描或容差轴不得重复。')
        angle_ranges = [(a.axis,min(a.values),max(a.values)) for a in
                        self.axes+(self.tolerance_axes or [])]
        if self.optimization:
            angle_ranges += [(a.axis,a.minimum,a.maximum) for a in self.optimization.bounds]
        for axis,low,high in angle_ranges:
            if axis.startswith('tilt'):
                base = getattr(s,'fiber_'+axis)
                if not -89.9<=base+low<=base+high<=89.9:
                    raise ValueError('实际接收倾角范围必须处于−89.9至89.9度。')
        required = math.prod(len(a.values) for a in self.axes)
        if self.refine:
            required += math.prod(2*len(a.values)-1 for a in self.axes)-required
        if required>self.max_evaluations:
            raise ValueError('max_evaluations小于所请求扫描的点数。')
        return self


def refined(values):
    return sorted(values+[(a+b)/2 for a,b in zip(values,values[1:])])


def pose_settings(settings,pose):
    parameters = {i:settings.fiber_parameters.get(i,0.) for i in range(6)}
    parameters[4] += pose.get('x',0.)
    parameters[5] += pose.get('y',0.)
    parameters[2] += pose.get('z',0.)
    parameters[3] += pose.get('z',0.)
    return settings.model_copy(update=dict(fiber_parameters=parameters,
        fiber_tilt_x=settings.fiber_tilt_x+pose.get('tilt_x',0.),
        fiber_tilt_y=settings.fiber_tilt_y+pose.get('tilt_y',0.)))


def loss_crossings(values,efficiencies,peak_value,peak_position,db):
    """Nearest bracketing crossings around the selected pose, interpolated in dB."""
    if peak_value<=0:
        return dict(loss_db=db,state='zero_peak',left=None,right=None,width=None)
    points = sorted(zip(values,efficiencies))
    target = peak_value*10**(-db/10)
    crossings = []
    for (a,va),(b,vb) in zip(points,points[1:]):
        if va==target:
            crossings.append(a)
        if (va-target)*(vb-target)<0 or vb==target:
            if va>0 and vb>0:
                la,lb = 10*math.log10(va/peak_value),10*math.log10(vb/peak_value)
                x = a+(-db-la)*(b-a)/(lb-la)
            else:
                x = a+(target-va)*(b-a)/(vb-va)
            crossings.append(x)
    left = max((x for x in crossings if x<=peak_position),default=None)
    right = min((x for x in crossings if x>=peak_position),default=None)
    return dict(loss_db=db,threshold=target,left=left,right=right,
        left_offset=left-peak_position if left is not None else None,
        right_offset=right-peak_position if right is not None else None,
        width=right-left if left is not None and right is not None else None,
        state='bracketed' if left is not None and right is not None else 'range_not_bracketing',
        interpolation='linear loss dB; linear efficiency for zero endpoint')


class EvaluationBudget(Exception):
    pass


def run_fiber_alignment(b,q):
    b._require_sequential()
    b._require_work()
    unit = str(b.system.SystemData.Units.LensUnits)

    def flow(task):
        started = time.monotonic()
        cache = {}
        best = None
        coarse_best = None
        rounds = 0
        stop_reason = 'completed'
        search_status = 'not_requested'
        task['payload'] = dict(analysis_kind=q.kind,series=[],grids=[],tolerances=[],
            receiver_definition='AstigmaticGaussian complex receiver field evaluated at POP end plane',
            coordinates=dict(translation='receiver parameter deltas in native POP transverse frame',
                axial='equal delta added to native X/Y waist positions; positive sign follows native waist convention',
                tilt='native TiltAboutX/Y deltas, degrees',length_unit=unit),
            metric='receiver_efficiency',computation_method='native POP fiber coupling integral',
            settings_mapping=dict(x='FiberParameter[4]',y='FiberParameter[5]',z='FiberParameter[2,3]',
                                  tilt_x='TiltAboutX',tilt_y='TiltAboutY'))
        task['baseline'] = dict(context=b.context(),settings=q.settings.model_dump())
        task['restoration'] = dict(required=False,restored=True,
            reason='receiver parameters belong to owned analysis objects; optical model is read-only')

        def evaluate(pose,phase):
            nonlocal best
            b._cancel_boundary(task)
            full = {name:float(pose.get(name,0)) for name in AXES}
            key = tuple(full[name] for name in AXES)
            if key in cache:
                return cache[key]
            if len(cache)>=q.max_evaluations or time.monotonic()-started>=q.budget_seconds:
                raise EvaluationBudget()
            settings = pose_settings(q.settings,full)
            record = dict(index=len(task['rows']),phase=phase,pose=full,status='running')
            task['rows'].append(record)
            try:
                result = yield from b._child_job(task,b.run_pop,settings)
                value = result['metrics']['receiver_efficiency']
                if type(value) not in {int,float} or not math.isfinite(value) or value<0 or value>1+1e-6:
                    raise ZemaxError('INVALID_METRIC','原生POP接收效率不在有限有效范围内。',value=repr(value))
            except Exception as exc:
                record.update(status='failed',error=b._evaluation_error(exc))
                raise
            record.update(status='succeeded',value=value,metrics=result['metrics'],
                task_id=result['task']['task_id'],actual_settings=result['task']['settings'],
                model_context=result['task'].get('context'),close_attempted=result['task'].get('close_attempted'))
            cache[key] = record
            if best is None or value>best['value']:
                best = record
                task['summary'] = dict(best=best,evaluations=len(cache),stop_reason='running')
            task['progress'] = min(99,100*len(cache)/q.max_evaluations)
            yield
            return record

        def grid_stage(axes,phase):
            records = []
            for values in itertools.product(*(a.values for a in axes)):
                record = yield from evaluate(dict(zip((a.axis for a in axes),values)),phase)
                records.append(record)
            return records

        try:
            coarse = yield from grid_stage(q.axes,'scan')
            coarse_best = max(coarse,key=lambda row:row['value'])
            axes = q.axes
            scan = coarse
            if q.refine:
                axes = [a.model_copy(update=dict(values=refined(a.values))) for a in q.axes]
                scan = yield from grid_stage(axes,'refined_scan')
            if len(axes)==1:
                task['payload']['series'].append(dict(series=0,description='POP receiver pose scan',
                    x_label=axes[0].axis,x_unit='degrees' if axes[0].axis.startswith('tilt') else unit,
                    y_label='receiver efficiency',y_unit='dimensionless',labels=['receiver_efficiency'],
                    x=axes[0].values,y=[[r['value']] for r in scan]))
            elif all(max(abs((v[i+1]-v[i])-(v[1]-v[0])) for i in range(len(v)-1))<1e-10*max(1,abs(v[-1]-v[0]))
                     for v in [a.values for a in axes]):
                a,c = axes
                nx,ny = len(a.values),len(c.values)
                lookup = {(r['pose'][a.axis],r['pose'][c.axis]):r['value'] for r in scan}
                task['payload']['grids'].append(dict(grid=0,description='POP receiver efficiency',
                    nx=nx,ny=ny,min_x=a.values[0],min_y=c.values[0],dx=a.values[1]-a.values[0],
                    dy=c.values[1]-c.values[0],x_label=a.axis,y_label=c.axis,
                    x_unit='degrees' if a.axis.startswith('tilt') else unit,
                    y_unit='degrees' if c.axis.startswith('tilt') else unit,value_unit='dimensionless',
                    values=[[lookup[(x,y)] for x in a.values] for y in c.values],array_order='values[y][x]'))
            else:
                task['payload']['scan_coordinates'] = {a.axis:a.values for a in axes}
            if q.optimization:
                bounds = q.optimization.bounds
                pose = dict(best['pose'])
                for bound in bounds:
                    pose[bound.axis] = max(bound.minimum,min(bound.maximum,pose[bound.axis]))
                current = yield from evaluate(pose,'search')
                step = {v.axis:(v.maximum-v.minimum)/4 for v in bounds}
                search_status = 'iteration_limit'
                for rounds in range(1,q.optimization.max_iterations+1):
                    improved = False
                    for bound in bounds:
                        selected = current
                        for sign in (-1,1):
                            trial = current['pose']|{bound.axis:max(bound.minimum,min(bound.maximum,
                                current['pose'][bound.axis]+sign*step[bound.axis]))}
                            candidate = yield from evaluate(trial,'search')
                            if candidate['value']>selected['value']:
                                selected = candidate
                        if selected['value']>current['value']:
                            current = selected
                            improved = True
                    if not improved:
                        step = {axis:value/2 for axis,value in step.items()}
                    if all(step[v.axis]/(v.maximum-v.minimum)<=q.optimization.relative_step_tolerance for v in bounds):
                        search_status = 'step_tolerance'
                        break
                # The selected best must satisfy all explicit search bounds.
                best = current
                task['payload']['search'] = dict(method='bounded coordinate pattern search; native POP objective',
                    state=search_status,iterations=rounds,steps=step,
                    at_boundary={v.axis:best['pose'][v.axis] in {v.minimum,v.maximum} for v in bounds})

            # Tolerance cuts hold the other four receiver-pose components at the selected best.
            selected = best
            for axis in q.tolerance_axes if q.tolerance_axes is not None else q.axes:
                sets = [axis.values,refined(axis.values)] if q.refine else [axis.values]
                cut_levels = []
                for values in sets:
                    values = sorted(set(values+[selected['pose'][axis.axis]]))
                    records = []
                    for v in values:
                        records.append((yield from evaluate(selected['pose']|{axis.axis:v},'tolerance')))
                    peak = selected['value']
                    crossings = [loss_crossings(values,[r['value'] for r in records],peak,
                                                selected['pose'][axis.axis],db) for db in (1,3)]
                    cut_levels.append(crossings)
                final = cut_levels[-1]
                for i,crossing in enumerate(final):
                    old = cut_levels[0][i]
                    relative = (abs(crossing['width']-old['width'])/abs(crossing['width'])
                                if crossing['width'] and old['width'] else None)
                    crossing.update(refinement_relative_width_change=relative,
                        converged=(relative<=.005) if q.refine and relative is not None else None)
                task['payload']['tolerances'].append(dict(axis=axis.axis,reference_pose=selected['pose'],
                    reference_efficiency=peak,unit='degrees' if axis.axis.startswith('tilt') else unit,
                    crossings=final,coarse_crossings=cut_levels[0],values=values,
                    efficiencies=[r['value'] for r in records]))
                task['payload']['series'].append(dict(series=len(task['payload']['series']),
                    description='Receiver tolerance '+axis.axis,x_label=axis.axis,
                    x_unit='degrees' if axis.axis.startswith('tilt') else unit,labels=['receiver_efficiency'],
                    y_unit='dimensionless',x=values,y=[[r['value']] for r in records]))
            best = selected
        except EvaluationBudget:
            stop_reason = 'evaluation_or_time_budget'
        finally:
            task['summary'] = dict(best=best,evaluations=len(cache),stop_reason=stop_reason,
                search_state=search_status,elapsed_seconds=time.monotonic()-started,
                coarse_best=coarse_best,refined=q.refine,
                peak_change_from_coarse=(best['value']-coarse_best['value']) if best and coarse_best else None)

        if best and q.save_best:
            b._cancel_boundary(task)
            model = Path(b.directory)/(task['task_id']+'_best.zos')
            request_file = model.with_suffix('.json')
            try:
                b.system.SaveAs(str(model))
            finally:
                try:
                    b.system.SaveAs(str(b.work_path))
                except Exception as exc:
                    b.requires_reconnect = True
                    raise ZemaxError('RESTORE_FAILED','最佳候选保存后恢复工作文件名失败。',
                                     native_message=str(exc)) from exc
            settings = pose_settings(q.settings,best['pose'])
            request_file.write_text(json.dumps(dict(tool='run_pop',arguments=dict(request=settings.model_dump()),
                model=str(model),pose_delta=best['pose'],receiver_efficiency=best['value'],
                source_task_id=best['task_id']),ensure_ascii=False,indent=2),encoding='utf-8')
            task['payload']['artifacts'] = [dict(kind='candidate_model',path=str(model)),
                                            dict(kind='candidate_request',path=str(request_file))]
            task['summary']['best_candidate'] = dict(model=str(model),request=str(request_file),
                settings_scope='receiver settings in companion request; optical model saved separately')
    return b._composite('fiber_alignment',q.model_dump(),flow)
