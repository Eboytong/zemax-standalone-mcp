"""Native coating scans and explicit layer setting/pickup readback."""
from .data import unwrap
from .errors import ZemaxError
from .detectors import check_setting_value
from .imaging import new_analysis, checked, check, select, collect_imaging
from .analyses import scalar_settings
from contextlib import contextmanager
import math

METRICS=['reflection','transmission','absorption','diattenuation','phase','retardance']
IDS={metric+'_vs_'+axis:metric.capitalize()+'vs'+axis.capitalize() for metric in METRICS for axis in ['angle','wavelength']}
IDS['coating_listing']='CoatingListing'
ANGLE=dict(minimum_angle='MinAngle',maximum_angle='MaxAngle',reverse_direction='ReverseDirection',minimum_y='MinY',maximum_y='MaxY')
WAVE=dict(angle='Angle',minimum_wavelength_um='MinWavelength',maximum_wavelength_um='MaxWavelength',reverse_direction='ReverseDirection',minimum_y='MinY',maximum_y='MaxY')
LAYER=dict(thickness_multiplier='ThicknessMultiplier',index_offset='IndexOffset',extinction_offset='ExtinctionOffset')
STATUS=dict(thickness_status='Thickness',index_status='Index',extinction_status='Extinction')


class CoatingWavelengthAnalysis:
    """Own a temporary coating analysis system and its wavelength table."""
    def __init__(self,analysis,system,original_id):
        self.analysis=analysis;self.system=system;self.original_id=original_id
        self.closed=False
    def __getattr__(self,name):return getattr(self.analysis,name)
    def Close(self):
        if self.closed:return True
        error=None;result=False
        try:result=self.analysis.Close()
        except Exception as exc:error=exc
        try:system_closed=self.system.Close(False)is not False
        except Exception as exc:
            if error is not None:
                error.add_note('Temporary coating system close also failed: '+str(exc));raise error
            raise
        if error is not None:raise error
        self.closed=result is not False and system_closed
        return self.closed

def configure(backend,s,q):
    if q.kind=='coating_listing':return dict(kind=q.kind,requested=q.model_dump(),native=scalar_settings(s))
    select(s.Surface,'Surface',q.surface)
    # Coating-angle settings use a zero-based wavelength list in installed v242.
    if q.kind.endswith('_angle'):select(s.Wavelength,'Wavelength',q.wavelength-1)
    mapping=ANGLE if q.kind.endswith('_angle')else WAVE
    values={name:getattr(q,key)for key,name in mapping.items()if getattr(q,key)is not None}
    if q.nsc_object is not None:values.update(ObjectNumber=q.nsc_object,FaceNumber=q.nsc_face)
    # Ordinary sequential scans retain inactive NSC selector defaults.
    for name,value in values.items():checked(backend.native,s,name,value)
    for name,value in values.items():check(backend.native,s,name,value)
    check_setting_value('Surface',q.surface,int(s.Surface.GetSurfaceNumber()))
    if q.kind.endswith('_angle'):check_setting_value('Wavelength',q.wavelength-1,int(s.Wavelength.GetWavelengthNumber()))
    actual=scalar_settings(s)
    if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','镀膜设置回读失败。',details=actual['unavailable_fields'])
    if q.kind.endswith('_angle'):
        actual['wavelength_number']=q.wavelength
        actual['wavelength_index_convention']='native zero-based; public one-based'
    return dict(kind=q.kind,requested=q.model_dump(),native=actual)


def label_polarization_result(data,kind,material=''):
    if not data.get('series'):
        raise ZemaxError('NO_RESULT_DATA','镀膜偏振分析没有主曲线。',kind=kind)
    labels={
        'phase':[f'{p} {"reflection" if material.upper()=="MIRROR" else "transmission"} phase' for p in ['S','P']],
        'retardance':['Reflection retardance','Transmission retardance'],
        'diattenuation':['Reflection diattenuation','Transmission diattenuation'],
    }
    metric=kind.split('_vs_',1)[0]
    for index,series in enumerate(data['series']):
        if index>0:
            series['labels_source']='native coefficient table; native labels retained'
            continue
        if len(series['y'])!=len(series['x']) or any(len(row)!=2 for row in series['y']):
            raise ZemaxError('INVALID_RESULT_DATA','镀膜偏振曲线应包含两个已知原生通道。',kind=kind,series=series['series'])
        series['native_labels']=series['labels']
        series['labels']=labels[metric]
        series['labels_source']='official analysis definition and native result header; two native channels'
        series['x_unit']='degrees' if kind.endswith('_angle') else 'micrometers'
        series['y_unit']='degrees' if metric in {'phase','retardance'} else 'dimensionless'
    data['analysis_kind']=kind
    data['coefficient_definition']={'phase':'S/P transmission phase for dielectric interface; reflection phase is selected for MIRROR substrate','phase_unit':'degrees, native OpticStudio propagation convention',
        'retardance':'native S/P phase difference; reflection and transmission channels','retardance_unit':'degrees','diattenuation':'native reflected/transmitted polarization diattenuation','diattenuation_unit':'dimensionless'}[metric]
    return data


def check_wavelength_scan(data,q):
    if not data.get('series') or not data['series'][0].get('x'):
        raise ZemaxError('NO_RESULT_DATA','镀膜波长分析没有带坐标的主曲线。')
    x=data['series'][0]['x'];actual=[min(x),max(x)]
    tolerance=max(1e-10,1e-8*(q.maximum_wavelength_um-q.minimum_wavelength_um))
    if abs(actual[0]-q.minimum_wavelength_um)>tolerance or abs(actual[1]-q.maximum_wavelength_um)>tolerance:
        raise ZemaxError('SETTING_REJECTED','镀膜原生结果横轴没有采用请求的扫描范围。',requested=[q.minimum_wavelength_um,q.maximum_wavelength_um],actual=actual,coordinate_unit='micrometers',tolerance=tolerance)
    return actual


def nsc_coating_target(backend,q):
    editor=backend.system.NCE;pure=str(getattr(backend.system,'Mode','Sequential'))=='NonSequential'
    previous=None if pure else int(editor.ActiveSurface);operation=None
    try:
        if not pure and previous!=q.surface:backend._select_nsc_group(q.surface)
        if not 1<=q.nsc_object<=int(editor.NumberOfObjects):raise ZemaxError('INDEX_OUT_OF_RANGE','NSC镀膜对象编号越界。',object=q.nsc_object,count=int(editor.NumberOfObjects))
        row=editor.GetObjectAt(q.nsc_object);data=row.CoatScatterData
        count=int(data.NumberOfFaces)if data.IsCoatScatterAvailable else 0
        if not 0<=q.nsc_face<count:raise ZemaxError('INDEX_OUT_OF_RANGE','NSC镀膜面编号越界。',face=q.nsc_face,count=count,index_convention='zero-based native optical face group')
        face=data.GetFaceData(q.nsc_face)
        return dict(nsc_object=q.nsc_object,nsc_face=q.nsc_face,material=str(row.Material),coating=str(face.Coating),object_type=str(row.Type),face_count=count,scope='pure_nsc'if pure else'sequential_nsc_component')
    except Exception as exc:
        operation=exc.as_dict()if isinstance(exc,ZemaxError)else dict(message=str(exc),native_type=type(exc).__name__);raise
    finally:
        if not pure and int(editor.ActiveSurface)!=previous:
            try:backend._select_nsc_group(previous)
            except Exception as exc:
                backend.requires_reconnect=True
                raise ZemaxError('RESTORE_FAILED','NSC镀膜预检后活动组恢复失败。',operation_error=operation,native_error=str(exc),restore_surface=previous)from exc


def run_coating(backend,q):
    pure=str(getattr(getattr(backend,'system',None),'Mode','Sequential'))=='NonSequential'
    if not pure or q.kind=='coating_listing':backend._require_sequential()
    target=None
    if q.kind!='coating_listing':
        if pure and(q.surface!=0 or q.nsc_object is None):raise ZemaxError('INVALID_ARGUMENT','纯NSC镀膜扫描使用surface=0及显式对象/面编号。')
        if not pure and q.surface==0:raise ZemaxError('INVALID_ARGUMENT','顺序镀膜扫描需要实际曲面编号。')
        row=None if pure else backend._row(q.surface)
        is_nsc=pure or str(getattr(row,'Type',''))=='NonSequential'
        if is_nsc and q.nsc_object is None:raise ZemaxError('INVALID_ARGUMENT','NSC组件镀膜扫描需要显式nsc_object和nsc_face。')
        if not is_nsc and q.nsc_object is not None:raise ZemaxError('INACTIVE_SETTING','对象/面选择器仅适用于NonSequential组件面。',surface=q.surface)
        if is_nsc:target=nsc_coating_target(backend,q)
        if q.reverse_direction and not is_nsc:
            raise ZemaxError('INACTIVE_SETTING','ReverseDirection 仅对 NonSequential 曲面生效。',
                setting='reverse_direction',surface=q.surface,surface_type=str(row.Type),
                condition_source='Installed v242 manual: Reflection vs Angle, ReverseDirection')
        if q.kind.endswith('_angle') and q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:
            raise ZemaxError('INDEX_OUT_OF_RANGE','镀膜分析波长编号越界。')
    source=backend.system;copy=None
    if q.kind!='coating_listing' and q.kind.endswith('_wavelength'):
        source_waves=source.SystemData.Wavelengths
        primary=next(float(source_waves.GetWavelength(i).Wavelength) for i in range(1,int(source_waves.NumberOfWavelengths)+1) if source_waves.GetWavelength(i).IsPrimary)
        copy=source.CopySystem()
        if copy is None:raise ZemaxError('COPY_FAILED','镀膜波长扫描无法创建独立分析副本。')
        try:
            waves=copy.SystemData.Wavelengths
            while int(waves.NumberOfWavelengths)>1:
                waves.RemoveWavelength(int(waves.NumberOfWavelengths))
            first=waves.GetWavelength(1);first.Wavelength=q.minimum_wavelength_um
            first.Weight=1.0
            if q.maximum_wavelength_um>q.minimum_wavelength_um:
                second=waves.AddWavelength(q.maximum_wavelength_um,1.0)
                if second is None or int(waves.NumberOfWavelengths)!=2:
                    raise ZemaxError('SETTING_REJECTED','镀膜扫描副本未接受最大波长端点。')
            if abs(float(first.Wavelength)-q.minimum_wavelength_um)>1e-10:
                raise ZemaxError('SETTING_REJECTED','镀膜扫描副本未接受最小波长端点。',requested=q.minimum_wavelength_um,actual=float(first.Wavelength))
            if q.maximum_wavelength_um>q.minimum_wavelength_um and abs(float(waves.GetWavelength(2).Wavelength)-q.maximum_wavelength_um)>1e-10:
                raise ZemaxError('SETTING_REJECTED','镀膜扫描副本未接受最大波长端点。',requested=q.maximum_wavelength_um,actual=float(waves.GetWavelength(2).Wavelength))
            selected=next((waves.GetWavelength(i) for i in range(1,int(waves.NumberOfWavelengths)+1) if abs(float(waves.GetWavelength(i).Wavelength)-primary)<1e-12),None)
            if selected is None:selected=waves.AddWavelength(primary,1.0)
            selected.MakePrimary()
            if not selected.IsPrimary or abs(float(selected.Wavelength)-primary)>1e-12:
                raise ZemaxError('SETTING_REJECTED','镀膜扫描副本未保持原主波长；相对膜厚依赖此波长。',primary_wavelength_um=primary)
        except Exception:
            try:
                if copy.Close(False) is False:backend.requires_reconnect=True
            except Exception:backend.requires_reconnect=True
            raise
    if target is not None and copy is None:
        copy=source.CopySystem()
        if copy is None:raise ZemaxError('COPY_FAILED','NSC镀膜扫描无法创建独立副本。')
    if target is not None:
        try:
            editor=copy.NCE
            if not pure and int(editor.ActiveSurface)!=q.surface and (not editor.SetActiveSurface(q.surface)or int(editor.ActiveSurface)!=q.surface):
                raise ZemaxError('SETTING_REJECTED','NSC镀膜副本未采用请求活动组。')
        except Exception:
            if copy.Close(False)is False:backend.requires_reconnect=True
            raise
    try:
        tool=new_analysis(backend if copy is None else type('AnalysisOwner',(),{'system':copy,'native':backend.native})(),IDS[q.kind])
        if copy is not None:tool=CoatingWavelengthAnalysis(tool,copy,int(source.SystemID))
    except Exception:
        if copy is not None:
            try:
                if copy.Close(False) is False:backend.requires_reconnect=True
            except Exception:backend.requires_reconnect=True
        raise
    try:
        analysis_backend=backend if copy is None else type('AnalysisOwner',(),{'native':backend.native,'system':copy})()
        settings=configure(analysis_backend,unwrap(tool.GetSettings()),q)
        if q.kind!='coating_listing':
            row=None if target is not None else(backend._row(q.surface) if copy is None else copy.LDE.GetSurfaceAt(q.surface))
            settings['evaluation_conditions']=dict(surface=q.surface,material=target['material']if target is not None else str(row.Material),coating=target['coating']if target is not None else str(row.CoatingData.Coating),configuration=None if pure else int(source.MCE.CurrentConfiguration),angle_unit='degrees',wavelength_unit='micrometers',coefficient_units='native labels/header; S/P field phase follows native convention',**({'analysis_system_id':int(copy.SystemID),'source_system_id':int(source.SystemID)}if copy is not None else {}))
            if target is not None:settings['evaluation_conditions'].update(target,calculation_source='native NSC coating analysis on owned system copy')
            if copy is not None and q.kind.endswith('_wavelength'):
                settings['evaluation_conditions'].update(wavelength_scan_system_id=int(copy.SystemID),primary_wavelength_um=primary,temporary_wavelengths=[float(waves.GetWavelength(i).Wavelength) for i in range(1,int(waves.NumberOfWavelengths)+1)])
    except Exception:
        holder={'native':tool}
        if not backend._close_task_native(holder):backend.requires_reconnect=True
        raise
    def collect(task):
        result=collect_imaging(backend,task)
        if q.kind!='coating_listing':
            if q.kind.endswith('_wavelength'):
                result['actual_wavelength_scan_um']=check_wavelength_scan(result,q)
            if target is not None:result['coating_target']=settings['evaluation_conditions']
            if q.kind.startswith(('phase_','retardance_','diattenuation_')):
                label_polarization_result(result,q.kind,settings['evaluation_conditions']['material'])
        return result
    return backend._start_task('analysis',tool,settings,analysis=True,collector=collect)


def layer_data(layer):
    return dict(layer=int(layer.Layer),**{key:float(getattr(layer,name))for key,name in LAYER.items()},
        **{key:dict(mode=str(getattr(layer,name+'Status')),pickup_from=int(getattr(layer,name+'PickupFrom')) if str(getattr(layer,name+'Status'))=='Pickup'else None)for key,name in STATUS.items()})


def get_layer(data,index):
    value=unwrap(data.GetLayerSettings(index))
    if value is None or int(value.Layer)!=index:
        raise ZemaxError('INVALID_RESULT_DATA','原生返回的镀膜层编号不符。',requested_layer=index,actual_layer=None if value is None else int(value.Layer))
    return value


@contextmanager
def readable_layers(owner,data):
    if int(data.NumberOfLayers)==0:
        yield
        return
    enabled=bool(data.UseLayerMultiplierAndOffsets)
    original=None
    try:
        if not enabled:
            data.UseLayerMultiplierAndOffsets=True
            check_setting_value('UseLayerMultiplierAndOffsets',True,bool(data.UseLayerMultiplierAndOffsets))
        yield
    except Exception as exc:
        original=exc
        raise
    finally:
        if not enabled:
            try:
                data.UseLayerMultiplierAndOffsets=False
                check_setting_value('UseLayerMultiplierAndOffsets',False,bool(data.UseLayerMultiplierAndOffsets))
            except Exception as restore:
                owner.requires_reconnect=True
                error=original if isinstance(original,ZemaxError) else ZemaxError('LAYER_READ_FAILED',str(original),native_type=type(original).__name__) if original else ZemaxError('RESTORE_FAILED','镀膜层读取后未恢复启用状态。')
                error.details['restore_error']=restore.as_dict() if isinstance(restore,ZemaxError) else dict(message=str(restore))
                raise error from restore


def preflight(data,q,owner):
    total=int(data.NumberOfLayers)
    enabled=q.use_layer_multiplier_and_offsets if q.use_layer_multiplier_and_offsets is not None else bool(data.UseLayerMultiplierAndOffsets)
    if q.layers and not enabled:raise ZemaxError('INACTIVE_SETTING','修改镀膜层参数需要启用层乘数和偏移。')
    with readable_layers(owner,data):
        current={i:layer_data(get_layer(data,i))for i in range(1,total+1)}
    for patch in q.layers:
        if patch.layer not in current:raise ZemaxError('INDEX_OUT_OF_RANGE','镀膜层编号越界。',layer=patch.layer,total=total)
        for key in LAYER:
            status_key=key.split('_')[0]+'_status'
            if getattr(patch,key)is not None and current[patch.layer][status_key]['mode']=='Pickup':
                mode=getattr(patch,status_key)
                if mode is None or mode.mode=='Pickup':raise ZemaxError('SOLVE_CONFLICT','修改拾取层数值须显式切换Fixed或Variable。',layer=patch.layer,property=key)
    for key in STATUS:
        edges={i:v[key]['pickup_from']for i,v in current.items()if v[key]['mode']=='Pickup'}
        for patch in q.layers:
            status=getattr(patch,key)
            if status is None:continue
            edges.pop(patch.layer,None)
            if status.mode=='Pickup':
                if status.layer not in current:raise ZemaxError('INDEX_OUT_OF_RANGE','镀膜拾取源越界。',layer=status.layer)
                edges[patch.layer]=status.layer
        for first in edges:
            visited=set();at=first
            while at in edges:
                if at in visited:raise ZemaxError('PICKUP_CYCLE','镀膜拾取关系包含循环。',property=key,layer=first)
                visited.add(at);at=edges[at]
    return current


def verify_layer(backend,value,patch):
    for key,name in LAYER.items():
        wanted=getattr(patch,key)
        if wanted is not None:check_setting_value(name,wanted,float(getattr(value,name)))
    for key,name in STATUS.items():
        wanted=getattr(patch,key)
        if wanted is None:continue
        actual=getattr(value,name+'Status');expected=backend.native.enum(backend.native.api.Editors.LDE.CoatingStatusType,wanted.mode)
        if not (actual.Equals(expected)if hasattr(actual,'Equals')else actual==expected):raise ZemaxError('SETTING_REJECTED','镀膜层状态未采用。',layer=patch.layer,property=key,requested=wanted.mode,actual=str(actual))
        if wanted.mode=='Pickup':check_setting_value(name+'PickupFrom',wanted.layer,int(getattr(value,name+'PickupFrom')))


class CoatingsMixin:
    def get_coating_rta(self, q):
        self._require_sequential()
        row = self._row(q.surface)
        waves = self.system.SystemData.Wavelengths
        prepared = []
        for condition in q.conditions:
            number = condition.wavelength
            if condition.wavelength_um is not None:
                wavelength = condition.wavelength_um
            else:
                if number is None:
                    number = next((i for i in range(1, int(waves.NumberOfWavelengths)+1)
                                   if waves.GetWavelength(i).IsPrimary), None)
                    if number is None:
                        raise ZemaxError('INVALID_SYSTEM', '系统波长表没有主波长。')
                if number > int(waves.NumberOfWavelengths):
                    raise ZemaxError('INDEX_OUT_OF_RANGE', '波长编号超出系统波长表。', wavelength=number)
                wavelength = float(waves.GetWavelength(number).Wavelength)
            direction = self.native.enum(self.native.api.Editors.DirectionOfRayTravel, condition.direction)
            prepared.append((condition, number, wavelength, direction))
        factory = getattr(row, 'GetCoatingPerformanceData', None)
        if factory is None:
            raise ZemaxError('UNSUPPORTED_INTERFACE', '本机曲面接口缺少GetCoatingPerformanceData。',
                             surface=q.surface, version=self.version)
        data = unwrap(factory())
        if data is None:
            raise ZemaxError('EMPTY_NATIVE_RESULT', '曲面镀膜性能接口返回空对象。', surface=q.surface)
        if int(data.SurfaceNumber) != q.surface:
            raise ZemaxError('RESULT_IDENTITY_MISMATCH', '镀膜性能对象的曲面归属不符。',
                             requested=q.surface, actual=int(data.SurfaceNumber))
        samples = []
        for index, (condition, number, wavelength, direction) in enumerate(prepared):
            try:
                data.GetCoatingPerformance(condition.angle_deg, wavelength, direction)
                values = {}
                for key, native_name in [('reflection', 'Reflection'), ('transmission', 'Transmission'), ('absorption', 'Absorption')]:
                    channels = unwrap(getattr(data, native_name))
                    s, p = float(channels.S), float(channels.P)
                    values[key] = dict(s=s, p=p, unpolarized=(s+p)/2)
                residual = {key: 1-sum(v[key] for v in values.values()) for key in ('s', 'p', 'unpolarized')}
                valid = all(math.isfinite(value) for v in values.values() for value in v.values())
                samples.append(dict(index=index, wavelength=number, wavelength_um=wavelength,
                                    angle_deg=condition.angle_deg, direction=condition.direction,
                                    **values, energy_residual=residual,
                                    status='valid' if valid else 'nonfinite_native_result'))
            except Exception as exc:
                raise ZemaxError('COATING_CALCULATION_FAILED', str(exc), surface=q.surface,
                                 failed_condition=index, completed_samples=samples,
                                 native_exception=type(exc).__name__) from exc
        return dict(surface=q.surface, coating=str(row.Coating),
                    media=dict(before_surface=q.surface-1, before_material=str(self._row(q.surface-1).Material),
                               after_surface=q.surface, after_material=str(row.Material)),
                    configuration=int(self.system.MCE.CurrentConfiguration), samples=samples,
                    total=len(samples), invalid_count=sum(s['status'] != 'valid' for s in samples),
                    units=dict(angle='degrees', wavelength='micrometers', coefficients='dimensionless intensity'),
                    direction_definition='inward: preceding medium to surface medium; outward: reverse',
                    relative_layer_reference='Installed 24.2 direct API uses the query wavelength to convert wave-relative layer thickness; CODA uses the system primary wavelength',
                    source='ILDERow.GetCoatingPerformanceData/GetCoatingPerformance',
                    ownership='row-owned data; no independent analysis or SystemTool created')

    def get_coating_layers(self,q):
        self._require_sequential();data=self._row(q.surface).CoatingData;total=int(data.NumberOfLayers)
        if q.start>total+1:raise ZemaxError('INDEX_OUT_OF_RANGE','镀膜层起点越界。',total=total)
        end=min(total+1,q.start+q.count)
        with readable_layers(self,data):
            rows=[layer_data(get_layer(data,i))for i in range(q.start,end)]
        return dict(surface=q.surface,coating=str(data.Coating),use_layer_multiplier_and_offsets=bool(data.UseLayerMultiplierAndOffsets),
            total=total,rows=rows,next_start=end if end<=total else None,
            definitions=dict(thickness_multiplier='dimensionless multiplier',index_offset='dimensionless refractive index increment',extinction_offset='dimensionless extinction coefficient increment'),
            source='ILDECoatingData/ILDECoatingSettings',activity_source='UseLayerMultiplierAndOffsets; no per-layer IsActive property in installed interface')

    def update_coating_layers(self,q):
        self._require_sequential();data=self._row(q.surface).CoatingData
        before=preflight(data,q,self);enabled_before=bool(data.UseLayerMultiplierAndOffsets);completed=[];prepared=[];failed_layer=None;prop='UseLayerMultiplierAndOffsets'
        self._mutate('coating_layers')
        try:
            if q.use_layer_multiplier_and_offsets is not None:
                data.UseLayerMultiplierAndOffsets=q.use_layer_multiplier_and_offsets
                check_setting_value(prop,q.use_layer_multiplier_and_offsets,bool(data.UseLayerMultiplierAndOffsets))
            # Detach changed pickup edges before installing the validated final graph.
            for patch in q.layers:
                failed_layer=patch.layer;value=get_layer(data,patch.layer);changed=False
                for key,name in STATUS.items():
                    if getattr(patch,key) is not None and str(getattr(value,name+'Status'))=='Pickup':
                        prop=name+'StatusFixed';getattr(value,'Set'+name+'StatusFixed')();changed=True
                if changed:
                    prop='detach_pickup'
                    if not data.SetLayerSettings(patch.layer,value):raise ZemaxError('SETTING_REJECTED','镀膜拾取解除被拒绝。',layer=patch.layer)
                    prepared.append(patch.layer)
            for patch in q.layers:
                failed_layer=patch.layer;value=get_layer(data,patch.layer)
                for key,name in STATUS.items():
                    mode=getattr(patch,key)
                    if mode is None or mode.mode=='Pickup':continue
                    prop=name+'Status';getattr(value,'Set'+name+'Status'+mode.mode)()
                for key,name in LAYER.items():
                    wanted=getattr(patch,key)
                    if wanted is not None:prop=name;setattr(value,name,wanted)
                for key,name in STATUS.items():
                    mode=getattr(patch,key)
                    if mode is not None and mode.mode=='Pickup':
                        prop=name+'StatusPickup'
                        if not getattr(value,'Set'+name+'StatusPickup')(mode.layer):raise ZemaxError('SETTING_REJECTED','镀膜拾取设置被拒绝。',layer=patch.layer,property=key)
                prop='SetLayerSettings'
                if not data.SetLayerSettings(patch.layer,value):raise ZemaxError('SETTING_REJECTED','原生拒绝提交镀膜层设置。',layer=patch.layer)
                verify_layer(self,get_layer(data,patch.layer),patch);completed.append(patch.layer)
            prop='final_readback'
            for patch in q.layers:verify_layer(self,get_layer(data,patch.layer),patch)
            expected=q.use_layer_multiplier_and_offsets if q.use_layer_multiplier_and_offsets is not None else enabled_before
            check_setting_value('UseLayerMultiplierAndOffsets',expected,bool(data.UseLayerMultiplierAndOffsets))
            return dict(surface=q.surface,completed_layers=completed,before=before,after=[layer_data(get_layer(data,p.layer))for p in q.layers],use_layer_multiplier_and_offsets=bool(data.UseLayerMultiplierAndOffsets),checkpoint=self.last_checkpoint)
        except Exception as exc:
            try:state=layer_data(get_layer(data,failed_layer))if failed_layer else None
            except Exception as read_exc:state=dict(read_error=str(read_exc))
            raise ZemaxError('PARTIAL_UPDATE','镀膜层修改未完成。',surface=q.surface,completed_layers=completed,prepared_layers=prepared,failed_layer=failed_layer,failed_property=prop,failed_layer_state=state,checkpoint=self.last_checkpoint,cause=exc.as_dict()if isinstance(exc,ZemaxError)else dict(code='NATIVE_ERROR',message=str(exc)))from exc
