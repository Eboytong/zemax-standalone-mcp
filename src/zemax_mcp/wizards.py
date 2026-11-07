"""MFE wizard settings and cooperative, checkpointed merit-function generation."""
from .analyses import scalar_settings, native_setting
from .data import unwrap
from .detectors import check_setting_value
from .errors import ZemaxError
from .wizard_models import WIZARD_FIELDS

WIZARDS = dict(sequential='SEQOptimizationWizard2', nsc='NSCOptimizationWizard', bitmap='NSCBitmapWizard', roadway='NSCRoadwayLightingWizard')

def check_value(native, target, name, expected):
    prop = target.GetType().GetProperty(name)
    actual = getattr(target, name)
    if prop.PropertyType.IsEnum:
        if not actual.Equals(native.enum(prop.PropertyType, expected)):
            raise ZemaxError('SETTING_REJECTED', '向导枚举未采用。', setting=name, requested=expected, actual=str(actual))
    else:
        check_setting_value(name, expected, actual)

def conditions(kind, final, requested, system):
    def require(fields, flag):
        for name in fields:
            if name in requested and not final.get(flag):
                raise ZemaxError('INACTIVE_SETTING', '向导参数需要先启用对应选项。', setting=name, required=flag)
    if kind == 'sequential':
        if bool(final['UseGaussianQuadrature']) == bool(final['UseRectangularArray']):
            raise ZemaxError('INVALID_SETTINGS', '请选择一种瞳采样方式。')
        require(['Rings', 'Arms', 'Obscuration'], 'UseGaussianQuadrature')
        require(['GridSizeNxN'], 'UseRectangularArray')
        require(['GlassMin', 'GlassMax', 'GlassEdgeThickness'], 'UseGlassBoundaryValues')
        require(['AirMin', 'AirMax', 'AirEdgeThickness'], 'UseAirBoundaryValues')
        require(['MaxDistortionPct'], 'UseMaximumDistortion')
        require(['ManufacturingYieldWeight'], 'OptimizeForManufacturingYield')
        if final['OptimizeForBestNominalPerformance'] and final['OptimizeForManufacturingYield']:
            raise ZemaxError('INVALID_SETTINGS', '名义性能与制造良率优化选项冲突。')
        if final['OptimizeForManufacturingYield'] and not final.get('IsHighManufacturingYieldAvailable'):
            raise ZemaxError('CAPABILITY_UNAVAILABLE', '当前系统或许可未开放制造良率优化。')
        for group in ('Glass', 'Air'):
            if final['Use'+group+'BoundaryValues'] and final[group+'Min'] > final[group+'Max']:
                raise ZemaxError('INVALID_SETTINGS', '厚度边界下限大于上限。', group=group)
        for name, all_name, count in [('FieldNumber','UseAllFields',system.SystemData.Fields.NumberOfFields), ('ConfigurationNumber','UseAllConfigurations',system.MCE.NumberOfConfigurations)]:
            if name in requested and final[all_name]:
                raise ZemaxError('INACTIVE_SETTING', '指定单项前请关闭全部选项。', setting=name, required=all_name+'=false')
            if not final[all_name] and not 1 <= final[name] <= count:
                raise ZemaxError('INDEX_OUT_OF_RANGE', '向导选择超出范围。', setting=name, count=count)
        if not 0 <= final['Obscuration'] < 1:
            raise ZemaxError('INVALID_SETTINGS', '瞳遮拦比例必须在[0,1)。')
    elif kind in ('nsc', 'bitmap'):
        require(['ClearDetector'], 'IsClearDataSettingsUsed')
        require(['UseSource', 'IsSplitRaysUsed', 'IsScatterRaysUsed', 'IsUsePolarizationUsed', 'IsIgnoreErrorsUsed', 'IsUseLightningTraceUsed'], 'IsRaytraceSettingsUsed')
        require(['MinimumFlux'], 'IsMinimumFluxUsed')
        require(['Target'], 'IsTargetSettingsUsed')
        require(['RaySampling', 'EdgeSampling'], 'IsResampleDetectorUsed')
    if kind == 'roadway':
        for name in ('MountingHeight','LongitudinalSpacing','LaneWidth'):
            if name in requested and final[name] <= 0:
                raise ZemaxError('INVALID_SETTINGS', '道路几何尺寸必须为正。', setting=name)
    for name, value in final.items():
        if name in requested and any(token in name for token in ('Weight','Frequency','Flux')) and isinstance(value,(int,float)) and value < 0:
            raise ZemaxError('INVALID_SETTINGS', '此向导参数必须非负。', setting=name)

def selections(target, names):
    result = {}
    for count_name, getter in names:
        count = int(getattr(target, count_name))
        if count < 0 or count > 10000:
            raise ZemaxError('INVALID_RESULT_DATA', '原生选项数量异常。', setting=count_name, actual=count)
        items=[]
        for index in range(count):
            try: items.append(dict(native_index=index, label=str(getattr(target,getter)(index))))
            except Exception as exc: items.append(dict(native_index=index, error=str(exc)))
        result[getter]=dict(native_count=count, entries=items, numbering='native accessor index; lookup errors retained')
    return result

class WizardsMixin:
    def _wizard(self, kind):
        mode = str(self.system.Mode)
        if (kind == 'sequential' and mode != 'Sequential') or (kind != 'sequential' and mode != 'NonSequential'):
            raise ZemaxError('UNSUPPORTED_MODE', '向导与当前系统模式不匹配。', kind=kind, mode=mode)
        wizard = unwrap(getattr(self.system.MFE, WIZARDS[kind]))
        target = unwrap(wizard.NSCSettings) if kind in ('nsc','bitmap') else wizard
        common = unwrap(wizard.CommonSettings)
        return wizard, target, common

    def get_optimization_wizard_options(self, req):
        wizard, target, _ = self._wizard(req.kind)
        settings = scalar_settings(target)
        enums = {name:self.native.property_enum_names(target,name) for name in WIZARD_FIELDS[req.kind].values()
            if target.GetType().GetProperty(name).PropertyType.IsEnum}
        lookup = []
        if req.kind in ('nsc','bitmap'):
            lookup = [('NumberOfSources','GetSourceAt'),('NumberOfDetectors','GetDetectorAt'),('NumberOfCriterion','GetCriterionAt'),('NumberOfConfigurations','GetConfigurationAt'),('NumberOfRaySamplings','GetRaySamplingAt'),('NumberOfEdgeSamplings','GetEdgeSamplingAt'),('NumberOfBoundaries','GetBoundaryAt')]
        elif req.kind == 'roadway':
            lookup = [('NumberOfOrigins','GetOriginAt'),('NumberOfConfigurations','GetConfigurationAt'),('NumberOfArrangements','GetArrangementAt'),('NumberOfClassifications','GetClassificationAt'),('NumberOfRoadClasses','GetRoadClassAt')]
        result = dict(kind=req.kind, settings=settings, enums=enums, selections=selections(target,lookup), ownership='MFE wizard; no SystemTool Close interface')
        if req.kind == 'bitmap':result['bitmap_files']=selections(wizard,[('NumberOfBitmapFiles','GetBitmapFileAt')])
        return result

    def run_optimization_wizard(self, req):
        q=req.request
        self._wizard(q.kind)
        def flow(task):
            self._cancel_boundary(task)
            wizard,target,common=self._wizard(q.kind)
            if q.reset:common.ResetSettings()
            mapping=WIZARD_FIELDS[q.kind]
            values={mapping[key]:getattr(q,key) for key in mapping if key in q.model_fields_set}
            original=scalar_settings(target)
            if original.get('unavailable_fields'):
                raise ZemaxError('SETTING_UNAVAILABLE', '向导初始设置读取失败。', unavailable_fields=original['unavailable_fields'])
            final={**original,**values}
            # Radio buttons can switch the other setting; encode the full desired pair.
            for a,b in [('UseGaussianQuadrature','UseRectangularArray'),('OptimizeForBestNominalPerformance','OptimizeForManufacturingYield')]:
                if values.get(a) is True and b not in values:values[b]=False;final[b]=False
                if values.get(b) is True and a not in values:values[a]=False;final[a]=False
            conditions(q.kind,final,values,self.system)
            if q.kind == 'bitmap' and q.apply and int(wizard.NumberOfBitmapFiles) == 0:
                raise ZemaxError('RESOURCE_NOT_FOUND', '位图向导没有可用位图。', next_action='准备原生向导可发现的位图文件后查询选项')
            # Native accessors define selector labels; requested indices must resolve.
            getters = dict(Criterion='GetCriterionAt', UseSource='GetSourceAt', UseDetector='GetDetectorAt', Configuration='GetConfigurationAt', RaySampling='GetRaySamplingAt', EdgeSampling='GetEdgeSamplingAt', Boundary='GetBoundaryAt') if q.kind in ('nsc','bitmap') else dict(Origin='GetOriginAt', Configuration='GetConfigurationAt', Arrangement='GetArrangementAt', SurfaceClassification='GetClassificationAt', RoadClass='GetRoadClassAt') if q.kind == 'roadway' else {}
            for name, getter in getters.items():
                if name in values:
                    try:
                        label = getattr(target, getter)(values[name])
                        if label is None or not str(label).strip():raise ValueError('empty native option')
                    except Exception as exc:
                        raise ZemaxError('INVALID_SELECTION', '向导原生选项无法解析。', setting=name, requested=values[name], reason=str(exc)) from exc
            if q.kind == 'bitmap' and 'BitmapFile' in values:
                try:
                    label = wizard.GetBitmapFileAt(values['BitmapFile'])
                    if label is None or not str(label).strip():raise ValueError('empty native bitmap')
                except Exception as exc:
                    raise ZemaxError('RESOURCE_NOT_FOUND', '原生位图选项无法解析。', requested=values['BitmapFile'], reason=str(exc)) from exc
            # Flags and selectors precede their dependent parameters.
            order=sorted(values,key=lambda n:0 if isinstance(values[n],bool) else 1 if n in ('Criterion','Type','Reference','UseDetector','UseSource','Configuration','BitmapFile') else 2)
            for name in order:
                native_setting(self.native,target,name,values[name]);check_value(self.native,target,name,values[name])
            for name,value in values.items():check_value(self.native,target,name,value)
            actual=scalar_settings(target)
            if actual.get('unavailable_fields'):
                raise ZemaxError('SETTING_UNAVAILABLE', '向导最终设置读取失败。', unavailable_fields=actual['unavailable_fields'])
            conditions(q.kind,actual,values,self.system)
            task['payload']=dict(kind=q.kind,requested=q.model_dump(),settings=actual,applied=False,source='ZOS-API MFE wizard',ownership='MFE-owned; no SystemTool Close')
            yield
            self._cancel_boundary(task)
            if q.apply:
                before=int(self.system.MFE.NumberOfOperands)
                self._mutate('wizard_'+q.kind)
                task['context']=self.context()
                try:
                    common.Apply()
                except Exception as exc:
                    details=dict(cause=self._evaluation_error(exc), checkpoint=self.last_checkpoint, operands_before=before)
                    try:details['operands_after']=int(self.system.MFE.NumberOfOperands)
                    except Exception as read_error:details['state_read_error']=str(read_error)
                    raise ZemaxError('WIZARD_APPLY_FAILED','原生向导生成评价函数失败。',**details) from exc
                task['payload'].update(applied=True,operands_before=before,operands_after=int(self.system.MFE.NumberOfOperands),
                    operands=self.get_merit_function(None),settings_after=scalar_settings(target),checkpoint=self.last_checkpoint)
            yield
        return self._composite('optimization_wizard_'+q.kind,q.model_dump(),flow,require_sequential=q.kind=='sequential')
