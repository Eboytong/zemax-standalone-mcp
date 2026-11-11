"""Fixed-stack coating optimization on an owned native multi-configuration bench."""
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .coating_models import CoatingLayerRange, CoatingRta, CoatingRtaCondition
from .coatings import CoatingsMixin, get_layer, layer_data, readable_layers
from .configurations import write_configuration_cell
from .detectors import check_setting_value
from .errors import ZemaxError
from .schema import FiniteFloat, PositiveIndex, Request


class CoatingThicknessBound(Request):
    layer: PositiveIndex
    minimum: Annotated[FiniteFloat, Field(gt=0,le=10)]
    maximum: Annotated[FiniteFloat, Field(gt=0,le=10)]

    @model_validator(mode='after')
    def interval(self):
        if self.minimum>=self.maximum:
            raise ValueError('膜厚倍率下界必须小于上界，范围为(0,10]。')
        return self


class CoatingObjective(CoatingRtaCondition):
    metric: Literal['reflection','transmission','absorption'] = 'reflection'
    polarization: Literal['s','p'] = 's'
    target: Annotated[FiniteFloat,Field(ge=0,le=1)] = 0
    weight: Annotated[FiniteFloat,Field(gt=0,le=1e6)] = 1


class CoatingOptimization(Request):
    kind: Literal['coating_optimization']
    surface: PositiveIndex
    variables: Annotated[list[CoatingThicknessBound],Field(min_length=1,max_length=30)]
    objectives: Annotated[list[CoatingObjective],Field(min_length=1,max_length=30)]
    algorithm: Literal['DampedLeastSquares','OrthogonalDescent'] = 'DampedLeastSquares'
    cycles: Literal['Fixed_1_Cycle','Fixed_5_Cycles','Fixed_10_Cycles','Fixed_50_Cycles'] = 'Fixed_10_Cycles'
    budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] = 120
    constraint_weight: Annotated[FiniteFloat,Field(ge=1,le=1e9)] = 10000
    save_best: bool = True

    @model_validator(mode='after')
    def unique_layers(self):
        if len({v.layer for v in self.variables})!=len(self.variables):
            raise ValueError('可变膜层编号不得重复。')
        return self


DATA = {'reflection':-1,'transmission':-2,'absorption':-3}


def objective_value(samples, objectives):
    if len(samples)!=len(objectives):
        raise ZemaxError('INVALID_METRIC','镀膜结果数与目标数不符。')
    values = [sample[obj.metric][obj.polarization] for sample,obj in zip(samples,objectives)]
    if len(values)!=len(objectives) or any(not math.isfinite(v) for v in values):
        raise ZemaxError('INVALID_METRIC','镀膜目标包含缺失或非有限结果。')
    loss = sum(obj.weight*(value-obj.target)**2 for value,obj in zip(values,objectives))/sum(o.weight for o in objectives)
    return dict(weighted_mean_squared_error=loss,weighted_rms_error=math.sqrt(loss),values=values)


def boundary_report(layers, bounds):
    lookup={v['layer']:v['thickness_multiplier'] for v in layers}
    return [dict(layer=v.layer,minimum=v.minimum,maximum=v.maximum,actual=lookup[v.layer],
                 satisfied=v.minimum<=lookup[v.layer]<=v.maximum) for v in bounds]


class BenchOwner(CoatingsMixin):
    """Borrow an owned system for the existing row-owned direct query adapter."""
    def __init__(self,backend,system):
        self.backend=backend;self.system=system;self.native=backend.native;self.version=backend.version
        self.requires_reconnect=False
    def _require_sequential(self):pass
    def _row(self,index):return self.system.LDE.GetSurfaceAt(index)


def set_layers(system,surface,states,variable_layers=()):
    data=system.LDE.GetSurfaceAt(surface).CoatingData
    data.UseLayerMultiplierAndOffsets=True
    check_setting_value('UseLayerMultiplierAndOffsets',True,bool(data.UseLayerMultiplierAndOffsets))
    for state in states:
        value=get_layer(data,state['layer'])
        for name,key in [('Thickness','thickness_multiplier'),('Index','index_offset'),('Extinction','extinction_offset')]:
            getattr(value,'Set'+name+'StatusFixed')()
            setattr(value,{'Thickness':'ThicknessMultiplier','Index':'IndexOffset','Extinction':'ExtinctionOffset'}[name],state[key])
        if state['layer'] in variable_layers:value.SetThicknessStatusVariable()
        if not data.SetLayerSettings(state['layer'],value):
            raise ZemaxError('SETTING_REJECTED','优化副本拒绝膜层设置。',layer=state['layer'])
        actual=layer_data(get_layer(data,state['layer']))
        for key in ('thickness_multiplier','index_offset','extinction_offset'):
            check_setting_value(key,state[key],actual[key])
        check_setting_value('ThicknessStatus','Variable' if state['layer'] in variable_layers else 'Fixed',actual['thickness_status']['mode'])


def operand(backend,mfe,code,parameters=None,target=0,weight=0):
    row=mfe.AddOperand()
    row.ChangeType(backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,code))
    check_setting_value('OperandType',code,str(row.Type))
    for column,value in (parameters or {}).items():backend._write_cell(row.GetCellAt(column),value)
    if code!='CONF':
        row.Target=target;row.Weight=weight
        check_setting_value('Target',target,float(row.Target));check_setting_value('Weight',weight,float(row.Weight))
    return int(row.OperandNumber)


def build_bench(b,bench,q,baseline,conditions):
    source=b.system;bench.New(False)
    media=[str(source.LDE.GetSurfaceAt(q.surface-i).Material) for i in (1,0)]
    if sum(not v for v in media)!=1 or any(v.upper() in ('MIRROR','MODEL') for v in media):
        raise ZemaxError('UNSUPPORTED_COATING_MEDIA','本优化合同采用空气与目录玻璃的单界面膜系。',media=media)
    bench.SystemData.Units.LensUnits=source.SystemData.Units.LensUnits
    catalogs=bench.SystemData.MaterialCatalogs
    for name in source.SystemData.MaterialCatalogs.GetCatalogsInUse():catalogs.AddCatalog(str(name))
    bench.SystemData.Files.CoatingFile=str(source.SystemData.Files.CoatingFile)
    for key in ('Temperature','Pressure','AdjustIndexDataToEnvironment'):
        if hasattr(source.SystemData.Environment,key):
            value=getattr(source.SystemData.Environment,key);setattr(bench.SystemData.Environment,key,value)
    bench.LDE.InsertNewSurfaceAt(1)
    front=bench.LDE.GetSurfaceAt(1);front.Thickness=1;front.SemiDiameter=10
    front.Coating=str(source.LDE.GetSurfaceAt(q.surface).Coating)
    bench.LDE.GetSurfaceAt(0).Thickness=float('inf')
    bench.SystemData.Aperture.ApertureValue=.1
    set_layers(bench,1,baseline,[v.layer for v in q.variables])
    waves=bench.SystemData.Wavelengths
    while int(waves.NumberOfWavelengths)>1:waves.RemoveWavelength(int(waves.NumberOfWavelengths))
    primary=next(float(source.SystemData.Wavelengths.GetWavelength(i).Wavelength)
                 for i in range(1,int(source.SystemData.Wavelengths.NumberOfWavelengths)+1)
                 if source.SystemData.Wavelengths.GetWavelength(i).IsPrimary)
    waves.GetWavelength(1).Wavelength=primary;waves.GetWavelength(1).MakePrimary()
    wave_numbers=[]
    for c in conditions:
        number=next((i for i in range(1,int(waves.NumberOfWavelengths)+1)
                     if abs(float(waves.GetWavelength(i).Wavelength)-c['wavelength_um'])<1e-12),None)
        if number is None:
            waves.AddWavelength(c['wavelength_um'],1);number=int(waves.NumberOfWavelengths)
        wave_numbers.append(number)
    fields=bench.SystemData.Fields;fields.SetFieldType(b.native.api.SystemData.FieldType.Angle)
    fields.GetField(1).X=0;fields.GetField(1).Y=0
    m=bench.MCE
    for _ in range(1,len(conditions)):
        if not m.AddConfiguration(False):raise ZemaxError('SETTING_REJECTED','镀膜优化副本无法增加配置。')
    before=str(source.LDE.GetSurfaceAt(q.surface-1).Material)
    after=str(source.LDE.GetSurfaceAt(q.surface).Material)
    mappings=[]
    for code,index,values in [('GLSS',0,[before if c['direction']=='inward' else after for c in conditions]),
                              ('GLSS',1,[after if c['direction']=='inward' else before for c in conditions]),
                              ('YFIE',1,[c['angle_deg'] for c in conditions])]:
        row=m.AddOperand();row.ChangeType(b.native.enum(b.native.api.Editors.MCE.MultiConfigOperandType,code));row.Param1=index
        for config,value in enumerate(values,1):write_configuration_cell(b,row.GetOperandCell(config),value)
        mappings.append(dict(type=code,parameter=index,requested_values=values,
            actual_values=[b._cell_value(row.GetOperandCell(c)) for c in range(1,len(values)+1)]))
    mfe=bench.MFE;mfe.RemoveOperandsAt(1,int(mfe.NumberOfOperands))
    indices=[];performance_indices=[]
    for config,(obj,wave) in enumerate(zip(q.objectives,wave_numbers),1):
        operand(b,mfe,'CONF',{2:config})
        channels={}
        for metric,base in DATA.items():
            for pol,sign in [('s',1),('p',-1)]:
                channels[metric+'_'+pol]=operand(b,mfe,'CODA',{2:1,3:wave,4:1,5:base*sign,6:0.,7:0.})
        performance_indices.append(channels)
        datum=DATA[obj.metric]*(1 if obj.polarization=='s' else -1)
        indices.append(operand(b,mfe,'CODA',{2:1,3:wave,4:1,5:datum,6:0.,7:0.},obj.target,obj.weight))
    for v in q.variables:
        operand(b,mfe,'CMGT',{2:1,3:v.layer},v.minimum,q.constraint_weight)
        operand(b,mfe,'CMLT',{2:1,3:v.layer},v.maximum,q.constraint_weight)
    return dict(configurations=mappings,wavelength_numbers=wave_numbers,primary_wavelength_um=primary,
                target_operands=indices,performance_operands=performance_indices,
                variable_count=len(q.variables),source='native GLSS/YFIE + CONF/CODA + CMGT/CMLT')


def bench_performance(bench,mapping,original):
    bench.MFE.CalculateMeritFunction()
    samples=[]
    for sample,indices in zip(original['samples'],mapping['performance_operands']):
        result={k:v for k,v in sample.items() if k not in (*DATA,'energy_residual')}
        for metric in DATA:
            s,p=(float(bench.MFE.GetOperandAt(indices[metric+'_'+pol]).Value) for pol in ('s','p'))
            if not math.isfinite(s) or not math.isfinite(p):
                raise ZemaxError('INVALID_METRIC','CODA返回非有限镀膜系数。',metric=metric,s=s,p=p)
            result[metric]=dict(s=s,p=p,unpolarized=(s+p)/2)
        result['energy_residual']={pol:1-sum(result[key][pol] for key in DATA) for pol in ('s','p','unpolarized')}
        samples.append(result)
    return original|dict(samples=samples,source='native MFE CODA, global primary reference wavelength for relative layers')


def direct_comparison(raw,physical):
    differences=[dict(condition=i,metric=metric,polarization=pol,direct=a[metric][pol],physical=c[metric][pol],
                     difference=a[metric][pol]-c[metric][pol])
                 for i,(a,c) in enumerate(zip(raw['samples'],physical['samples']))
                 for metric in DATA for pol in ('s','p')]
    error=max((abs(v['difference']) for v in differences),default=0)
    return dict(max_absolute_difference=error,state='matching' if error<=1e-8 else 'native_reference_difference',
        definition='GetCoatingPerformance uses query wavelength for wave-relative layers; CODA uses the system primary wavelength',
        differences=differences)


def compare_objectives(bench,indices,expected):
    native_merit=float(bench.MFE.CalculateMeritFunction())
    values=[float(bench.MFE.GetOperandAt(i).Value) for i in indices]
    errors=[abs(a-b) for a,b in zip(values,expected)]
    if len(values)!=len(expected) or any(not math.isfinite(a) or e>1e-8+1e-6*abs(b)
                                       for a,b,e in zip(values,expected,errors)):
        raise ZemaxError('COATING_OBJECTIVE_MAPPING_FAILED','CODA多配置目标与指定曲面双向查询不符。',
                         native_values=values,direct_values=expected,absolute_errors=errors)
    return dict(native_merit=native_merit,native_values=values,direct_values=expected,max_absolute_error=max(errors,default=0))


def close_system(b,system):
    try:
        if system.Close(False) is False:raise RuntimeError('Close(False) returned false')
    except Exception as exc:
        b.requires_reconnect=True
        raise ZemaxError('CLEANUP_FAILED','镀膜优化副本关闭失败。',native_error=str(exc)) from exc


def run_coating_optimization(b,q):
    b._require_sequential();b._require_work()
    baseline=b.get_coating_layers(CoatingLayerRange(surface=q.surface,count=1000))
    if not baseline['total'] or baseline['total']>1000:
        raise ZemaxError('INVALID_ARGUMENT','需要具有1—1000层的固定膜系。',layers=baseline['total'])
    states=baseline['rows'];lookup={r['layer']:r for r in states}
    for v in q.variables:
        if v.layer not in lookup:raise ZemaxError('INDEX_OUT_OF_RANGE','可变膜层编号越界。',layer=v.layer)
        row=lookup[v.layer]
        if row['thickness_status']['mode']=='Pickup':raise ZemaxError('SOLVE_PROTECTED','可变层仍有厚度拾取。',layer=v.layer)
        if not v.minimum<=row['thickness_multiplier']<=v.maximum:
            raise ZemaxError('INVALID_ARGUMENT','起始膜厚倍率须处于请求边界内。',layer=v.layer)
    if not baseline['use_layer_multiplier_and_offsets']:
        raise ZemaxError('INACTIVE_SETTING','请先启用镀膜UseLayerMultiplierAndOffsets。')
    for state in states:
        for key in ('thickness_status','index_status','extinction_status'):
            if state.get(key,{}).get('mode')=='Pickup':
                raise ZemaxError('SOLVE_PROTECTED','固定膜系优化需要先解除层间拾取。',layer=state['layer'],property=key)
    conditions=[CoatingRtaCondition.model_validate(o.model_dump(include=set(CoatingRtaCondition.model_fields),exclude_none=True)) for o in q.objectives]
    direct_request=CoatingRta(surface=q.surface,conditions=conditions)
    initial=b.get_coating_rta(direct_request)
    initial_score=objective_value(initial['samples'],q.objectives)

    def flow(task):
        bench=None;candidate=None;error=None
        initial_score=objective_value(initial['samples'],q.objectives)
        task['baseline']=dict(context=b.context(),layers=baseline,performance=initial,objective=initial_score)
        task['restoration']=dict(required=False,restored=True,reason='all optimization writes use owned copies')
        task['payload']=dict(analysis_kind=q.kind,series=[],grids=[],computation_method='native multi-configuration CODA local optimization',
            units=dict(wavelength='micrometers',angle='degrees',thickness_multiplier='dimensionless; catalog thickness times multiplier'),
            objective_definition='sum(weight*(native_coefficient-target)^2)/sum(weight)',
            constraint_method='native CMGT/CMLT penalties; final multipliers checked against exact request bounds')
        try:
            b._cancel_boundary(task)
            bench=b.system.CopySystem()
            if bench is None:raise ZemaxError('COPY_FAILED','无法创建镀膜优化副本。')
            mapping=build_bench(b,bench,q,states,initial['samples'])
            physical_initial=bench_performance(bench,mapping,initial)
            initial_score=objective_value(physical_initial['samples'],q.objectives)
            task['baseline'].update(performance=physical_initial,objective=initial_score)
            task['payload']['direct_before']=initial
            task['payload']['direct_comparison_before']=direct_comparison(initial,physical_initial)
            task['payload']['native_mapping']=mapping
            task['payload']['mapping_before']=compare_objectives(bench,mapping['target_operands'],initial_score['values'])
            yield
            b._cancel_boundary(task)
            def start(_):
                tool=bench.Tools.OpenLocalOptimization()
                try:
                    b.native.set_enum(tool,'Algorithm',q.algorithm);b.native.set_enum(tool,'Cycles',q.cycles);tool.NumberOfCores=1
                    check_setting_value('Variables',len(q.variables),int(tool.Variables))
                    def collect(child):
                        if not tool.Succeeded:raise ZemaxError('NATIVE_OPTIMIZATION_FAILED',str(tool.ErrorMessage))
                        return dict(native_terminal=dict(succeeded=bool(tool.Succeeded),status=str(tool.Status),
                                    error=str(tool.ErrorMessage),current_merit=float(tool.CurrentMeritFunction)),
                                    layers=[layer_data(get_layer(bench.LDE.GetSurfaceAt(1).CoatingData,i)) for i in range(1,len(states)+1)])
                except Exception:
                    tool.Close();raise
                return b._start_task('coating_native_optimization',tool,
                    dict(algorithm=str(tool.Algorithm),cycles=str(tool.Cycles),variables=int(tool.Variables),number_of_cores=1),
                    collector=collect,budget_seconds=q.budget_seconds)
            optimized=yield from b._child_job(task,start,None)
            task['payload']['native_optimization']=optimized['native_terminal']
            task['payload']['native_task']=optimized['task']
            bounds=boundary_report(optimized['layers'],q.variables)
            task['payload']['constraints']=bounds
            if not all(v['satisfied'] for v in bounds):
                raise ZemaxError('COATING_BOUNDS_VIOLATED','原生优化候选超出请求膜厚边界。',constraints=bounds)
            candidate=b.system.CopySystem()
            if candidate is None:raise ZemaxError('COPY_FAILED','无法创建候选模型副本。')
            cdata=candidate.LDE.GetSurfaceAt(q.surface).CoatingData
            # Retain all original solve definitions; only selected thicknesses change.
            for v in q.variables:
                value=get_layer(cdata,v.layer);value.SetThicknessStatusVariable()
                value.ThicknessMultiplier=optimized['layers'][v.layer-1]['thickness_multiplier']
                if not cdata.SetLayerSettings(v.layer,value):raise ZemaxError('SETTING_REJECTED','候选膜厚写入失败。',layer=v.layer)
            candidate.UpdateStatus()
            for state in optimized['layers']:
                actual=layer_data(get_layer(cdata,state['layer']))
                for key in ('thickness_multiplier','index_offset','extinction_offset'):
                    check_setting_value(key,state[key],actual[key])
            actual_owner=BenchOwner(b,candidate)
            direct_final=actual_owner.get_coating_rta(direct_request)
            final=bench_performance(bench,mapping,direct_final)
            final_score=objective_value(final['samples'],q.objectives)
            task['payload']['direct_after']=direct_final
            task['payload']['direct_comparison_after']=direct_comparison(direct_final,final)
            task['payload']['mapping_after']=compare_objectives(bench,mapping['target_operands'],final_score['values'])
            selected=final_score['weighted_mean_squared_error']<=initial_score['weighted_mean_squared_error']
            task['summary']=dict(initial=initial_score,optimized=final_score,selected='optimized' if selected else 'baseline',
                improved=final_score['weighted_mean_squared_error']<initial_score['weighted_mean_squared_error'],
                fixed_stack=dict(surface=q.surface,coating=baseline['coating'],layers=baseline['total']),
                native_terminal=optimized['native_terminal'],constraints_satisfied=True)
            task['payload']['before']=physical_initial;task['payload']['after']=final
            task['payload']['layers_after']=optimized['layers']
            for i,(obj,old,new) in enumerate(zip(q.objectives,initial_score['values'],final_score['values'])):
                task['rows'].append(dict(index=i,**obj.model_dump(),before=old,after=new,residual=new-obj.target))
            task['payload']['series']=[dict(series=0,description='Coating objective coefficients',x_label='objective index',
                x_unit='index',y_unit='dimensionless',labels=['before','after','target'],
                x=list(range(len(q.objectives))),y=[[a,c,o.target] for a,c,o in zip(initial_score['values'],final_score['values'],q.objectives)])]
            yield
            b._cancel_boundary(task)
            if q.save_best:
                path=Path(b.directory)/(task['task_id']+'_best.zos')
                chosen=candidate if selected else b.system.CopySystem()
                if not selected:
                    try:chosen.SaveAs(str(path))
                    finally:close_system(b,chosen)
                else:chosen.SaveAs(str(path))
                task['payload']['artifacts']=[dict(kind='candidate_model',path=str(path))]
                task['summary']['best_model']=str(path)
        except Exception as exc:
            error=exc;raise
        finally:
            errors=[]
            for system in (candidate,bench):
                if system is not None:
                    try:close_system(b,system)
                    except Exception as exc:errors.append(str(exc))
            task['payload']['resources']=dict(candidate_closed=candidate is not None and not errors,
                bench_closed=bench is not None and not errors,cleanup_errors=errors)
            if errors:
                raise ZemaxError('CLEANUP_FAILED','镀膜优化资源释放失败。',cleanup_errors=errors,
                    operation_error=b._evaluation_error(error) if error else None)
    return b._composite('coating_optimization',q.model_dump(),flow)
