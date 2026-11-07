"""Checked sequential-to-NSC conversion with checkpoint and mode evidence."""
from .errors import ZemaxError
from .detectors import checked_setting,check_setting_readback
from .analyses import scalar_settings

MAPPING=dict(ignore_errors='IgnoreErrors',create_sources_and_detectors='CreateSourcesAndDetectors',convert_to_global_coordinates='ConvertToGlobalCoordinates',convert_stop_to_nsc_aperture='ConvertStopToNSCAperture',stop_mechanical_half_width='StopMechanicalHalfWidth',overfill_factor='OverfillFactor')


def scene_snapshot(backend):
    system=backend.system;mode=str(system.Mode)
    value=dict(mode=mode,lens_units=str(system.SystemData.Units.LensUnits),configuration=int(system.MCE.CurrentConfiguration))
    if mode=='Sequential':
        value['surfaces']=[dict(surface=i,type=str(system.LDE.GetSurfaceAt(i).Type),material=str(system.LDE.GetSurfaceAt(i).Material),thickness=float(system.LDE.GetSurfaceAt(i).Thickness))for i in range(system.LDE.NumberOfSurfaces)]
        value['nsc_groups']=[s['surface']for s in value['surfaces']if s['type']=='NonSequential']
    else:
        nce=system.NCE;value['object_count']=int(nce.NumberOfObjects)
        value['objects']=[dict(object=i,type=str(nce.GetObjectAt(i).Type),comment=str(nce.GetObjectAt(i).Comment))for i in range(1,min(200,nce.NumberOfObjects)+1)]
        value['objects_truncated']=nce.NumberOfObjects>200
    return value


def configure(backend,tool,q,last):
    values={name:getattr(q,key)for key,name in MAPPING.items()if getattr(q,key)is not None}
    if q.create_sources_and_detectors and q.overfill_factor is None:values['OverfillFactor']=1.2
    values.update(ConvertFileToNSC=q.mode=='pure',FirstSurface=q.first_surface,LastSurface=last)
    for name,value in values.items():checked_setting(backend.native,tool,name,value)
    for name,value in values.items():check_setting_readback(tool,name,value)
    actual=scalar_settings(tool)
    if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','转换工具设置回读失败。',details=actual['unavailable_fields'])
    return actual


class ConversionMixin:
    def run_nsc_conversion(self,q):
        self._require_sequential();last=q.last_surface if q.last_surface is not None else int(self.system.LDE.NumberOfSurfaces)-2
        if not 1<=q.first_surface<=last<=self.system.LDE.NumberOfSurfaces-2:
            raise ZemaxError('INDEX_OUT_OF_RANGE','转换范围必须位于物面之后、像面之前。',first=q.first_surface,last=last)
        if q.create_sources_and_detectors and (q.first_surface!=1 or last!=self.system.LDE.NumberOfSurfaces-2):
            raise ZemaxError('CONDITION_NOT_MET','自动生成光源和探测器会转换全系统，须选择完整内部曲面范围。')
        before=scene_snapshot(self)
        self._mutate('convert_to_nsc')
        self.system_context={}
        self._engineering_mapping_valid=False
        self.detector_history_known=False;self.detector_records={}
        tool=self.system.Tools.OpenConvertToNSCGroup()
        try:
            actual=configure(self,tool,q,last)
        except Exception as exc:
            holder={'native':tool}
            if not self._close_task_native(holder):
                failure=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
                failure.details['cleanup_warnings']=holder.get('cleanup_warnings',[])
                if failure is not exc:raise failure from exc
            raise
        def collect(task):
            if not tool.Succeeded:raise ZemaxError('TASK_FAILED',str(tool.ErrorMessage),checkpoint=self.last_checkpoint)
            native_result=dict(actual_after=scalar_settings(tool),stop_object_number=int(tool.StopObjectNumber),stop_object_face=int(tool.StopObjectFace))
            if not self._close_task_native(task):raise ZemaxError('CLEANUP_FAILED','转换工具关闭未确认。',checkpoint=self.last_checkpoint)
            self.system_context={}
            after=scene_snapshot(self)
            expected='NonSequential'if q.mode=='pure'else'Sequential'
            if after['mode']!=expected:raise ZemaxError('CONVERSION_NOT_APPLIED','转换后的系统模式不符。',expected=expected,actual=after['mode'],checkpoint=self.last_checkpoint)
            if q.mode=='group' and len(after['nsc_groups'])<=len(before['nsc_groups']):raise ZemaxError('CONVERSION_NOT_APPLIED','转换后未发现新增NSC组。',before=before['nsc_groups'],after=after['nsc_groups'],checkpoint=self.last_checkpoint)
            if q.mode=='pure'and after['object_count']<1:raise ZemaxError('INVALID_RESULT_DATA','原生转换成功但未返回非序列对象。',checkpoint=self.last_checkpoint)
            self.get_system_settings(None)
            self.detector_history_known=False;self.detector_records={}
            return dict(before=before,after=after,**native_result,checkpoint=self.last_checkpoint,source='IConvertToNSCGroup',
                model_effect='working design converted; checkpoint retains sequential baseline',
                follow_up='mixed-mode object access uses explicit nsc_surface; pure NSC may use tracing/detector tools',
                validation='native conversion result; independent critical-ray equivalence remains a separate check')
        return self._start_task('nsc_conversion',tool,dict(request=q.model_dump(),actual=actual),before=before,collector=collect)
