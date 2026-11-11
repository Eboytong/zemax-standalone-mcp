"""Native two-mirror response calibration and discrete offline feedback."""
import math
import random
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import FiniteFloat,PositiveIndex,Request
from .errors import ZemaxError
from .detectors import check_setting_value

Vector4=Annotated[list[FiniteFloat],Field(min_length=4,max_length=4)]


class FsmMirror(Request):
    tilt_surface: PositiveIndex
    mirror_surface: PositiveIndex
    return_surface: PositiveIndex

    @model_validator(mode='after')
    def adjacent(self):
        if self.mirror_surface!=self.tilt_surface+1 or self.return_surface!=self.mirror_surface+1:
            raise ValueError('FSM使用相邻前断点、平面镜、后断点。')
        return self


class FsmControl(Request):
    kind: Literal['fsm_control']
    start_surface: PositiveIndex
    mirrors: Annotated[list[FsmMirror],Field(min_length=2,max_length=2)]
    observation_surfaces: Annotated[list[PositiveIndex],Field(min_length=2,max_length=2)]
    disturbances: Annotated[list[Vector4],Field(min_length=2,max_length=100)]
    sample_period_seconds: Annotated[FiniteFloat,Field(gt=0,le=10)]
    actuator_time_constant_seconds: Annotated[FiniteFloat,Field(ge=0,le=100)] = 0
    delay_samples: Annotated[int,Field(strict=True,ge=0,le=20)] = 0
    gain: Annotated[FiniteFloat,Field(gt=0,le=2)] = .5
    limits_deg: Annotated[list[Annotated[FiniteFloat,Field(gt=0,le=5)]],Field(min_length=4,max_length=4)] = [.1,.1,.1,.1]
    measurement_noise_std: Annotated[list[Annotated[FiniteFloat,Field(ge=0)]],Field(min_length=4,max_length=4)] = [0,0,0,0]
    seed: Annotated[int,Field(strict=True,ge=0,le=2147483647)] = 0
    probe_angle_deg: Annotated[FiniteFloat,Field(gt=0,le=.01)] = .0001
    probe_height: Annotated[FiniteFloat,Field(gt=0,le=.1)] = .0001
    probe_slope: Annotated[FiniteFloat,Field(gt=0,le=.001)] = .000001
    wavelength: PositiveIndex = 1
    condition_limit: Annotated[FiniteFloat,Field(gt=1)] = 1e8
    residual_tolerance: Annotated[FiniteFloat,Field(gt=0)] = .00001
    validation_tolerance: Annotated[FiniteFloat,Field(gt=0)] = .00001

    @model_validator(mode='after')
    def order(self):
        if not self.start_surface<self.mirrors[0].tilt_surface or not self.mirrors[0].return_surface<self.mirrors[1].tilt_surface:
            raise ValueError('输入面和两个FSM须按传播顺序排列。')
        if not self.mirrors[1].return_surface<self.observation_surfaces[0]<self.observation_surfaces[1]:
            raise ValueError('两个观测面须位于FSM之后且依次排列。')
        if self.probe_angle_deg>min(self.limits_deg):raise ValueError('角度探针须位于执行器范围内。')
        return self


def matvec(matrix,vector):
    result=[sum(a*b for a,b in zip(row,vector)) for row in matrix]
    if any(not math.isfinite(v) for v in result):raise ZemaxError('INVALID_CONTROL_VALUE','控制矩阵计算超出有限数值范围。')
    return result


def response_inverse(matrix,limit):
    from .scan_pupil import inverse
    try:inverted=inverse(matrix)
    except ZemaxError as exc:raise ZemaxError('UNOBSERVABLE_FSM','双平面四自由度响应矩阵秩不足。') from exc
    condition=max(sum(abs(v) for v in row) for row in matrix)*max(sum(abs(v) for v in row) for row in inverted)
    if not math.isfinite(condition) or condition>limit:
        raise ZemaxError('ILL_CONDITIONED_FSM','原生响应矩阵条件数超过阈值。',condition=condition,maximum=limit)
    return inverted,condition


def simulate(response,disturbance_response,q):
    inverted,condition=response_inverse(response,q.condition_limit)
    rng=random.Random(q.seed)
    command=[0.]*4;actual=[0.]*4;measurements=[];rows=[]
    alpha=1 if q.actuator_time_constant_seconds==0 else -math.expm1(-q.sample_period_seconds/q.actuator_time_constant_seconds)
    for k,disturbance in enumerate(q.disturbances):
        actual=[a+alpha*(c-a) for a,c in zip(actual,command)]
        residual=[a+b for a,b in zip(matvec(response,actual),matvec(disturbance_response,disturbance))]
        measured=[v+rng.gauss(0,s) if s else v for v,s in zip(residual,q.measurement_noise_std)]
        measurements.append(measured)
        delayed=measurements[k-q.delay_samples] if k>=q.delay_samples else [0.]*4
        correction=matvec(inverted,delayed)
        requested=[v-q.gain*c for v,c in zip(command,correction)]
        updated=[max(-limit,min(limit,v)) for v,limit in zip(requested,q.limits_deg)]
        rows.append(dict(sample=k,time_seconds=k*q.sample_period_seconds,disturbance=disturbance,
            actual_angles_deg=list(actual),command_angles_deg=list(command),next_command_angles_deg=updated,
            residual=residual,measurement=measured,max_abs_residual=max(map(abs,residual)),
            saturated=[a!=b for a,b in zip(requested,updated)]))
        command=updated
    settling=next((row['time_seconds'] for i,row in enumerate(rows)
                   if all(v['max_abs_residual']<=q.residual_tolerance for v in rows[i:])),None)
    return rows,dict(condition_infinity_norm=condition,actuator_discrete_alpha=alpha,
        settling_time_seconds=settling,converged=rows[-1]['max_abs_residual']<=q.residual_tolerance,
        saturated_samples=sum(any(v['saturated']) for v in rows),final_residual=rows[-1]['residual'])


def run_fsm_control(b,q):
    from .models import BatchRays
    from .scan_pupil import RayOwner
    b._require_sequential();b._require_work()
    def flow(task):
        system=None;errors=[];original_error=None
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],
            control_definition='u[k+1]=clip(u[k]-gain*inverse(R)*measurement[k-delay]); first-order actuators',
            state_order=['input_x','input_y','input_l/n','input_m/n'],
            observation_order=['plane1_x','plane1_y','plane2_x','plane2_y'],
            command_order=['mirror1_X','mirror1_Y','mirror2_X','mirror2_Y'],
            units=dict(position='lens units',slope='dimensionless',actuator='degrees',time='seconds'))
        task['restoration']=dict(required=False,restored=True,reason='owned native copy; source unchanged')
        try:
            system=b.system.CopySystem()
            if system is None:raise ZemaxError('COPY_FAILED','FSM副本创建失败。')
            if q.observation_surfaces[-1]>=int(system.LDE.NumberOfSurfaces) or q.wavelength>int(system.SystemData.Wavelengths.NumberOfWavelengths):
                raise ZemaxError('INDEX_OUT_OF_RANGE','FSM目标面或波长编号越界。')
            cells=[];bases=[]
            for spec in q.mirrors:
                before=system.LDE.GetSurfaceAt(spec.tilt_surface);mirror=system.LDE.GetSurfaceAt(spec.mirror_surface);after=system.LDE.GetSurfaceAt(spec.return_surface)
                if str(before.Type)!='CoordinateBreak' or str(after.Type)!='CoordinateBreak' or str(mirror.Material)!='MIRROR' or str(mirror.Type)!='Standard' or not math.isinf(float(mirror.Radius)):
                    raise ZemaxError('UNSUPPORTED_FSM_MODEL','FSM采用CoordinateBreak/平面MIRROR/CoordinateBreak。')
                if abs(float(before.Thickness))+abs(float(mirror.Thickness))>1e-12:
                    raise ZemaxError('INVALID_FSM_PIVOT','FSM三个面须共点。')
                for row in [before,after]:
                    if any(abs(float(b._cell(row,f'parameter_{i}').DoubleValue))>1e-12 for i in [1,2,5]):
                        raise ZemaxError('UNSUPPORTED_FSM_MODEL','FSM断点使用零偏心及零Z旋转。')
                if b._cell_value(b._cell(before,'parameter_6'))!=0 or b._cell_value(b._cell(after,'parameter_6'))!=1:
                    raise ZemaxError('INVALID_FSM_RETURN_ORDER','前断点Order=0，后断点Order=1以恢复固定观测坐标。')
                for p in [3,4]:
                    a=b._cell(before,f'parameter_{p}');c=b._cell(after,f'parameter_{p}')
                    b._guard_cell(a);b._guard_cell(c)
                    if abs(float(a.DoubleValue)+float(c.DoubleValue))>1e-10:
                        raise ZemaxError('INVALID_FSM_RETURN','后断点旋转须与前断点互逆。')
                    cells.append((a,c));bases.append(float(a.DoubleValue))
            fixed=[list(system.LDE.GetGlobalMatrix(i)) for i in q.observation_surfaces]
            if any(not t[0] for t in fixed):raise ZemaxError('INVALID_TRANSFORM','观测面坐标变换无效。')
            owner=RayOwner(b,system)
            observed_directions=[]
            def pose(angles):
                for (a,c),base,delta in zip(cells,bases,angles):
                    a.DoubleValue=base+delta;c.DoubleValue=-base-delta
                system.UpdateStatus()
                for (a,c),base,delta in zip(cells,bases,angles):
                    check_setting_value('FSM tilt',base+delta,float(a.DoubleValue));check_setting_value('FSM return',-base-delta,float(c.DoubleValue))
                for i,reference in zip(q.observation_surfaces,fixed):
                    current=list(system.LDE.GetGlobalMatrix(i))
                    if not current[0] or any(abs(a-c)>1e-8 for a,c in zip(current[1:],reference[1:])):
                        raise ZemaxError('FSM_SENSOR_FRAME_MOVED','FSM旋转改变了固定观测面坐标。',surface=i)
            def observe(inputs):
                rays=[]
                for x,y,sx,sy in inputs:
                    n=1/math.sqrt(1+sx*sx+sy*sy)
                    rays.append(dict(x=x,y=y,z=0,l=sx*n,m=sy*n,n=n,wavelength=q.wavelength))
                targets=[]
                for target in q.observation_surfaces:
                    req=BatchRays(input_mode='Direct',start_surface=q.start_surface,target_surface=target,rays=rays)
                    def start(_):
                        return b._composite('fsm_native_rays',dict(target=target,ray_count=len(rays)),lambda child:owner._extended_trace_flow(child,req,target))
                    result=yield from b._child_job(task,start,None)
                    rows=result['rows']
                    if len(rows)!=len(rays) or any(r.get('error_code') or r.get('vignette_code') or not r.get('position') or not r.get('direction') or abs(r['direction'][2])<1e-8 for r in rows):
                        raise ZemaxError('FSM_RAY_FAILED','FSM光线未到达观测面。',target=target)
                    targets.append(rows)
                observed_directions[:]=[r['direction'] for r in targets[-1]]
                return [targets[0][i]['position'][:2]+targets[1][i]['position'][:2] for i in range(len(inputs))]
            pose([0]*4)
            probes=[[0.]*4]
            steps=[q.probe_height,q.probe_height,q.probe_slope,q.probe_slope]
            for i,step in enumerate(steps):
                for sign in [1,-1]:
                    ray=[0.]*4;ray[i]=sign*step;probes.append(ray)
            measured=yield from observe(probes);baseline=measured[0]
            baseline_slopes=[v/observed_directions[0][2] for v in observed_directions[0][:2]]
            disturbance_response=[[(measured[1+2*j][i]-measured[2+2*j][i])/(2*steps[j]) for j in range(4)] for i in range(4)]
            response=[[0.]*4 for _ in range(4)]
            for axis in range(4):
                outputs=[]
                for sign in [1,-1]:
                    angles=[0.]*4;angles[axis]=sign*q.probe_angle_deg;pose(angles)
                    outputs.append((yield from observe([[0.]*4]))[0])
                for i in range(4):response[i][axis]=(outputs[0][i]-outputs[1][i])/(2*q.probe_angle_deg)
            rows,summary=simulate(response,disturbance_response,q)
            task['payload'].update(response_matrix=response,disturbance_matrix=disturbance_response,baseline_observations=baseline,
                observation_transforms=fixed,nominal_angles_deg=bases,actual_settings=q.model_dump())
            maximum=0.
            for row in rows:
                b._cancel_boundary(task);pose(row['actual_angles_deg'])
                actual=(yield from observe([row['disturbance']]))[0]
                actual=[a-c for a,c in zip(actual,baseline)]
                error=max(abs(a-c) for a,c in zip(actual,row['residual']))
                row.update(native_residual=actual,native_linear_error=error)
                slopes=[v/observed_directions[0][2] for v in observed_directions[0][:2]]
                row['native_output_slope_residual']=[a-c for a,c in zip(slopes,baseline_slopes)]
                row['native_output_angle_residual_rad']=[math.atan(a)-math.atan(c) for a,c in zip(slopes,baseline_slopes)]
                maximum=max(maximum,error);task['rows'].append(row)
                task['progress']=int(100*len(task['rows'])/len(rows));yield
            summary.update(max_native_linear_error=maximum,native_validation_passed=maximum<=q.validation_tolerance,
                final_output_slope_residual=rows[-1]['native_output_slope_residual'],
                actuator_bandwidth_hz=1/(2*math.pi*q.actuator_time_constant_seconds) if q.actuator_time_constant_seconds else None,
                sample_count=len(rows),time_definition='explicit discrete period, delay and actuator time constant; API wall time is separate')
            task['summary']=summary
            if maximum>q.validation_tolerance:
                raise ZemaxError('FSM_LINEAR_RANGE_EXCEEDED','有限扰动原生复算超出线性响应容差。',maximum_error=maximum,tolerance=q.validation_tolerance)
            task['payload']['series']=[dict(series=0,description='Dual FSM residual observations',x_label='time',x_unit='seconds',y_unit='lens units',
                labels=['plane1_x','plane1_y','plane2_x','plane2_y'],x=[r['time_seconds'] for r in rows],y=[r['native_residual'] for r in rows])]
        except BaseException as exc:original_error=exc;raise
        finally:
            if system is not None:
                try:
                    if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                except Exception as exc:errors.append(str(exc));b.requires_reconnect=True
            task['payload']['resources']=dict(copy_closed=system is not None and not errors,cleanup_errors=errors)
            if errors:raise ZemaxError('CLEANUP_FAILED','FSM副本关闭失败。',cleanup_errors=errors,operation_error=b._evaluation_error(original_error) if original_error else None)
    return b._composite(q.kind,q.model_dump(),flow)
