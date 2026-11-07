"""Dedicated critical and single NSC ray settings and structured native results."""
import math,shutil,uuid
from pathlib import Path
from .data import unwrap
from .errors import ZemaxError
from .files import input_path
from .analyses import scalar_settings
from .imaging import new_analysis,checked,check,select
from .imaging import collect_imaging
from .detectors import check_setting_value
from .path_analysis import finite

CRITICAL=dict(position_tolerance='PositionTolerance',angle_tolerance_deg='AngleTolerance',rays_to_display='RaysToDisplay',display_xyz='DisplayXYZ',display_lmn='DisplayLMN',display_actual_end_data='DisplayActualEndData',display_target_end_data='DisplayTargetEndData',display_start_data='DisplayStartData')
SINGLE=dict(x='RaySourceX',y='RaySourceY',z='RaySourceZ',l='RaySourceL',m='RaySourceM',n='RaySourceN',reference_object='RefObject',split_rays='SplitNSCRays',scatter_rays='ScatterNSCRays',use_polarization='UsePolarization',show_xyz='ShowXYZ',show_lmn='ShowLMN',show_path='ShowPath',show_normal='ShowNormal',show_electric_field='ShowExyz',expand_into_branches='ExpandIntoBranches',decimal_precision='DecimalPrecision')
SEGMENT_NAMES=['segment_level','segment_parent','hit_object','hit_face','inside_of','status','x','y','z','l','m','n','ex_real','ex_imag','ey_real','ey_imag','ez_real','ez_imag','intensity','path_length','xy_bin','lm_bin','x_normal','y_normal','z_normal','index','starting_phase','phase_of','phase_at']

def configure_nsc_surface_sag(q,set_setting,zrd_path=None):
    values={
        'ObjectNumber':q.object_number,'FaceNumber':q.face_number,'Sampling':q.sampling,
        'Data':q.data,'ShowAs':q.show_as,'RemoveOption':q.remove_option,
        'BestFitSphereOption':q.best_fit_sphere_option,'KeepZRD':q.keep_zrd,
    }
    optional={
        'Offset':q.offset,'Width':q.width,'Rotation':q.rotation,'Decenter_X':q.decenter_x,
        'Decenter_Y':q.decenter_y,'ContourFormat':q.contour_format,
        'BFSReverseDirection':q.bfs_reverse_direction,'KeepObjectTilts':q.keep_object_tilts,
        'ProbeRayOffset':q.probe_ray_offset,
    }
    if zrd_path is not None:optional['ZRDFilename']=str(zrd_path)
    values.update({name:value for name,value in optional.items() if value is not None})
    for name,value in values.items():set_setting(name,value)
    return values


def run_nsc_surface_sag(backend,q):
    backend._require_nsc();backend._require_work();backend._object(q.object_number)
    zrd_path=None
    if q.keep_zrd:
        zrd_path=Path(str(backend.system.SystemFile)).parent/q.zrd_filename
        if zrd_path.exists():raise ZemaxError('RESOURCE_EXISTS','指定的ZRD输出文件已存在。',path=str(zrd_path))
    tool=new_analysis(backend,'NSCSurfaceSag')
    try:
        s=unwrap(tool.GetSettings())
        values=configure_nsc_surface_sag(q,lambda name,value:checked(backend.native,s,name,value),zrd_path.name if zrd_path is not None else None)
        for name,value in values.items():check(backend.native,s,name,value)
        actual=scalar_settings(s)
        if actual.get('unavailable_fields'):
            raise ZemaxError('SETTING_UNAVAILABLE','NSC曲面Sag设置回读失败。',details=actual['unavailable_fields'])
        settings=dict(kind=q.kind,requested=q.model_dump(),native=actual,lens_units=str(backend.system.SystemData.Units.LensUnits))
        if zrd_path is not None:settings['zrd_output_path']=str(zrd_path)
    except Exception as exc:
        holder={'native':tool}
        if not backend._close_task_native(holder):
            failure=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
            failure.details['cleanup_warnings']=holder.get('cleanup_warnings',[])
            if failure is not exc:raise failure from exc
        raise

    def collect(task):
        result=backend._collect_general_analysis(task)
        samples=[v for grid in result.get('grids',[])for row in grid['values']for v in row]
        samples.extend(v for series in result.get('series',[])for row in series['y']for v in row)
        if not any(v is not None for v in samples):
            raise ZemaxError('NO_RESULT_DATA','NSC曲面Sag未返回有效采样点。',artifacts=result.get('artifacts',[]),native_messages=result.get('native_messages',[]),native_preamble=result.get('native_preamble',[]))
        result['sampling_summary']=dict(valid_samples=sum(v is not None for v in samples),invalid_samples=sum(v is None for v in samples))
        for grid in result.get('grids',[]):
            grid.update(array_order='values[y][x]',coordinate_unit=task['settings']['lens_units'],value_unit=task['settings']['lens_units'],
                coordinate_definition='native sag sampling plane; min + index * step, including endpoints; native decenter/rotation/tilt settings retained')
        result['lens_units']=task['settings']['lens_units']
        result['coordinates']='native NSC surface/object coordinates; axes and values retained from native labels'
        if zrd_path is not None:
            if zrd_path.is_file():result['artifacts'].append(dict(kind='zrd',path=str(zrd_path)))
            else:result['zrd_export_error']='Native analysis completed without creating the requested ZRD file.'
        return result

    return backend._start_task(q.kind,tool,settings,analysis=True,collector=collect)


def report(backend,task,r):
    result=dict(analysis_kind=task['settings']['kind'],computation_method='native_analysis',rows=[],artifacts=[],
        native_header=[str(x)for x in r.HeaderData.Lines]if r.HeaderData is not None else [],native_messages=[dict(code=str(r.GetMessageAt(i).ErrorCode),text=str(r.GetMessageAt(i).Text))for i in range(r.NumberOfMessages)])
    path=backend.directory/(task['task_id']+'_native.txt')
    try:
        if r.GetTextFile(str(path)):result['artifacts'].append(dict(kind='native_text',path=str(path)))
        else:result['native_export_error']='GetTextFile returned false'
    except Exception as exc:result['native_export_error']=dict(type=type(exc).__name__,message=str(exc))
    return result


def collect_critical(backend,task,r):
    data=unwrap(r.CriticalRayData)
    if data is None:raise ZemaxError('RESULT_UNAVAILABLE','原生未提供CriticalRayData。',native_report=report(backend,task,r))
    count=int(data.NumRays)
    if not 0<=count<=127008:raise ZemaxError('RESULT_TOO_LARGE','关键光线数量超出原生127008上限。',count=count)
    rays=list(data.Rays)
    if len(rays)!=count:raise ZemaxError('INVALID_RESULT_DATA','关键光线数量与数组不符。',declared=count,actual=len(rays))
    result=report(backend,task,r)
    for i,ray in enumerate(rays):
        ray=unwrap(ray)
        row=dict(native_index=i,field=int(ray.FieldPoint),ray_type=str(ray.RayType),passed=bool(ray.Pass),termination_object=int(ray.TerminationObject),wavelength_um=finite(ray.Wavelength,'Wavelength'))
        for label,suffix in [('input','In'),('target','Target'),('actual','Actual')]:
            row[label+'_position']=[finite(getattr(ray,axis+suffix),axis+suffix)for axis in 'XYZ']
            row[label+'_direction']=[finite(getattr(ray,axis+suffix),axis+suffix)for axis in 'LMN']
        result['rows'].append(row)
    scope=task['settings']['requested']['rays_to_display']
    native_passed=sum(x['passed']for x in result['rows'])
    result['native_data_scope']=dict(returned_rays=count,passed=native_passed,failed=count-native_passed,
        selection_method='adapter filters native dedicated rows by requested display scope')
    if scope!='AllRays':result['rows']=[row for row in result['rows']if row['passed']==(scope=='PassedRays')]
    returned=len(result['rows']);passed=sum(x['passed']for x in result['rows'])
    result.update(native_labels=[str(x)for x in data.HeaderLabels],summary=dict(returned_rays=returned,returned_passed=passed,returned_failed=returned-passed,scope=scope),
        units=dict(position=str(backend.system.SystemData.Units.LensUnits),direction='direction cosines',wavelength='um',angle_tolerance='degrees'),
        pass_definition='native target detector termination plus position and angle tolerances; errors ignored, polarization/splitting/scattering disabled by native CRT')
    return result


def read_segment(data,index,native):
    from System import Int32,Double
    status=native.enum(native.api.Tools.RayTrace.RayStatus,'Parent')
    return data.ReadSegmentFull(Int32(index),*([Int32(0)]*5+[status]+[Double(0)]*14+[Int32(0)]*2+[Double(0)]*7))


def collect_single(backend,task,r):
    data=unwrap(r.NSCSingleRayTraceData)
    if data is None or not data.IsValid:raise ZemaxError('RESULT_UNAVAILABLE','原生未提供有效NSCSingleRayTraceData。',native_report=report(backend,task,r))
    total=int(data.NumberOfSegments)
    if total<0:raise ZemaxError('INVALID_RESULT_DATA','原生光线段数为负数。',count=total)
    result=report(backend,task,r)
    for i in range(1,min(total,task['settings']['requested']['max_segments'])+1):
        out=read_segment(data,i,backend.native)
        if len(out)!=30 or not out[0]:raise ZemaxError('RESULT_READ_FAILED','ReadSegmentFull未返回有效光线段。',native_segment_index=i,returned_length=len(out))
        row=dict(native_segment_index=i)
        for name,value in zip(SEGMENT_NAMES,out[1:]):
            row[name]=str(value)if name=='status'else int(value)if name in SEGMENT_NAMES[:5]+['xy_bin','lm_bin']else finite(value,name)
        result['rows'].append(row)
    result.update(summary=dict(native_segments=total,returned_segments=len(result['rows']),truncated=total>len(result['rows']),wave_index=int(data.WaveIndex),wavelength_um=finite(data.WavelengthUM,'WavelengthUM')),
        units=dict(position=str(backend.system.SystemData.Units.LensUnits),path_length='lens units, physical distance from parent',phase='radians at detector',direction='direction cosines',coordinates='NSC global; input relative to selected reference object',intensity='native normalized launch intensity'))
    database=Path(str(data.ZRDFile))
    if str(data.ZRDFile) and not database.is_absolute():
        database=Path(str(backend.system.SystemFile)).parent/database
    result['native_database_file']=str(data.ZRDFile)
    configured=task['settings'].get('database_output_path')
    if configured and Path(configured).is_file():
        database=Path(configured)
        result['database_path_source']='adopted_SaveRaysFile'
    else:result['database_path_source']='native_ZRDFile'
    if database.is_file():result['artifacts'].append(dict(kind='zrd',path=str(database)))
    else:result['database_export_error']='native returned no existing ZRD file; structured segments retained'
    return result


def run_nsc_analysis(backend,q):
    backend._require_nsc();backend._require_work()
    critical=q.kind=='critical_ray_trace'
    if critical:
        source=input_path(q.path,{'.crs'})
        working=Path(str(backend.system.SystemFile)).parent/('critical_'+uuid.uuid4().hex+'.CRS')
        shutil.copyfile(source,working);backend.system.UpdateFileLists()
    else:
        if q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。')
        if q.reference_object>backend.system.NCE.NumberOfObjects:raise ZemaxError('INDEX_OUT_OF_RANGE','参考对象编号越界。')
    tool=new_analysis(backend,'CriticalRayTracer'if critical else'NSCSingleRayTrace')
    try:
        s=unwrap(tool.GetSettings());mapping=CRITICAL if critical else SINGLE
        values={name:getattr(q,key)for key,name in mapping.items()}
        # Single-ray SaveRaysFile resolves a file name beside SystemFile.
        database=Path(str(backend.system.SystemFile)).parent/('single_'+uuid.uuid4().hex+'.zrd') if not critical else None
        values['Filename'if critical else'SaveRaysFile']=str(working) if critical else database.name
        if not critical:select(s.Wavelength,'Wavelength',q.wavelength)
        # Polarization is enabled before ray splitting; final readback checks the combination.
        if not critical:checked(backend.native,s,'UsePolarization',q.use_polarization)
        for name,value in values.items():checked(backend.native,s,name,value)
        for name,value in values.items():check(backend.native,s,name,value)
        if not critical:check_setting_value('Wavelength',q.wavelength,int(s.Wavelength.GetWavelengthNumber()))
        actual=scalar_settings(s)
        if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','原生光线设置回读失败。',details=actual['unavailable_fields'])
        settings=dict(kind=q.kind,requested=q.model_dump(),native=actual)
        if critical:settings.update(source_file=str(source),working_file=str(working))
        else:settings['database_output_path']=str(database)
    except Exception as exc:
        holder={'native':tool}
        if not backend._close_task_native(holder):
            failure=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
            failure.details['cleanup_warnings']=holder.get('cleanup_warnings',[])
            if failure is not exc:raise failure from exc
        raise
    def collect(task):
        r=unwrap(task['native'].GetResults())
        if r is None or not r.IsValid:raise ZemaxError('ANALYSIS_FAILED','光线分析没有有效原生结果。')
        return (collect_critical if critical else collect_single)(backend,task,r)
    return backend._start_task(q.kind,tool,settings,analysis=True,collector=collect)
