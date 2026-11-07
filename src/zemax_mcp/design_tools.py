"""Checkpointed design SystemTools sharing the worker task owner."""
import math
from .errors import ZemaxError
from .detectors import check_setting_value

OPENERS = {
    'scale_factor': 'OpenScale', 'scale_units': 'OpenScale',
    'quick_adjust': 'OpenQuickAdjust', 'find_best_asphere': 'OpenFindBestAsphere',
    'convert_asphere': 'OpenConvertAsphereTypes', 'ray_aiming_wizard': 'OpenRayAimingWizard',
}
RAY_FIELDS = ('RayAiming', 'Method', 'UseRayAimingCache', 'UseRobustRayAiming', 'ScalePupilShiftFactorsByField', 'AutomaticallyCalculatePupilShiftsIsChecked', 'UseEnhancedRayAiming', 'UseAdvancedConvergence', 'UseFallBackSearchDuringCacheSetup', 'PupilShiftX', 'PupilShiftY', 'PupilShiftZ', 'PupilCompressX', 'PupilCompressY', 'NumStepsCacheSetup')
FIELDS = {
    'ray_aiming_wizard': (),
    'scale_factor': ('ScaleByFactor', 'ScaleByUnits', 'ScaleFactor', 'FirstComponent', 'LastComponent', 'NumberOfComponents'),
    'scale_units': ('ScaleByFactor', 'ScaleByUnits', 'ScaleToUnit', 'NumberOfComponents'),
    'quick_adjust': ('AdjustSurface', 'SurfaceParameter', 'Criterion', 'EvaluateSurface'),
    'find_best_asphere': ('FirstSurface', 'LastSurface', 'AsphereType'),
    'convert_asphere': ('Surface', 'AsphereType', 'NumberOfTerms', 'ExcludeSecondOrderTerm', 'AllowRadiusVariation', 'AllowConicVariation'),
}
ENUMS = {'ScaleToUnit', 'SurfaceParameter', 'Criterion', 'AsphereType', 'RayAiming', 'Method'}

def read_settings(tool, kind):
    return {name: str(getattr(tool, name)) if name in ENUMS else getattr(tool, name) for name in FIELDS[kind]}

def check_design_setting(backend, tool, name, value):
    actual = getattr(tool, name)
    if name in ENUMS:
        prop = tool.GetType().GetProperty(name)
        expected = backend.native.enum(prop.PropertyType, value)
        if not actual.Equals(expected):
            raise ZemaxError('SETTING_REJECTED', '原生枚举未采用。', setting=name, requested=value, actual=str(actual))
    else:
        check_setting_value(name, value, actual)

def apply_settings(backend, tool, kind, values):
    for name, value in values.items():
        if name in ENUMS:
            backend.native.set_enum(tool, name, value)
        else:
            setattr(tool, name, value)
        check_design_setting(backend, tool, name, value)
    for name, value in values.items():
        check_design_setting(backend, tool, name, value)
    return read_settings(tool, kind)

class DesignToolsMixin:
    def get_design_tool_options(self, req):
        self._require_sequential()
        tool = getattr(self.system.Tools, OPENERS[req.kind])()
        try:
            enums = {name: self.native.property_enum_names(tool, name) for name in FIELDS[req.kind] if name in ENUMS}
            result = dict(kind=req.kind, settings=read_settings(tool, req.kind), enums=enums,
                component_bounds='native FirstComponent/LastComponent defaults; optional overrides checked by native readback',
                write_only=['IsAutomatic'] if req.kind == 'convert_asphere' else [])
        except Exception:
            self._close_task_native({'native': tool})
            raise
        if not self._close_task_native({'native': tool}):
            raise ZemaxError('CLEANUP_FAILED', '设计工具资源释放未确认。')
        return result

    def _design_snapshot(self):
        lde = self.system.LDE
        rows = []
        for index in range(lde.NumberOfSurfaces):
            row = lde.GetSurfaceAt(index)
            rows.append(dict(surface=index, type=str(row.Type), radius=float(row.Radius),
                thickness=float(row.Thickness), conic=float(row.Conic)))
        return dict(surfaces=rows, lens_units=str(self.system.SystemData.Units.LensUnits),
            configuration=int(self.system.MCE.CurrentConfiguration), model_revision=self.revision)

    def run_design_tool(self, req):
        q = req.request
        self._require_sequential()
        last = self.system.LDE.NumberOfSurfaces - 1
        cell = None
        if q.kind == 'quick_adjust':
            if q.surface >= last:
                raise ZemaxError('INDEX_OUT_OF_RANGE', '调整曲面必须位于像面之前。', surface=q.surface)
            evaluate = last if q.evaluate_surface is None else q.evaluate_surface
            if not q.surface < evaluate <= last:
                raise ZemaxError('INDEX_OUT_OF_RANGE', '评价曲面必须位于调整曲面之后。', evaluate_surface=evaluate)
            cell = getattr(self._row(q.surface), q.parameter + 'Cell')
            self._guard_cell(cell, q.replace_solve)
        if q.kind == 'find_best_asphere' and q.last_surface >= last:
            raise ZemaxError('INDEX_OUT_OF_RANGE', '搜索范围必须位于像面之前。')
        if q.kind == 'convert_asphere' and q.surface >= last:
            raise ZemaxError('INDEX_OUT_OF_RANGE', '转换曲面必须位于像面之前。')
        before = self._design_snapshot()
        if q.kind == 'ray_aiming_wizard':
            before['ray_aiming'] = {name: str(getattr(self.system.SystemData.RayAiming, name)) if name in ENUMS else getattr(self.system.SystemData.RayAiming, name) for name in RAY_FIELDS}
        # Create recovery point before native setters, since tools may mutate on setup.
        if q.kind != 'ray_aiming_wizard' or q.apply:
            self._mutate(q.kind)
        if q.kind == 'quick_adjust' and q.replace_solve and str(cell.Solve) not in ('Fixed', 'Variable'):
            cell.MakeSolveFixed()
            check_setting_value('Solve', 'Fixed', str(cell.Solve))
        tool = getattr(self.system.Tools, OPENERS[q.kind])()
        try:
            values = {}
            if q.kind == 'scale_factor':
                values = dict(ScaleByFactor=True, ScaleByUnits=False, ScaleFactor=q.factor)
                if q.first_component is not None: values['FirstComponent'] = q.first_component
                if q.last_component is not None: values['LastComponent'] = q.last_component
            elif q.kind == 'scale_units':
                values = dict(ScaleByUnits=True, ScaleByFactor=False, ScaleToUnit=q.unit)
            elif q.kind == 'quick_adjust':
                values = dict(AdjustSurface=q.surface, SurfaceParameter=q.parameter, Criterion=q.criterion)
                if q.evaluate_surface is None:
                    tool.SetEvaluateSurfaceImage()
                values['EvaluateSurface'] = evaluate
            elif q.kind == 'find_best_asphere':
                values = dict(FirstSurface=q.first_surface, LastSurface=q.last_surface, AsphereType=q.asphere_type)
            elif q.kind == 'convert_asphere':
                # Formal IsAutomatic has no getter in 2024 R2.
                tool.IsAutomatic = q.number_of_terms is None
                values = dict(Surface=q.surface, AsphereType=q.asphere_type,
                    ExcludeSecondOrderTerm=q.exclude_second_order_term,
                    AllowRadiusVariation=q.allow_radius_variation, AllowConicVariation=q.allow_conic_variation)
                if q.number_of_terms is not None: values['NumberOfTerms'] = q.number_of_terms
            actual = apply_settings(self, tool, q.kind, values)
            if q.kind == 'scale_factor' and actual['FirstComponent'] > actual['LastComponent']:
                raise ZemaxError('INVALID_SETTINGS', '原生缩放范围起点大于终点。', actual=actual)
            if q.kind == 'convert_asphere':
                actual['automatic'] = dict(requested=q.number_of_terms is None, readback='unavailable: native IsAutomatic is write-only')
        except Exception:
            self._close_task_native({'native': tool})
            raise

        def collect(task):
            native = task['native']
            if not native.Succeeded:
                raise ZemaxError('TASK_FAILED', str(native.ErrorMessage) or '原生设计工具失败。')
            result = dict(kind=q.kind, settings=read_settings(native, q.kind), source='ZOS-API SystemTool', before=before)
            names = ('StartMeritFunction', 'BestMeritFunction', 'BestSurface') if q.kind == 'find_best_asphere' else ('ResidualRMSError',) if q.kind == 'convert_asphere' else ()
            for name in names:
                value = getattr(native, name)
                if not math.isfinite(float(value)):
                    raise ZemaxError('INVALID_RESULT_DATA', '原生设计工具结果非有限。', field=name, actual=str(value))
                result[name] = value
            if q.kind == 'ray_aiming_wizard':
                recommended = native.GetRecommendedSettings()
                if recommended is None:
                    raise ZemaxError('RESULT_UNAVAILABLE', '原生Ray Aiming向导未返回推荐设置。')
                recommended_values = {name: getattr(recommended, name) for name in RAY_FIELDS}
                result['recommended'] = {name: str(value) if name in ENUMS else value for name, value in recommended_values.items()}
                if q.apply:
                    native.ApplyRecommendedSettings()
                current = self.system.SystemData.RayAiming
                for name in RAY_FIELDS:
                    expected = recommended_values[name] if q.apply else before['ray_aiming'][name]
                    if name in ENUMS and q.apply:
                        if not getattr(current, name).Equals(expected):
                            raise ZemaxError('SETTING_REJECTED', 'Ray Aiming推荐设置未采用。', setting=name)
                    else:
                        check_design_setting(self, current, name, expected)
                result['applied'] = q.apply
                result['actual_ray_aiming'] = {name: str(getattr(current, name)) if name in ENUMS else getattr(current, name) for name in RAY_FIELDS}
            if not self._close_task_native(task):
                raise ZemaxError('CLEANUP_FAILED', '设计工具资源释放未确认。')
            result['after'] = self._design_snapshot()
            result['checkpoint'] = self.last_checkpoint
            if q.kind == 'convert_asphere': result['residual_unit'] = before['lens_units']
            return result

        return self._start_task(q.kind, tool, dict(request=q.model_dump(), actual=actual), before=before, collector=collect)
