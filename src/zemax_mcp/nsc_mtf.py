"""Detector-based geometric MTF with fixed native cycles/mm and checked Nyquist."""
import shutil,uuid,math
from pathlib import Path
from .data import unwrap
from .errors import ZemaxError
from .files import input_path
from .analyses import scalar_settings
from .imaging import new_analysis,checked,check,collect_imaging
from .detectors import check_setting_value


def detector_sampling(backend,index):
    row=backend._object(index)
    if str(row.Type)!='DetectorRectangle':raise ZemaxError('UNSUPPORTED_DETECTOR','NSC MTF当前适配DetectorRectangle。',actual=str(row.Type))
    data=unwrap(row.ObjectData)
    if int(data.PsfWaveNumber)!=0:raise ZemaxError('CONDITION_NOT_MET','NSC几何MTF要求探测器PsfWaveNumber=0。',actual=int(data.PsfWaveNumber))
    units=str(backend.system.SystemData.Units.LensUnits)
    factor={'Millimeters':1,'Centimeters':10,'Inches':25.4,'Meters':1000}[units]
    nx,ny=int(data.NumberXPixels),int(data.NumberYPixels)
    hx,hy=float(data.XHalfWidth),float(data.YHalfWidth)
    if nx<1 or ny<1 or not all(math.isfinite(v)and v>0 for v in [hx,hy]):raise ZemaxError('INVALID_DETECTOR_DATA','探测器像素尺寸或宽度无效。',nx=nx,ny=ny,x_half_width=hx,y_half_width=hy)
    dx,dy=2*hx*factor/nx,2*hy*factor/ny
    return dict(nx=nx,ny=ny,x_pixel_width_mm=dx,y_pixel_width_mm=dy,nyquist_cycles_per_mm=min(.5/dx,.5/dy),psf_wave_number=0,lens_units=units)


def run_nsc_mtf(backend,q):
    backend._require_nsc();backend._require_work()
    sampling=detector_sampling(backend,q.detector)
    if q.frequencies is not None:
        return run_nsc_mtf_endpoints(backend,q,sampling)
    if q.maximum_frequency>sampling['nyquist_cycles_per_mm']*(1+1e-12):raise ZemaxError('SAMPLING_LIMIT','请求频率超出探测器Nyquist频率，原生超过该频率的结果无效。',requested=q.maximum_frequency,nyquist=sampling['nyquist_cycles_per_mm'],unit='cycles/mm')
    source=working=None
    if q.path:
        source=input_path(q.path,{'.zrd'})
        working=Path(str(backend.system.SystemFile)).parent/('nsc_mtf_'+uuid.uuid4().hex+'.zrd')
        shutil.copyfile(source,working);backend.system.UpdateFileLists()
    provenance=dict(source='ZRD replay',source_file=str(source),working_file=str(working),filter=q.filter)if source else dict(source='current accumulated detector',**backend._detector_provenance(q.detector))
    tool=new_analysis(backend,'NSCGeometricMtf')
    try:
        s=unwrap(tool.GetSettings());s.Detector.SetDetectorNumber(q.detector)
        values=dict(RayDatabaseFilename=working.name if working else'',Filter=q.filter,MaximumFrequency=q.maximum_frequency,MinimumPlotScale=q.minimum_plot_scale,MaximumPlotScale=q.maximum_plot_scale)
        for name,value in values.items():checked(backend.native,s,name,value)
        for name,value in values.items():check(backend.native,s,name,value)
        check_setting_value('Detector',q.detector,int(s.Detector.GetDetectorNumber()))
        actual=scalar_settings(s)
        if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE','NSC MTF设置回读失败。',details=actual['unavailable_fields'])
        actual['Detector']=int(s.Detector.GetDetectorNumber())
        settings=dict(kind=q.kind,requested=q.model_dump(),native=actual,detector_sampling=sampling,provenance=provenance)
    except Exception as exc:
        holder={'native':tool}
        if not backend._close_task_native(holder):
            failure=exc if isinstance(exc,ZemaxError)else ZemaxError('NATIVE_ERROR',str(exc),type=type(exc).__name__)
            failure.details['cleanup_warnings']=holder.get('cleanup_warnings',[])
            if failure is not exc:raise failure from exc
        raise
    def collect(task):
        result=collect_imaging(backend,task)
        if not result.get('series'):raise ZemaxError('RESULT_UNAVAILABLE','NSC MTF没有返回原生曲线。',artifacts=result.get('artifacts'),native_messages=result.get('native_messages'))
        for curve in result['series']:
            curve['x_unit']='cycles/mm';curve['value_units']=['dimensionless MTF']*len(curve['labels'])
        result.update(frequency_unit='cycles/mm',detector_sampling=sampling,provenance=provenance,
                      frequency_sampling='native_display_curve',
                      numerical_precision=dict(source='native serialized display curve',
                          controlled_comparison='interior nodes exceed1e-7+1e-7relative; original values retained',
                          exact_frequency_option='frequencies',evidence='verification/development/NS-03/progress496-endpoint.json'),
                      direction_axes={'Tangential':'detector local Y','Sagittal':'detector local X'},
                      axis_definition='native Tangential/Sagittal labels; detector-local axes; all light at detector unless explicit ZRD filter')
        return result
    return backend._start_task('nsc_geometric_mtf',tool,settings,analysis=True,collector=collect)


def endpoint_values(curves,frequency):
    """Select an actually returned endpoint, without interpolating native values."""
    if not curves:raise ZemaxError('RESULT_UNAVAILABLE','NSC MTF逐点查询没有曲线。',frequency=frequency)
    endpoints=[]
    for index,curve in enumerate(curves):
        x=curve.get('x',[]);y=curve.get('y',[]);labels=curve.get('labels',[])
        node=0 if frequency==0 else len(x)-1
        if not x or len(x)!=len(y)or not labels or len(y[node])!=len(labels):
            raise ZemaxError('INVALID_RESULT_DATA','NSC MTF逐点曲线尺寸不一致。',frequency=frequency,series=index,raw_curve=curve)
        actual=x[node]
        if not isinstance(actual,(int,float))or not math.isfinite(actual)or abs(actual-frequency)>1e-12+1e-12*abs(frequency):
            raise ZemaxError('FREQUENCY_MAPPING_FAILED','NSC MTF原生终点与请求频率不符。',frequency=frequency,actual=actual,series=index)
        values=y[node]
        if any(not isinstance(v,(int,float))or not math.isfinite(v)for v in values):
            raise ZemaxError('INVALID_RESULT_DATA','NSC MTF原生终点包含无效值。',frequency=frequency,series=index,raw_values=values)
        endpoints.append(dict(series=index,labels=labels,values=list(values),native_node=node,native_frequency=actual))
    return endpoints


def run_nsc_mtf_endpoints(b,q,sampling):
    """Use one dedicated native analysis endpoint per requested frequency."""
    if q.frequencies[-1]>sampling['nyquist_cycles_per_mm']*(1+1e-12):
        raise ZemaxError('SAMPLING_LIMIT','请求频率超出探测器Nyquist频率。',requested=q.frequencies[-1],
            nyquist=sampling['nyquist_cycles_per_mm'],unit='cycles/mm')
    if q.path:input_path(q.path,{'.zrd'})
    def flow(task):
        payload=dict(analysis_kind=q.kind,frequency_sampling='native_frequency_endpoints',
            computation_method='one native NSCGeometricMtf analysis per frequency; zero uses returned DC node',
            frequency_unit='cycles/mm',detector_sampling=sampling,series=[],native_queries=[],
            direction_axes={'Tangential':'detector local Y','Sagittal':'detector local X'},
            requested_settings=q.model_dump())
        task['payload']=payload
        for frequency in q.frequencies:
            b._cancel_boundary(task)
            request=q.model_copy(update=dict(frequencies=None,maximum_frequency=frequency))
            result=yield from b._child_job(task,lambda child:run_nsc_mtf(b,child),request)
            curves=result.get('series',[]);endpoints=endpoint_values(curves,frequency)
            if not payload['series']:
                for curve in curves:
                    payload['series'].append({key:value for key,value in curve.items()if key not in {'x','y'}}|dict(x=[],y=[]))
            elif len(curves)!=len(payload['series'])or any(
                curve.get('labels')!=previous['labels'] for curve,previous in zip(curves,payload['series'],strict=True)):
                raise ZemaxError('FREQUENCY_MAPPING_FAILED','NSC MTF逐点查询的曲线身份变化。',
                    frequency=frequency,child_task_id=result['task']['task_id'],raw_curves=curves)
            native_settings=result['task']['settings']['native']
            query=dict(frequency=frequency,child_task_id=result['task']['task_id'],actual_settings=native_settings,
                provenance=result.get('provenance'),endpoints=endpoints,
                native_messages=result.get('native_messages',[]),artifacts=result.get('artifacts',[]))
            payload['native_queries'].append(query)
            for curve,endpoint in zip(payload['series'],endpoints,strict=True):
                curve['x'].append(frequency);curve['y'].append(endpoint['values'])
            task['rows'].append(query)
            task['progress']=100*len(task['rows'])/len(q.frequencies)
            yield
    return b._composite(q.kind,q.model_dump(),flow,require_sequential=False)
