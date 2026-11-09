"""Full-field spot settings, native report and dedicated spot statistics."""
import math
from pathlib import Path
from .errors import ZemaxError

# IAS_Spot selector 1 evaluates the active configuration. Selector 2 returns
# first-configuration statistics in the controlled two-configuration model.
CURRENT_CONFIGURATION_SELECTOR = 1


def configure(q, write):
    values=dict(Pattern=q.pattern,ReferTo=q.reference,ShowScale=q.show_scale,ColorRaysBy=q.color_rays_by,
        RayDensity=q.ray_density,Configuration=CURRENT_CONFIGURATION_SELECTOR,DirectionCosines=q.direction_cosines,
        UseSymbols=q.use_symbols,UsePolarization=q.use_polarization,ScatterRays=q.scatter_rays,
        ShowAiryDisk=q.show_airy_disk,IgnoreLateralColor=q.ignore_lateral_color,PlotScale=q.plot_scale,
        DeltaFocus=0.,Exaggerate=q.exaggerate)
    for name,value in values.items():write(name,value)
    return values


def run_full_field(backend,q):
    from .data import unwrap
    from .analyses import scalar_settings
    from .imaging import new_analysis,checked,check,select
    from .detectors import check_setting_value
    backend._require_sequential(focused=True);backend._require_work()
    if q.field>backend.system.SystemData.Fields.NumberOfFields or q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','全视场光斑视场或波长越界。')
    surface=q.surface if q.surface is not None else backend.system.LDE.NumberOfSurfaces-1
    backend._row(surface)
    tool=new_analysis(backend,'FullFieldSpot')
    if tool is None:raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE','全视场光斑工厂返回空对象。')
    try:
        s=unwrap(tool.GetSettings())
        select(s.Field,'Field',q.field);select(s.Wavelength,'Wavelength',q.wavelength);select(s.Surface,'Surface',surface)
        values=configure(q,lambda n,v:checked(backend.native,s,n,v))
        for name,value in values.items():check(backend.native,s,name,value)
        for name,number in [('Field',q.field),('Wavelength',q.wavelength),('Surface',surface)]:
            check_setting_value(name,number,int(getattr(getattr(s,name),'Get'+name+'Number')()))
        actual=scalar_settings(s)
        if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','全视场光斑设置回读失败。',details=actual['unavailable_fields'])
        settings=dict(kind=q.kind,requested=q.model_dump(),native=actual,
            resolved_configuration=int(backend.system.MCE.CurrentConfiguration))
    except Exception as exc:
        owner=dict(native=tool)
        if not backend._close_task_native(owner)and isinstance(exc,ZemaxError):exc.details['cleanup_warnings']=owner.get('cleanup_warnings',[])
        raise
    def collect(task):
        try:result=backend._collect_general_analysis(task)
        except ZemaxError as exc:
            if exc.code!='EXPORT_FAILED':raise
            from .nsc_analyses import report
            result=report(backend,task,unwrap(task['native'].GetResults()))
            result['native_text_export_error']=exc.as_dict()
        native=unwrap(task['native'].GetResults());spot=unwrap(native.SpotData)
        metrics=[]
        if spot is not None:
            fields=[q.field]if q.field else range(1,int(spot.NumberOfFields)+1)
            for field in fields:
                row=dict(field_number=field,wavelength_selection=q.wavelength,native_wavelength_slot=1,
                    rms_radius=float(spot.GetRMSSpotSizeFor(field,1)),geo_radius=float(spot.GetGeoSpotSizeFor(field,1)),
                    reference_x=float(spot.GetReferenceCoordinate_X_For(field,1)),reference_y=float(spot.GetReferenceCoordinate_Y_For(field,1)))
                if not all(math.isfinite(row[k])for k in ['rms_radius','geo_radius','reference_x','reference_y']):
                    raise ZemaxError('INVALID_RESULT_DATA','全视场光斑统计含非有限数值。',row=row,artifacts=result['artifacts'])
                if row['rms_radius']<0 or row['geo_radius']<0:
                    raise ZemaxError('INVALID_RESULT_DATA','全视场光斑统计半径为负值。',row=row,artifacts=result['artifacts'])
                metrics.append(row)
        path=next((a['path']for a in result['artifacts']if a['kind']=='native_text'),None)
        rows=[dict(line=i,text=line)for i,line in enumerate(Path(path).read_text(encoding='utf-16').splitlines(),1)]if path else metrics
        if not rows:
            result['native_result_counts']={name:int(getattr(native,name))for name in ['NumberOfDataSeries','NumberOfDataSeriesRgb','NumberOfDataGrids','NumberOfDataGridsRgb',
                'NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb','NumberOfRayData','NumberOfMessages']}
            raise ZemaxError('RESULT_UNAVAILABLE','全视场光斑未提供文本或SpotData。',native_report=result)
        result.update(analysis_kind=q.kind,metrics=metrics,rows=rows,
            radius_unit='dimensionless'if q.direction_cosines else'micrometers',
            reference_coordinate_unit='dimensionless'if q.direction_cosines else'lens units',
            coordinate_quantity='direction_cosines'if q.direction_cosines else'surface_local_intercepts',
            native_wavelength_slot=1,
            display_reference='shared reference for all fields; ChiefRay uses field1',display_exaggeration=q.exaggerate,
            statistics_source='native SpotData, wavelength selection aggregate; no per-wavelength duplication')
        result['structured_data_available']=bool(result['rows']or metrics or result.get('series'))
        return result
    return backend._start_task(q.kind,tool,settings,analysis=True,collector=collect)
