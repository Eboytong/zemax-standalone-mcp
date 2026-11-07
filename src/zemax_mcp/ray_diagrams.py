"""Read-only first-order diagrams and signed image-plane ray incidence scans."""
import math
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,Index,PositiveIndex,FiniteFloat
from .errors import ZemaxError

class YYbarDiagram(Request):
    kind: Literal['yybar_diagram']
    first_surface: Index = 1
    last_surface: Index | None = None
    wavelength: PositiveIndex = 1
    plot_scale: Annotated[FiniteFloat,Field(ge=0)] = 0

    @model_validator(mode='after')
    def ordered(self):
        if self.last_surface is not None and self.last_surface<self.first_surface:
            raise ValueError('last_surface必须不早于first_surface。')
        return self

class IncidentAngleVsImageHeight(Request):
    kind: Literal['incident_angle_vs_image_height']
    wavelength: PositiveIndex = 1
    field_density: Annotated[int,Field(strict=True,ge=2,le=1001)] = 21


def native_query(b,code,args):
    try:value=float(b.system.MFE.GetOperandValue(code,*args))
    except Exception as exc:raise ZemaxError('NATIVE_ERROR','原生光线操作数查询失败。',operand=str(code),arguments=args,native_exception=str(exc),native_exception_type=type(exc).__name__)from exc
    if not math.isfinite(value):raise ZemaxError('INVALID_RESULT_DATA','原生光线操作数返回非有限值。',operand=str(code),arguments=args,value=str(value))
    return value


def run_yybar(b,q):
    from .models import BatchRays
    b._require_sequential();b._require_work()
    last=int(b.system.LDE.NumberOfSurfaces)-1 if q.last_surface is None else q.last_surface
    b._row(q.first_surface);b._row(last)
    if q.wavelength>b.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。',wavelength=q.wavelength)
    code=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,'PARY')
    def flow(task):
        unit=task['context']['lens_units']
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_PARY',
            actual_settings=dict(request=q.model_dump(),first_surface=q.first_surface,last_surface=last,
                wavelength_um=task['system_settings']['wavelengths'][q.wavelength-1]['wavelength_um'],
                configuration=task['context']['configuration'],settings_source='explicit native PARY arguments; plot_scale applied by renderer'),
            unit=unit,axis_definition='x=chief ray Y-bar, y=axial marginal ray Y; each point is a lens surface',
            normalized_rays=dict(chief=dict(hx=0,hy=1,px=0,py=0),marginal=dict(hx=0,hy=0,px=0,py=1)),
            resource_ownership='native PARY queries plus owned native batch trace validity checks; each batch tool closed by child task',validation_task_ids=[],series=[])
        for surface in range(q.first_surface,last+1):
            validation=yield from b._child_job(task,b.run_batch_ray_trace,BatchRays(ray_type='Paraxial',target_surface=surface,
                rays=[dict(hx=0.,hy=1.,px=0.,py=0.,wavelength=q.wavelength),dict(hx=0.,hy=0.,px=0.,py=1.,wavelength=q.wavelength)]))
            task['payload']['validation_task_ids'].append(validation['task']['task_id'])
            checked=validation['rows']
            if len(checked)!=2 or any(r.get('error_code')!=0 or not r.get('position') for r in checked):
                raise ZemaxError('INVALID_RAY_DATA','Y-Ybar原生近轴追迹未取得有效光线。',surface=surface,rays=checked)
            row=dict(index=len(task['rows']),surface=surface,native_arguments={},validation_rays=checked)
            for key,hy,py in [('chief_y',1.,0.),('marginal_y',0.,1.)]:
                b._cancel_boundary(task);args=[surface,q.wavelength,0.,hy,0.,py,0.,0.]
                row[key]=native_query(b,code,args);row['native_arguments'][key]=args
                yield
            row['state']='succeeded';task['rows'].append(row)
        scale=q.plot_scale or max(abs(r[key])for r in task['rows']for key in ('chief_y','marginal_y')) or 1.
        task['payload']['actual_settings']['effective_plot_scale']=scale
        task['payload']['series']=[dict(series=0,description='Y-Ybar diagram',labels=['Marginal Y ('+unit+')'],
            x_label='Chief Y-bar',x_unit=unit,y_label='Marginal Y',y_unit=unit,value_units=[unit],
            x=[r['chief_y']for r in task['rows']],y=[[r['marginal_y']]for r in task['rows']],
            point_labels=[str(r['surface'])for r in task['rows']],axis_limits=[-scale,scale],aspect='equal')]
    return b._composite(q.kind,q.model_dump(),flow)


def signed_plane_angle(direction):
    l,m,n=direction
    if not all(math.isfinite(v)for v in direction) or not math.isclose(l*l+m*m+n*n,1,rel_tol=1e-7,abs_tol=1e-8):
        raise ZemaxError('INVALID_RESULT_DATA','原生光线方向不是有限单位向量。',direction=direction)
    return math.degrees(math.atan(m/n)) if n else math.copysign(90.,m)


def incoming_trace(b,parent,request,target):
    """Trace to the incident side of image refraction in an owned native copy."""
    from types import SimpleNamespace
    from .speos import OwnedCopyTool
    image=b.system.LDE.GetSurfaceAt(target);material=str(image.Material);image_type=str(image.Type)
    if not material:
        return (yield from b._child_job(parent,b.run_batch_ray_trace,request))
    source=b.system;copy=source.CopySystem()
    if copy is None:raise ZemaxError('COPY_FAILED','无法创建像面入射方向分析副本。')
    owned=OwnedCopyTool(copy);original=None
    info=dict(source_system_id=int(source.SystemID),analysis_system_id=int(copy.SystemID),
              original_image_material=material,original_image_type=image_type,copy_image_material=None,closed=False)
    parent['payload']['incoming_trace_copy']=info
    try:
        row=copy.LDE.GetSurfaceAt(target)
        if str(row.MaterialCell.GetSolveData().Type)!='Fixed':
            fixed=row.MaterialCell.CreateSolveType(b.native.enum(b.native.api.Editors.SolveType,'Fixed'))
            row.MaterialCell.SetSolveData(fixed)
        row.Material=''
        info['copy_image_material']=str(row.Material)
        if info['copy_image_material']:
            raise ZemaxError('SETTING_REJECTED','分析副本未移除像面折射。',actual_material=info['copy_image_material'])
        def close_tool(task):
            owned.tool=task['native'];owned.tool_closed=b._close_task_native(task)
            return owned.tool_closed
        owner=SimpleNamespace(system=copy,native=b.native,_cancel_boundary=b._cancel_boundary,_close_task_native=close_tool)
        def launch(_):
            return b._composite('incident_incoming_trace',dict(request=request.model_dump(),analysis_system_id=int(copy.SystemID)),
                lambda task:b._trace_flow.__func__(owner,task,request,target))
        if image_type not in ('Standard','CoordinateBreak'):
            geometry=yield from b._child_job(parent,launch,None)
            valid=[r for r in geometry['rows']if r.get('error_code')==0 and r.get('position') and r.get('surface_normal')]
            if not valid or any(abs(r['position'][2])>1e-10 or abs(r['surface_normal'][0])>1e-10 or abs(r['surface_normal'][1])>1e-10 for r in valid):
                raise ZemaxError('PRECONDITION_FAILED','材料像面在追迹位置未确认平面几何。',surface=target,source_type=image_type,validation_task=geometry['task']['task_id'])
            info['geometry_validation_task_id']=geometry['task']['task_id']
            row.ChangeType(row.GetSurfaceTypeSettings(b.native.enum(b.native.api.Editors.LDE.SurfaceType,'Standard')))
            row=copy.LDE.GetSurfaceAt(target);row.Radius=float('inf');row.Conic=0.;row.Material=''
            info['copy_image_type']=str(row.Type)
            if info['copy_image_type']!='Standard':raise ZemaxError('SETTING_REJECTED','材料副本像面未采用平面类型。',actual_type=info['copy_image_type'])
        result=yield from b._child_job(parent,launch,None)
        if str(row.Material):raise ZemaxError('SETTING_REJECTED','像面材料在分析副本追迹时被重新采用。',actual_material=str(row.Material))
        return result
    except BaseException as exc:
        original=exc
        raise
    finally:
        try:
            b._release_owned(owned);info['closed']=True
        except Exception as cleanup:
            b.requires_reconnect=True;info['cleanup_error']=str(cleanup)
            if isinstance(original,ZemaxError):original.details['cleanup_error']=str(cleanup)
            elif original is None:raise
            else:raise ZemaxError('CLEANUP_FAILED','像面分析副本未确认关闭。',
                original_error=dict(type=type(original).__name__,message=str(original)),cleanup_error=str(cleanup))from original


def run_incident_angle(b,q):
    from .models import BatchRays
    from .field_analyses import normalized_field
    b._require_sequential();b._require_work()
    target=int(b.system.LDE.NumberOfSurfaces)-1;image=b._row(target)
    radius=float(image.Radius)
    if math.isnan(radius) or (math.isfinite(radius) and radius!=0):
        raise ZemaxError('PRECONDITION_FAILED','入射角随像高的原生定义要求平面像面。',surface=target,radius=str(radius))
    if q.wavelength>b.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。',wavelength=q.wavelength)
    def flow(task):
        settings=task['system_settings'];unit=task['context']['lens_units'];fields=settings['fields']
        maximum=max((math.hypot(f['x'],f['y'])if settings['field_normalization']=='Radial'else abs(f['y']))for f in fields);jobs=[];rays=[]
        for i in range(q.field_density):
            value=maximum*i/(q.field_density-1)
            hx,hy=normalized_field(fields,dict(x=0.,y=value),settings['field_normalization'])
            jobs.append(dict(field_y=value,hx=hx,hy=hy))
            rays.extend(dict(hx=hx,hy=hy,px=0.,py=py,wavelength=q.wavelength)for py in [-1.,0.,1.])
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_normalized_real_batch_trace',
            actual_settings=dict(request=q.model_dump(),target_surface=target,field_range=[0.,maximum],
                field_normalization=settings['field_normalization'],field_range_source='normalized +Y scan Hy=0..1; radial maximum field radius or rectangular maximum absolute Y',configuration=task['context']['configuration'],
                wavelength_um=settings['wavelengths'][q.wavelength-1]['wavelength_um'],settings_source='explicit native batch ray arguments'),
            field_unit='degrees'if settings['field_type']=='Angle'else unit,image_height_unit=unit,angle_unit='degrees',
            angle_definition='signed local Y-Z incidence atan(m/n) on planar image; front/back propagation referenced to local plane',
            incoming_direction_source='native batch trace; material-bearing image uses an independent neutral planar copy; material-free image retains native image-type behavior',
            supported_native_domain='rotationally symmetric system without vignetting and planar image',series=[])
        result=yield from incoming_trace(b,task,BatchRays(rays=rays,target_surface=target),target)
        task['payload']['ray_trace_task_id']=result['task']['task_id']
        counts=dict(launched=len(rays),succeeded=0,vignetted=0,error=0,missing=0,invalid=0)
        for i,job in enumerate(jobs):
            b._cancel_boundary(task);traced=result['rows'][3*i:3*i+3];angles=[]
            for ray in traced:
                state=ray['state'];counts[state if state in counts else 'invalid']+=1
                angle=None
                if state=='succeeded':
                    normal=ray.get('surface_normal')
                    if normal and (abs(normal[0])>1e-10 or abs(normal[1])>1e-10):
                        counts['succeeded']-=1;counts['invalid']+=1;ray['state']='nonplanar_image_normal'
                    else:angle=signed_plane_angle(ray['direction'])
                angles.append(angle)
            chief=traced[1];height=float(chief['position'][1])if chief['state']=='succeeded'else None
            if height is not None and not math.isfinite(height):raise ZemaxError('INVALID_RESULT_DATA','原生主光线像高非有限。',ray=chief)
            task['rows'].append(dict(index=i,**job,image_height=height,lower_angle_deg=angles[0],chief_angle_deg=angles[1],upper_angle_deg=angles[2],
                rays=traced,state='succeeded'if all(a is not None for a in angles)else 'partial'))
            yield
        task['summary']=counts
        task['payload']['trace_conditions_met']=counts['succeeded']==len(rays)
        if not counts['succeeded'] or not any(r['image_height'] is not None and any(r[k] is not None for k in ('lower_angle_deg','chief_angle_deg','upper_angle_deg'))for r in task['rows']):raise ZemaxError('NO_VALID_RAYS','三条光线均未取得有效像面入射角。',counts=counts)
        task['payload']['series']=[dict(series=0,description='Incident angle vs image height',
            labels=['Lower pupil (deg)','Chief (deg)','Upper pupil (deg)'],value_units=['degrees']*3,
            x_label='Chief image Y',x_unit=unit,y_label='Signed incident angle',y_unit='degrees',
            x=[r['image_height']for r in task['rows']],y=[[r[k]for k in ['lower_angle_deg','chief_angle_deg','upper_angle_deg']]for r in task['rows']],
            invalid_count=sum(a is None for r in task['rows']for a in [r['lower_angle_deg'],r['chief_angle_deg'],r['upper_angle_deg']]))]
    return b._composite(q.kind,q.model_dump(),flow)
