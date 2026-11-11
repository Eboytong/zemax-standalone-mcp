"""Uniform-temperature response and native multi-configuration focus compensation."""
import math
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .detectors import check_setting_value
from .errors import ZemaxError
from .schema import FiniteFloat, PositiveIndex, Request


class ThermalCompensation(Request):
    kind: Literal['thermal_compensation']
    configurations: Annotated[list[PositiveIndex], Field(min_length=2, max_length=20)]
    reference_configuration: PositiveIndex = 1
    compensation_surface: PositiveIndex
    minimum_gap: Annotated[FiniteFloat, Field(gt=0)]
    maximum_gap: Annotated[FiniteFloat, Field(gt=0)]
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    rings: Annotated[int, Field(strict=True, ge=2, le=10)] = 3
    optimize: bool = True
    replace_compensation_solves: bool = False
    cycles: Literal['Fixed_1_Cycle', 'Fixed_5_Cycles', 'Fixed_10_Cycles', 'Fixed_50_Cycles'] = 'Fixed_10_Cycles'
    budget_seconds: Annotated[FiniteFloat, Field(gt=0, le=3600)] = 120

    @model_validator(mode='after')
    def contract(self):
        if len(set(self.configurations)) != len(self.configurations):
            raise ValueError('温度配置编号不得重复。')
        if self.reference_configuration not in self.configurations:
            raise ValueError('参考配置须包含在温度配置中。')
        if self.minimum_gap >= self.maximum_gap:
            raise ValueError('补偿间隔下界须小于上界。')
        return self


def read_state(b, system, q):
    from System import Array, Double
    from .glass_trials import native_value
    fields = system.SystemData.Fields
    if str(fields.Normalization) != 'Radial':
        raise ZemaxError('UNSUPPORTED_FIELD_NORMALIZATION', '热补偿采用Radial视场归一化。')
    maximum = max(math.hypot(float(fields.GetField(i).X), float(fields.GetField(i).Y))
                  for i in range(1, int(fields.NumberOfFields) + 1))
    field = fields.GetField(q.field)
    params = {2:q.rings, 3:q.wavelength, 4:float(field.X)/maximum if maximum else 0,
              5:float(field.Y)/maximum if maximum else 0}
    count = int(system.SystemData.Wavelengths.NumberOfWavelengths)
    surfaces = []
    for i in range(1, int(system.LDE.NumberOfSurfaces)-1):
        row = system.LDE.GetSurfaceAt(i)
        indices = Array[Double]([0.]*count)
        if int(system.LDE.GetIndex(i, count, indices)) != count:
            raise ZemaxError('INVALID_INDEX_RESULT', '热配置折射率数量不符。', surface=i)
        values = list(map(float, indices))
        if any(not math.isfinite(v) or v <= 0 for v in values):
            raise ZemaxError('INVALID_INDEX_RESULT', '热配置返回无效折射率。', surface=i)
        radius = float(row.Radius)
        surfaces.append(dict(surface=i, radius=None if math.isinf(radius) else radius,
            plane=math.isinf(radius), thickness=float(row.Thickness), material=str(row.Material),
            indices=values, tce_ppm_per_celsius=float(row.TCE)))
    return dict(configuration=int(system.MCE.CurrentConfiguration),
        temperature_c=float(system.SystemData.Environment.Temperature),
        pressure_atm=float(system.SystemData.Environment.Pressure),
        adjust_index_to_environment=bool(system.SystemData.Environment.AdjustIndexToEnvironment),
        gap=float(system.LDE.GetSurfaceAt(q.compensation_surface).Thickness), surfaces=surfaces,
        rms_spot=native_value(b, system, 'RSCE', params),
        rms_wavefront=native_value(b, system, 'RWCE', params),
        effective_focal_length=native_value(b, system, 'EFFL', {3:q.wavelength}))


def run_thermal_compensation(b, q):
    from .coating_optimization import operand
    b._require_sequential(focused=True)
    b._require_work()
    def flow(task):
        system = None
        errors = []
        operation_error = None
        task['payload'] = dict(analysis_kind=q.kind, series=[], grids=[],
            computation_method='native MCE thermal configurations and native multi-configuration local optimization',
            units=dict(length='lens units',temperature='Celsius',rms_spot='lens units',rms_wavefront='waves'))
        task['restoration'] = dict(required=False,restored=True,reason='owned system copy; source configuration, solves and MFE unchanged')
        try:
            system = b.system.CopySystem()
            if system is None:
                raise ZemaxError('COPY_FAILED','热补偿工作副本创建失败。')
            m = system.MCE
            task['payload']['material_catalogs']=[str(v) for v in system.SystemData.MaterialCatalogs.GetCatalogsInUse() if str(v).strip()]
            task['payload']['actual_settings']=dict(request=q.model_dump(),source_configuration=int(m.CurrentConfiguration),
                budget_scope='native optimization only',reference='existing native TEMP and thermal-pickup configurations')
            if max(q.configurations) > int(m.NumberOfConfigurations):
                raise ZemaxError('INDEX_OUT_OF_RANGE','温度配置编号越界。')
            if q.compensation_surface >= int(system.LDE.NumberOfSurfaces)-1:
                raise ZemaxError('INDEX_OUT_OF_RANGE','补偿面须位于像面之前。')
            if q.field > int(system.SystemData.Fields.NumberOfFields) or q.wavelength > int(system.SystemData.Wavelengths.NumberOfWavelengths):
                raise ZemaxError('INDEX_OUT_OF_RANGE','评价视场或波长编号越界。')
            task['payload']['actual_settings']['wavelength_um']=float(system.SystemData.Wavelengths.GetWavelength(q.wavelength).Wavelength)
            thermal_rows = [m.GetOperandAt(i) for i in range(1,int(m.NumberOfOperands)+1)]
            if len([r for r in thermal_rows if str(r.Type)=='TEMP']) != 1:
                raise ZemaxError('INVALID_THERMAL_CONFIGURATIONS','需要唯一TEMP温度操作数。')
            gaps = [r for r in thermal_rows if str(r.Type)=='THIC' and int(r.Param1)==q.compensation_surface]
            if len(gaps) != 1:
                raise ZemaxError('INVALID_COMPENSATION_OPERAND','需要唯一对应补偿面的THIC配置操作数。')
            gap_operand = gaps[0]
            original_solves = []
            before = []
            for conf in q.configurations:
                b._cancel_boundary(task)
                if not m.SetCurrentConfiguration(conf):
                    raise ZemaxError('CONFIGURATION_FAILED','无法选择温度配置。',configuration=conf)
                status = str(system.UpdateStatus())
                if status:
                    raise ZemaxError('CONFIGURATION_FAILED',status,configuration=conf)
                state = read_state(b,system,q)
                if str(system.LDE.GetSurfaceAt(q.compensation_surface).Material).strip():
                    raise ZemaxError('UNSUPPORTED_COMPENSATOR','补偿变量采用空气间隔。')
                if not q.minimum_gap <= state['gap'] <= q.maximum_gap:
                    raise ZemaxError('COMPENSATION_BOUNDS','基线补偿间隔超出边界。',configuration=conf,value=state['gap'])
                cell = gap_operand.GetOperandCell(conf)
                solve = str(cell.Solve)
                original_solves.append(dict(configuration=conf,mode=solve))
                if q.optimize and solve not in {'Fixed','Variable'} and not q.replace_compensation_solves:
                    raise ZemaxError('SOLVE_PROTECTED','补偿间隔有拾取关系；显式允许替换后执行。',configuration=conf,solve=solve)
                before.append(state)
                yield
            if len({r['temperature_c'] for r in before}) < 2:
                raise ZemaxError('INVALID_THERMAL_CONFIGURATIONS','温度配置须至少有两个不同温度。')
            task['payload']['before'] = before
            task['payload']['original_compensation_solves'] = original_solves
            if q.optimize:
                # Keep unrelated dependency solves; fix all pre-existing optimization variables.
                for i in range(int(system.LDE.NumberOfSurfaces)):
                    row = system.LDE.GetSurfaceAt(i)
                    for cell in [row.RadiusCell,row.ThicknessCell,row.ConicCell]:
                        if str(cell.Solve)=='Variable':
                            b._set_variable_mode(cell,False)
                for row in thermal_rows:
                    for conf in range(1,int(m.NumberOfConfigurations)+1):
                        cell = row.GetOperandCell(conf)
                        if str(cell.Solve)=='Variable' and not cell.MakeSolveFixed():
                            raise ZemaxError('SOLVE_UPDATE_FAILED','无法固定旧MCE变量。')
                mfe = system.MFE
                mfe.RemoveOperandsAt(1,int(mfe.NumberOfOperands))
                for conf in q.configurations:
                    m.SetCurrentConfiguration(conf)
                    cell = gap_operand.GetOperandCell(conf)
                    if not cell.MakeSolveFixed():
                        raise ZemaxError('SOLVE_UPDATE_FAILED','无法固定补偿单元。')
                    data = cell.CreateSolveType(b.native.api.Editors.SolveType.Variable)
                    b._checked_set_solve(cell,data)
                    check_setting_value('compensation_solve','Variable',str(cell.Solve))
                    operand(b,mfe,'CONF',{2:conf})
                    fields=system.SystemData.Fields
                    maxfield=max(math.hypot(float(fields.GetField(i).X),float(fields.GetField(i).Y)) for i in range(1,int(fields.NumberOfFields)+1))
                    field=fields.GetField(q.field)
                    operand(b,mfe,'RSCE',{2:q.rings,3:q.wavelength,4:float(field.X)/maxfield if maxfield else 0,5:float(field.Y)/maxfield if maxfield else 0},0,1)
                    operand(b,mfe,'CTGT',{2:q.compensation_surface},q.minimum_gap,10000)
                    operand(b,mfe,'CTLT',{2:q.compensation_surface},q.maximum_gap,10000)
                system.UpdateStatus()
                def start(_):
                    tool=system.Tools.OpenLocalOptimization()
                    try:
                        b.native.set_enum(tool,'Algorithm','DampedLeastSquares')
                        b.native.set_enum(tool,'Cycles',q.cycles)
                        tool.NumberOfCores=1
                        check_setting_value('Variables',len(q.configurations),int(tool.Variables))
                        def collect(child):
                            if not tool.Succeeded:
                                raise ZemaxError('NATIVE_OPTIMIZATION_FAILED',str(tool.ErrorMessage))
                            return dict(merit=float(tool.CurrentMeritFunction),succeeded=True)
                        return b._start_task('thermal_native_optimization',tool,dict(algorithm=str(tool.Algorithm),cycles=str(tool.Cycles),variables=int(tool.Variables),number_of_cores=1),collector=collect,budget_seconds=q.budget_seconds)
                    except Exception:
                        tool.Close()
                        raise
                task['payload']['native_optimization']=yield from b._child_job(task,start,None)
            after=[]
            for initial in before:
                b._cancel_boundary(task)
                system.MCE.SetCurrentConfiguration(initial['configuration'])
                system.UpdateStatus()
                state=read_state(b,system,q)
                if not q.minimum_gap <= state['gap'] <= q.maximum_gap:
                    raise ZemaxError('COMPENSATION_BOUNDS','原生优化结果超出补偿边界。',actual=state['gap'])
                for a,c in zip(initial['surfaces'],state['surfaces']):
                    for key in ['radius','material','indices','tce_ppm_per_celsius']:
                        if a[key]!=c[key]:
                            raise ZemaxError('DEPENDENT_MODEL_CHANGE','补偿改变了其他热几何或材料。',surface=a['surface'],field=key)
                    if a['surface']!=q.compensation_surface and a['thickness']!=c['thickness']:
                        raise ZemaxError('DEPENDENT_MODEL_CHANGE','补偿改变了其他厚度。',surface=a['surface'])
                state['compensation_displacement']=state['gap']-initial['gap']
                after.append(state)
                task['rows'].append(dict(configuration=state['configuration'],temperature_c=state['temperature_c'],before=initial,after=state))
                yield
            system.MCE.SetCurrentConfiguration(q.reference_configuration)
            path=Path(b.directory)/(task['task_id']+'_thermal.zos')
            system.SaveAs(str(path))
            if not path.is_file():
                raise ZemaxError('SAVE_FAILED','原生推荐模型未生成。')
            task['payload']['after']=after
            task['payload']['artifacts']=[dict(kind='recommended_model',path=str(path))]
            ordered=sorted(task['rows'],key=lambda v:v['temperature_c'])
            task['payload']['series']=[dict(series=0,description='Uniform thermal RMS spot',x_label='temperature',x_unit='Celsius',y_unit='lens units',labels=['baseline','compensated'],x=[r['temperature_c'] for r in ordered],y=[[r['before']['rms_spot'],r['after']['rms_spot']] for r in ordered])]
            task['summary']=dict(configurations=len(after),optimized=q.optimize,recommended_model=str(path),
                reference_configuration=q.reference_configuration,compensation='independent actuator air-gap position per requested temperature configuration',
                max_rms_before=max(r['rms_spot'] for r in before),max_rms_after=max(r['rms_spot'] for r in after))
        except BaseException as exc:
            operation_error=exc
            raise
        finally:
            if system is not None:
                try:
                    if system.Close(False) is False:
                        raise RuntimeError('Close(False) returned false')
                except Exception as exc:
                    errors.append(str(exc));b.requires_reconnect=True
            task['payload']['resources']=dict(copies_created=int(system is not None),all_copies_closed=not errors,cleanup_errors=errors)
            if errors:
                raise ZemaxError('CLEANUP_FAILED','热补偿副本关闭失败。',cleanup_errors=errors,operation_error=b._evaluation_error(operation_error) if operation_error else None)
    return b._composite(q.kind,q.model_dump(),flow)
