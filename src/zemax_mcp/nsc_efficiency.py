"""Owned pure-NSC evaluation, bounded scans and native detector optimization."""
import itertools
import math
import time
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .data import unwrap
from .detector_readers import axis, checked_scalar
from .detectors import check_setting_value
from .errors import ZemaxError
from .schema import FiniteFloat, PositiveIndex, Request


class NscRoi(Request):
    detector: PositiveIndex
    x_start: Annotated[int, Field(strict=True, ge=0)] = 0
    y_start: Annotated[int, Field(strict=True, ge=0)] = 0
    width: Annotated[int, Field(strict=True, ge=1, le=128)]
    height: Annotated[int, Field(strict=True, ge=1, le=128)]
    target_power: Annotated[FiniteFloat, Field(ge=0)] | None = None
    power_weight: Annotated[FiniteFloat, Field(gt=0, le=1e6)] = 1
    uniformity_weight: Annotated[FiniteFloat, Field(ge=0, le=1e6)] = 0


Cell = Literal['XPosition','YPosition','ZPosition','TiltX','TiltY','TiltZ','Power']


class NscDesignVariable(Request):
    object: PositiveIndex
    cell: Cell
    minimum: FiniteFloat
    maximum: FiniteFloat
    scan_values: Annotated[list[FiniteFloat], Field(max_length=25)] = Field(default_factory=list)

    @model_validator(mode='after')
    def bounds(self):
        if self.minimum >= self.maximum:raise ValueError('变量下界须小于上界。')
        if self.cell == 'Power' and self.minimum < 0:raise ValueError('源功率须非负。')
        if len(set(self.scan_values)) != len(self.scan_values):raise ValueError('扫描节点须互异。')
        if any(not self.minimum <= v <= self.maximum for v in self.scan_values):raise ValueError('扫描节点超出变量边界。')
        return self


class NscEfficiency(Request):
    kind: Literal['nsc_efficiency']
    sources: Annotated[list[PositiveIndex], Field(min_length=1, max_length=20)]
    detectors: Annotated[list[NscRoi], Field(min_length=1, max_length=10)]
    mode: Literal['evaluate','scan','optimize'] = 'evaluate'
    variables: Annotated[list[NscDesignVariable], Field(max_length=10)] = Field(default_factory=list)
    ranking: Literal['efficiency','cv','target_error'] = 'efficiency'
    rays_per_source: Annotated[int, Field(strict=True, ge=1, le=1000000)] = 10000
    verification_rays_per_source: Annotated[int, Field(strict=True, ge=1, le=4000000)] = 40000
    random_seed: Annotated[int, Field(strict=True, ge=0, le=2147483647)] = 42
    verification_seeds: Annotated[list[Annotated[int, Field(strict=True, ge=0, le=2147483647)]], Field(min_length=1,max_length=5)] = Field(default_factory=lambda:[42,43,44])
    use_polarization: bool = False
    split_rays: bool = False
    scatter_rays: bool = False
    hotspot_factor: Annotated[FiniteFloat, Field(gt=1)] = 2
    algorithm: Literal['DampedLeastSquares','OrthogonalDescent'] = 'DampedLeastSquares'
    cycles: Literal['Fixed_1_Cycle','Fixed_5_Cycles','Fixed_10_Cycles','Fixed_50_Cycles'] = 'Fixed_10_Cycles'
    budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=3600)] = 120
    save_best: bool = True

    @model_validator(mode='after')
    def contract(self):
        if len(set(self.sources)) != len(self.sources):raise ValueError('光源编号重复。')
        if len({v.detector for v in self.detectors}) != len(self.detectors):raise ValueError('每个探测器仅定义一个ROI。')
        if len({(v.object,v.cell) for v in self.variables}) != len(self.variables):raise ValueError('变量重复。')
        if len(set(self.verification_seeds)) != len(self.verification_seeds):raise ValueError('复算种子重复。')
        if self.verification_rays_per_source < self.rays_per_source:raise ValueError('复算光线数须不小于基础采样。')
        if sum(v.width*v.height for v in self.detectors)>4096:raise ValueError('ROI总像素数上限4096。')
        if self.mode=='evaluate' and self.variables:raise ValueError('evaluate模式不接受变量。')
        if self.mode!='evaluate' and not self.variables:raise ValueError('scan/optimize需要变量。')
        if self.mode=='scan' and (len(self.variables)>3 or any(not v.scan_values for v in self.variables) or math.prod(len(v.scan_values) for v in self.variables)>125):
            raise ValueError('scan支持1—3轴、每轴显式节点、最多125个候选。')
        if self.mode!='scan' and any(v.scan_values for v in self.variables):raise ValueError('scan_values仅适用于scan。')
        if self.mode=='optimize' or self.ranking=='target_error':
            if any(v.target_power is None for v in self.detectors):raise ValueError('原生优化/目标误差排名需要每个ROI的target_power。')
        if self.mode=='optimize' and self.ranking!='target_error':raise ValueError('optimize使用target_error排名。')
        return self


def roi_statistics(values, source_power, hotspot_factor=2):
    flat=[v for row in values for v in row]
    valid=[float(v) for v in flat if v is not None and math.isfinite(v) and v>=0]
    invalid=len(flat)-len(valid);power=sum(valid);mean=power/len(valid) if valid else None
    std=math.sqrt(sum((v-mean)**2 for v in valid)/len(valid)) if valid else None
    cv=std/mean if mean and not invalid else None
    return dict(power=power,efficiency=power/source_power if source_power>0 and not invalid else None,
        mean_pixel_flux=mean,standard_deviation=std,cv=cv,cv_definition='population std/mean over all ROI pixels including zero; invalid pixels invalidate CV',
        pixel_count=len(flat),invalid_count=invalid,zero_count=sum(v==0 for v in valid),
        peak_to_mean=max(valid)/mean if mean else None,hotspot_count=sum(v>hotspot_factor*mean for v in valid) if mean else 0,
        hotspot_factor=hotspot_factor,state='invalid_pixels' if invalid else 'dark' if not power else 'valid')


def score(result,q):
    rows=result['detectors']
    if any(r['invalid_count'] for r in rows):return None
    if q.ranking=='efficiency':
        values=[r['efficiency'] for r in rows]
        return -sum(values)/len(values) if all(v is not None for v in values) else None
    if q.ranking=='cv':
        return sum(r['cv'] for r in rows)/len(rows) if all(r['cv'] is not None for r in rows) else None
    return result['target_error']


def variable_cell(b,system,v):
    name='Par3' if v.cell=='Power' else v.cell
    return system.NCE.GetObjectAt(v.object).GetObjectCell(b.native.enum(b.native.api.Editors.NCE.ObjectColumn,name))


def prepare(b,system,q):
    # Clear only Variable solves in the owned copy; other solve definitions stay intact.
    for i in range(1,system.NCE.NumberOfObjects+1):
        for name in b.native.enum_names(b.native.api.Editors.NCE.ObjectColumn):
            c=system.NCE.GetObjectAt(i).GetObjectCell(b.native.enum(b.native.api.Editors.NCE.ObjectColumn,name))
            if c is not None and c.IsActive and str(c.Solve)=='Variable':b._set_variable_mode(c,False)
    found=[]
    for i in range(1,system.NCE.NumberOfObjects+1):
        row=system.NCE.GetObjectAt(i)
        if not str(row.Type).startswith('Source'):continue
        data=unwrap(row.ObjectData)
        if not hasattr(data,'NumberOfAnalysisRays'):
            raise ZemaxError('UNSUPPORTED_SOURCE','光源缺少正式分析光线数属性。',object=i,type=str(row.Type))
        data.NumberOfAnalysisRays=q.rays_per_source if i in q.sources else 0
        check_setting_value('NumberOfAnalysisRays',q.rays_per_source if i in q.sources else 0,int(data.NumberOfAnalysisRays))
        if i in q.sources:
            if not hasattr(data,'Power'):
                raise ZemaxError('UNSUPPORTED_SOURCE','光源需要正式Power属性。',object=i,type=str(row.Type))
            if hasattr(data,'RandomSeedCell'):
                b._write_cell(data.RandomSeedCell,q.random_seed or 1)
                check_setting_value('RandomSeedCell',q.random_seed or 1,int(data.RandomSeedCell.IntegerValue))
            found.append(i)
    if set(found)!=set(q.sources):raise ZemaxError('INVALID_SOURCE','请求编号未对应可追迹光源。',sources=q.sources,found=found)
    total=sum(float(unwrap(system.NCE.GetObjectAt(i).ObjectData).Power) for i in found)
    if not math.isfinite(total) or total<=0:raise ZemaxError('INVALID_SOURCE_POWER','总输入源功率须为正有限值。')
    for roi in q.detectors:
        if roi.detector>system.NCE.NumberOfObjects:raise ZemaxError('INDEX_OUT_OF_RANGE','探测器编号越界。',detector=roi.detector)
        row=system.NCE.GetObjectAt(roi.detector);d=unwrap(row.ObjectData)
        if str(row.Type)!='DetectorRectangle' or int(d.DataType)!=0:raise ZemaxError('UNSUPPORTED_DETECTOR_DATA','需要空间矩形非相干探测器。',detector=roi.detector,type=str(row.Type))
        if roi.x_start+roi.width>int(d.NumberXPixels) or roi.y_start+roi.height>int(d.NumberYPixels):
            raise ZemaxError('INDEX_OUT_OF_RANGE','ROI须完整位于探测器内。',detector=roi.detector)
    for v in q.variables:
        if v.object>system.NCE.NumberOfObjects:raise ZemaxError('INDEX_OUT_OF_RANGE','变量对象越界。',object=v.object)
        if v.cell=='Power' and v.object not in q.sources:raise ZemaxError('INVALID_VARIABLE','Power变量须属于选定光源。')
        cell=variable_cell(b,system,v);b._guard_nsc_cell(cell)
        actual=float(cell.DoubleValue)
        if not v.minimum<=actual<=v.maximum:raise ZemaxError('INVALID_ARGUMENT','起始变量超出边界。',object=v.object,cell=v.cell,actual=actual)
    units=system.SystemData.Units
    if str(units.SourceUnits)!='Watts' or str(units.SourceUnitPrefix)!='None':
        raise ZemaxError('UNSUPPORTED_UNITS','效率工作流采用无前缀Watts源功率。',units=str(units.SourceUnits),prefix=str(units.SourceUnitPrefix))
    return dict(sources=found,source_power_unit='W',lens_unit=str(units.LensUnits),optimization_random_seed=q.random_seed or 1,
        optimization_seed_definition='RandomSeedCell uses request seed where exposed; other sources use native NSTR default, checked by two identical MFE evaluations; explicit trace uses tool.SetRandomSeed',
        original_variables_retained_in_source=True)


def metrics(b,system,q):
    sources=[dict(object=i,power=float(unwrap(system.NCE.GetObjectAt(i).ObjectData).Power)) for i in q.sources]
    power=sum(v['power'] for v in sources);rows=[];grids=[];loss=0;weight=0
    for k,roi in enumerate(q.detectors):
        d=unwrap(system.NCE.GetObjectAt(roi.detector).ObjectData);nx,ny=int(d.NumberXPixels),int(d.NumberYPixels)
        values=[[checked_scalar(system.NCE.GetDetectorData(roi.detector,1+x+nx*y,0,0.),detector=roi.detector,pixel=1+x+nx*y)
                 for x in range(roi.x_start,roi.x_start+roi.width)] for y in range(roi.y_start,roi.y_start+roi.height)]
        stats=roi_statistics(values,power,q.hotspot_factor)
        xa=axis('X',float(d.XHalfWidth),nx,str(system.SystemData.Units.LensUnits))
        ya=axis('Y',float(d.YHalfWidth),ny,str(system.SystemData.Units.LensUnits))
        dx,dy=2*float(d.XHalfWidth)/nx,2*float(d.YHalfWidth)/ny
        stats.update(detector=roi.detector,roi=roi.model_dump(),pixel_area_lens_units_squared=dx*dy,
            area_lens_units_squared=dx*dy*roi.width*roi.height,
            mean_irradiance_w_per_lens_unit_squared=stats['mean_pixel_flux']/(dx*dy) if stats['mean_pixel_flux'] is not None else None)
        rows.append(stats)
        grids.append(dict(grid=k,description=f'Detector {roi.detector} ROI flux',nx=roi.width,ny=roi.height,
            values=values,x=xa['centers'][roi.x_start:roi.x_start+roi.width],y=ya['centers'][roi.y_start:roi.y_start+roi.height],
            dx=dx,dy=dy,min_x=xa['centers'][roi.x_start],min_y=ya['centers'][roi.y_start],
            x_label='local X',y_label='local Y',x_unit=str(system.SystemData.Units.LensUnits),y_unit=str(system.SystemData.Units.LensUnits),z_unit='W',
            invalid_count=stats['invalid_count'],array_order='values[y][x]; native pixel=1+x+nx*y'))
        if roi.target_power is not None:
            loss+=roi.power_weight*(stats['power']-roi.target_power)**2;weight+=roi.power_weight
            target=roi.target_power/(roi.width*roi.height)
            loss+=roi.uniformity_weight*sum((v-target)**2 for row in values for v in row if v is not None)
            weight+=roi.uniformity_weight*roi.width*roi.height
    return dict(sources=sources,source_power=power,detectors=rows,grids=grids,target_error=loss/weight if weight else None,
        double_count_warning=len(rows)>1,aggregation='each detector efficiency uses the same input power; mean efficiency ranks candidates; detectors may intercept the same ray')


def build_merit(b,system,q):
    from .coating_optimization import operand
    for index in q.sources:
        data=unwrap(system.NCE.GetObjectAt(index).ObjectData)
        if hasattr(data,'RandomSeedCell'):
            b._write_cell(data.RandomSeedCell,q.random_seed or 1)
            check_setting_value('RandomSeedCell',q.random_seed or 1,int(data.RandomSeedCell.IntegerValue))
    mfe=system.MFE;mfe.RemoveOperandsAt(1,int(mfe.NumberOfOperands))
    operand(b,mfe,'NSDD',{3:0,4:0,5:0})
    operand(b,mfe,'NSTR',{3:0,4:int(q.split_rays),5:int(q.scatter_rays),6:int(q.use_polarization or q.split_rays),7:0.})
    mapping=[]
    for roi in q.detectors:
        d=unwrap(system.NCE.GetObjectAt(roi.detector).ObjectData);nx=int(d.NumberXPixels);indices=[]
        for y in range(roi.y_start,roi.y_start+roi.height):
            for x in range(roi.x_start,roi.x_start+roi.width):
                indices.append(operand(b,mfe,'NSDD',{3:roi.detector,4:1+x+nx*y,5:0},roi.target_power/(roi.width*roi.height),roi.uniformity_weight))
        total=operand(b,mfe,'OSUM',{2:indices[0],3:indices[-1]},roi.target_power,roi.power_weight)
        mapping.append(dict(detector=roi.detector,pixel_operands=indices,sum_operand=total))
    bound_codes={'XPosition':('NPXG','NPXL'),'YPosition':('NPYG','NPYL'),'ZPosition':('NPZG','NPZL'),
        'TiltX':('NTXG','NTXL'),'TiltY':('NTYG','NTYL'),'TiltZ':('NTZG','NTZL'),'Power':('NPGT','NPLT')}
    for v in q.variables:
        params={3:v.object,4:3 if v.cell=='Power' else 0}
        for code,target in zip(bound_codes[v.cell],(v.minimum,v.maximum)):operand(b,mfe,code,params,target,10000)
        b._set_variable_mode(variable_cell(b,system,v),True)
    return mapping


def run_nsc_efficiency(b,q):
    b._require_nsc();b._require_work()
    if q.mode=='optimize' and q.ranking!='target_error':
        raise ZemaxError('INVALID_ARGUMENT','optimize使用target_error排名，与原生MFE目标一致。')
    def flow(task):
        system=None;error=None;deadline=time.monotonic()+q.budget_seconds
        def remaining():
            seconds=deadline-time.monotonic()
            if seconds<=0:raise ZemaxError('BUDGET_EXCEEDED','NSC工作流总时间预算已用尽。')
            return seconds
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],units=dict(power='W',efficiency='dimensionless',cv='dimensionless'),
            computation_method='native NSC trace + pixel statistics; optional native NSTR/NSDD/OSUM optimization')
        task['restoration']=dict(required=False,restored=True,reason='source model and source detector buffers are read-only; all work uses an owned copy')
        try:
            b._cancel_boundary(task);system=b.system.CopySystem()
            if system is None:raise ZemaxError('COPY_FAILED','无法创建NSC工作副本。')
            task['payload']['actual_settings']=prepare(b,system,q)
            initial_values=[float(variable_cell(b,system,v).DoubleValue) for v in q.variables]
            def apply(values):
                for v,value in zip(q.variables,values):
                    c=variable_cell(b,system,v);b._write_cell(c,value);check_setting_value(v.cell,value,float(c.DoubleValue))
                system.UpdateStatus()
                for v,value in zip(q.variables,values):check_setting_value(v.cell,value,float(variable_cell(b,system,v).DoubleValue))
            def trace(rays,seed):
                for i in q.sources:
                    d=unwrap(system.NCE.GetObjectAt(i).ObjectData);d.NumberOfAnalysisRays=rays
                    check_setting_value('NumberOfAnalysisRays',rays,int(d.NumberOfAnalysisRays))
                    if hasattr(d,'RandomSeedCell'):
                        b._write_cell(d.RandomSeedCell,0);check_setting_value('RandomSeedCell',0,int(d.RandomSeedCell.IntegerValue))
                tool=system.Tools.OpenNSCRayTrace()
                try:
                    status=str(tool.ClearDetectors(0))
                    if status!='Success':raise ZemaxError('DETECTOR_CLEAR_FAILED','副本探测器清空失败。',status=status)
                    tool.UsePolarization=q.use_polarization or q.split_rays;tool.SplitNSCRays=q.split_rays;tool.ScatterNSCRays=q.scatter_rays
                    tool.IgnoreErrors=False;tool.NumberOfCores=1;tool.SaveRays=False;tool.SetRandomSeed(seed)
                    for name,value in dict(UsePolarization=q.use_polarization or q.split_rays,SplitNSCRays=q.split_rays,ScatterNSCRays=q.scatter_rays,IgnoreErrors=False,NumberOfCores=1,SaveRays=False).items():check_setting_value(name,value,getattr(tool,name))
                    def collect(child):
                        if not tool.Succeeded:raise ZemaxError('NSC_TRACE_FAILED',str(tool.ErrorMessage))
                        energy=float(tool.GetTotalRayEnergy());dead=float(tool.DeadRayErrors)
                        if not math.isfinite(energy) or not math.isfinite(dead) or dead!=0:raise ZemaxError('NSC_TRACE_ERRORS','副本追迹出现错误光线。',dead_ray_errors=dead)
                        if not b._close_task_native(child):raise ZemaxError('CLEANUP_FAILED','副本追迹工具关闭失败。')
                        return metrics(b,system,q)|dict(trace=dict(rays_per_source=rays,seed=seed,energy=energy,dead_ray_errors=dead))
                    return b._start_task('nsc_efficiency_trace',tool,dict(rays_per_source=rays,random_seed=seed,number_of_cores=1),collector=collect,budget_seconds=remaining())
                except Exception:
                    tool.Close();raise
            baseline=yield from b._child_job(task,lambda _:trace(q.rays_per_source,q.random_seed),None)
            task['payload']['baseline']=baseline
            candidates=[dict(index=0,values=initial_values,result=baseline,score=score(baseline,q),source='baseline')]
            if q.mode=='scan':
                for values in itertools.product(*(v.scan_values for v in q.variables)):
                    b._cancel_boundary(task);apply(values)
                    result=yield from b._child_job(task,lambda _:trace(q.rays_per_source,q.random_seed),None)
                    candidates.append(dict(index=len(candidates),values=list(values),result=result,score=score(result,q),source='scan'))
            elif q.mode=='optimize':
                mapping=build_merit(b,system,q);native_before=float(system.MFE.CalculateMeritFunction())
                task['payload']['native_mapping']=mapping;task['payload']['native_merit_before']=native_before
                first=[float(system.MFE.GetOperandAt(i).Value) for m in mapping for i in m['pixel_operands']]
                system.MFE.CalculateMeritFunction()
                second=[float(system.MFE.GetOperandAt(i).Value) for m in mapping for i in m['pixel_operands']]
                difference=max((abs(a-c) for a,c in zip(first,second)),default=0)
                task['payload']['native_reproducibility']=dict(max_absolute_difference=difference,first=first,second=second)
                if any(not math.isfinite(v) for v in first+second) or difference>1e-12:
                    raise ZemaxError('UNSTABLE_NSC_OBJECTIVE','固定设置下NSTR目标未能重现。',max_absolute_difference=difference)
                def start(_):
                    tool=system.Tools.OpenLocalOptimization()
                    try:
                        b.native.set_enum(tool,'Algorithm',q.algorithm);b.native.set_enum(tool,'Cycles',q.cycles);tool.NumberOfCores=1
                        check_setting_value('Variables',len(q.variables),int(tool.Variables))
                        def collect(child):
                            if not tool.Succeeded:raise ZemaxError('NATIVE_OPTIMIZATION_FAILED',str(tool.ErrorMessage))
                            return dict(succeeded=True,current_merit=float(tool.CurrentMeritFunction),values=[float(variable_cell(b,system,v).DoubleValue) for v in q.variables])
                        return b._start_task('nsc_native_optimization',tool,dict(algorithm=str(tool.Algorithm),cycles=str(tool.Cycles),variables=int(tool.Variables),number_of_cores=1),collector=collect,budget_seconds=remaining())
                    except Exception:tool.Close();raise
                optimized=yield from b._child_job(task,start,None)
                task['payload']['native_optimization']=optimized
                if any(not math.isfinite(x) or not v.minimum<=x<=v.maximum for v,x in zip(q.variables,optimized['values'])):
                    raise ZemaxError('NSC_BOUNDS_VIOLATED','原生优化候选超出请求边界。',values=optimized['values'])
                result=yield from b._child_job(task,lambda _:trace(q.rays_per_source,q.random_seed),None)
                candidates.append(dict(index=1,values=optimized['values'],result=result,score=score(result,q),source='native_optimization'))
            valid=[v for v in candidates if v['score'] is not None and math.isfinite(v['score'])]
            if not valid:raise ZemaxError('NO_VALID_CANDIDATE','候选无有效排名指标。')
            best=min(valid,key=lambda v:v['score']);apply(best['values'])
            verified=[]
            for seed in q.verification_seeds:
                result=yield from b._child_job(task,lambda _:trace(q.verification_rays_per_source,seed),None)
                verified.append(result)
            task['payload']['verification']=verified;task['payload']['candidates']=candidates
            task['payload']['grids']=verified[0]['grids']
            task['summary']=dict(mode=q.mode,candidate_count=len(candidates),best_index=best['index'],best_values=best['values'],
                ranking=q.ranking,best_score=best['score'],baseline_score=candidates[0]['score'],verification_rays_per_source=q.verification_rays_per_source,
                detectors=verified[0]['detectors'],source_power=verified[0]['source_power'])
            task['payload']['repeatability']=[dict(detector=roi.detector,power_min=min(r['detectors'][i]['power'] for r in verified),
                power_max=max(r['detectors'][i]['power'] for r in verified),seeds=q.verification_seeds) for i,roi in enumerate(q.detectors)]
            for rank,c in enumerate(sorted(valid,key=lambda v:v['score'])):
                task['rows'].append(dict(rank=rank,index=c['index'],source=c['source'],values=c['values'],score=c['score'],detectors=c['result']['detectors']))
            task['payload']['series']=[dict(series=0,description='NSC candidate score (lower is better)',x_label='candidate index',x_unit='index',y_unit=q.ranking,
                labels=['score'],x=[c['index'] for c in valid],y=[[c['score']] for c in valid])]
            b._cancel_boundary(task)
            if q.save_best:
                path=Path(b.directory)/(task['task_id']+'_best.zos');system.SaveAs(str(path))
                task['summary']['best_model']=str(path);task['payload']['artifacts']=[dict(kind='candidate_model',path=str(path))]
        except Exception as exc:error=exc;raise
        finally:
            closed=False;cleanup=[]
            if system is not None:
                try:
                    if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
                    closed=True
                except Exception as exc:cleanup.append(str(exc));b.requires_reconnect=True
            task['payload']['resources']=dict(copy_closed=closed,cleanup_errors=cleanup)
            if cleanup:raise ZemaxError('CLEANUP_FAILED','NSC工作副本关闭失败。',cleanup_errors=cleanup,operation_error=b._evaluation_error(error) if error else None)
    return b._composite(q.kind,q.model_dump(),flow,require_sequential=False)
