"""Optical power maps using explicit, read-only native POWF/POWP queries."""
import math
from typing import Annotated, Literal
from pydantic import Field
from .schema import Request, PositiveIndex, FiniteFloat, Positive
from .errors import ZemaxError
from .ray_diagrams import native_query

DATA = ['Spherical','Cylinder','Maximum','Minimum','Tangential','Sagittal','Y','X','Astigmatic']
Count = Annotated[int, Field(strict=True, ge=3, le=129)]

class PowerMap(Request):
    surface: PositiveIndex
    wavelength: PositiveIndex = 1
    data_type: Literal['Spherical','Cylinder','Maximum','Minimum','Tangential','Sagittal','Y','X','Astigmatic'] = 'Spherical'
    quantity: Literal['Power','EFL'] = 'Power'
    offset: FiniteFloat = 0
    x_points: Count = 11
    y_points: Count = 11

class PowerFieldMap(PowerMap):
    kind: Literal['power_field_map']
    x_field_width: Positive
    y_field_width: Positive
    use_tangent_of_field_angle: bool = False

class PowerPupilMap(PowerMap):
    kind: Literal['power_pupil_map']
    field: PositiveIndex = 1


def arguments(q, hx, hy, px=0., py=0.):
    data=DATA.index(q.data_type)+(9 if q.quantity=='EFL' else 0)
    if q.kind=='power_field_map':return [q.surface,q.wavelength,hx,hy,float(data),0.,0.,0.]
    return [q.surface,q.wavelength,hx,hy,px,py,float(data),0.]


def axis(width, count):
    return [-width/2+width*i/(count-1) for i in range(count)]


def field_axes(q, settings):
    """Return uniform display axes and the physical field coordinates queried."""
    unit='degrees' if settings['field_type']=='Angle' else settings['lens_units']
    if not q.use_tangent_of_field_angle:
        xs=axis(q.x_field_width,q.x_points);ys=axis(q.y_field_width,q.y_points)
        return xs,ys,xs,ys,unit
    if settings['field_type']!='Angle':
        raise ZemaxError('INACTIVE_SETTING','切线视场采样要求角度视场。',
                         setting='use_tangent_of_field_angle',field_type=settings['field_type'])
    if max(q.x_field_width,q.y_field_width)>=180:
        raise ZemaxError('INVALID_ARGUMENT','切线视场总宽度必须小于180度。',
                         x_field_width=q.x_field_width,y_field_width=q.y_field_width)
    xs=axis(2*math.tan(math.radians(q.x_field_width/2)),q.x_points)
    ys=axis(2*math.tan(math.radians(q.y_field_width/2)),q.y_points)
    return xs,ys,[math.degrees(math.atan(v)) for v in xs],[math.degrees(math.atan(v)) for v in ys],'dimensionless tangent'


def run_power_map(b,q):
    from .models import BatchRays
    from .field_analyses import normalized_field
    b._require_sequential();b._require_work();b._row(q.surface)
    settings=b.get_system_settings(None)
    if q.wavelength>len(settings['wavelengths']):raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。')
    pupil=q.kind=='power_pupil_map'
    if pupil and q.field>len(settings['fields']):raise ZemaxError('INDEX_OUT_OF_RANGE','视场编号越界。')
    if not pupil:
        fields=settings['fields']
        sx=max(abs(f['x']) for f in fields);sy=max(abs(f['y']) for f in fields)
        if settings['field_normalization']=='Radial':sx=sy=max(math.hypot(f['x'],f['y']) for f in fields)
        if not sx or not sy:raise ZemaxError('PRECONDITION_FAILED','视场网格需要非零的归一化视场尺度。',x_scale=sx,y_scale=sy)
        if q.x_field_width/2>sx or q.y_field_width/2>sy:raise ZemaxError('INVALID_ARGUMENT','扫描宽度超出当前归一化视场范围。',x_scale=sx,y_scale=sy)
    if pupil:
        xs=axis(2,q.x_points);ys=axis(2,q.y_points)
        field_x=field_y=None;coordinate_unit='normalized pupil'
    else:
        xs,ys,field_x,field_y,coordinate_unit=field_axes(q,settings)
    name='POWP' if pupil else 'POWF';code=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name)
    unit='diopters' if q.quantity=='Power' else settings['lens_units']
    def flow(task):
        coords=[];rays=[]
        fixed=normalized_field(settings['fields'],settings['fields'][q.field-1],settings['field_normalization']) if pupil else None
        for iy,y in enumerate(ys):
            for ix,x in enumerate(xs):
                if pupil and x*x+y*y>1+1e-12:continue
                hx,hy=fixed if pupil else (field_x[ix]/sx,field_y[iy]/sy)
                px,py=(x,y) if pupil else (0.,0.)
                coords.append((iy,ix,hx,hy,px,py));rays.append(dict(hx=hx,hy=hy,px=px,py=py,wavelength=q.wavelength))
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_'+name,
            actual_settings=dict(request=q.model_dump(),configuration=task['context']['configuration'],wavelength_um=settings['wavelengths'][q.wavelength-1]['wavelength_um'],settings_source='explicit native operand arguments; offset applied after query',
                field_sampling='uniform tangent' if not pupil and q.use_tangent_of_field_angle else 'uniform',
                physical_field_x=field_x,physical_field_y=field_y),
            native_interface_limit='Runtime442 thematic settings AS_Default; explicit operand path used',
            ray_validation_scope='central reference ray; native ring validity is not exposed',
            native_ring_validity='unavailable',
            valid_mask_scope='central reference ray passed and native query returned finite value; peripheral native ring status unavailable',
            native_zero_semantics='native zero is retained; mathematical zero, infinite focal length and native failure sentinel are not inferred',
            series=[],grids=[])
        values=[[None]*len(xs) for _ in ys];valid=[[False]*len(xs) for _ in ys]
        for start in range(0,len(rays),1000):
            checked=yield from b._child_job(task,b.run_batch_ray_trace,BatchRays(target_surface=q.surface,rays=rays[start:start+1000]))
            rows=checked['rows']
            if len(rows)!=len(rays[start:start+1000]):raise ZemaxError('INVALID_RESULT_DATA','参考光线数量与网格不一致。')
            for (iy,ix,hx,hy,px,py),ray in zip(coords[start:start+1000],rows,strict=True):
                b._cancel_boundary(task)
                args=arguments(q,hx,hy,px,py);row=dict(index=len(task['rows']),grid_x=ix,grid_y=iy,x=xs[ix],y=ys[iy],native_arguments=args,reference_ray=ray)
                if not pupil:row.update(field_x=field_x[ix],field_y=field_y[iy])
                if ray.get('error_code') or ray.get('vignette_code'):
                    row.update(state='invalid_reference_ray',raw_value=None,value=None,
                        native_query_status='not_executed_invalid_reference_ray',raw_value_state='not_queried',
                        native_ring_validity='unavailable')
                else:
                    raw=native_query(b,code,args);value=raw+q.offset
                    if not math.isfinite(value):raise ZemaxError('INVALID_RESULT_DATA','偏置后数值非有限。',raw_value=raw,offset=q.offset)
                    row.update(state='native_value',raw_value=raw,value=value,
                        native_query_status='returned_finite_value',raw_value_state='native_zero'if raw==0 else'finite_nonzero',
                        native_ring_validity='unavailable')
                    if raw==0:row['zero_interpretation']='unresolved_native_zero_semantics'
                    values[iy][ix]=value;valid[iy][ix]=True
                task['rows'].append(row);yield
        task['payload']['grids']=[dict(grid=0,nx=len(xs),ny=len(ys),min_x=xs[0],min_y=ys[0],dx=xs[1]-xs[0],dy=ys[1]-ys[0],x=xs,y=ys,
            x_label='Pupil X' if pupil else ('tan(Field X)' if q.use_tangent_of_field_angle else 'Field X'),y_label='Pupil Y' if pupil else ('tan(Field Y)' if q.use_tangent_of_field_angle else 'Field Y'),x_unit=coordinate_unit,y_unit=coordinate_unit,
            physical_field_x=field_x,physical_field_y=field_y,
            description=q.data_type+' '+q.quantity,value_unit=unit,array_order='values[y][x]; endpoint samples',values=values,valid_mask=valid,invalid_count=sum(v is None for row in values for v in row),
            valid_mask_scope=task['payload']['valid_mask_scope'],native_ring_validity='unavailable',
            native_zero_count=sum(r['raw_value_state']=='native_zero'for r in task['rows']),
            invalid_reference_ray_count=sum(r['state']=='invalid_reference_ray'for r in task['rows']))]
        task['payload']['structured_data_available']=True
    return b._composite(q.kind,q.model_dump(),flow)
