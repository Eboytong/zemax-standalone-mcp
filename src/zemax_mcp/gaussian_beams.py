"""Read-only native Gaussian queries; each result retains operand arguments."""
import math
from .errors import ZemaxError

PARAXIAL=dict(divergence_rad='GBPD',position_from_waist='GBPP',phase_radius='GBPR',
              beam_radius='GBPS',waist_radius='GBPW',rayleigh_range='GBPZ')
SKEW=dict(divergence_rad='GBSD',position_from_waist='GBSP',phase_radius='GBSR',
          beam_radius='GBSS',waist_radius='GBSW')


def native_arguments(q,surface,axis):
    if q.kind=='paraxial_gaussian_beam':
        return [surface,q.wavelength,1. if axis=='X' else 0.,q.waist_radius,q.surface_1_to_waist,q.m2,0.,0.]
    return [q.start_surface,surface,float(q.wavelength),float(q.field),q.start_surface_to_waist,
            -q.waist_radius_x if axis=='X' else q.waist_radius_y,0.,0.]


def run_gaussian(backend,q):
    backend._require_sequential();backend._require_work()
    count=int(backend.system.LDE.NumberOfSurfaces)
    paraxial=q.kind=='paraxial_gaussian_beam'
    start=q.surface_start if paraxial else q.start_surface
    end=q.surface_end if paraxial else q.end_surface
    end=count-1 if end is None else end
    if start>=count or end>=count:
        raise ZemaxError('INDEX_OUT_OF_RANGE','Gaussian 输出曲面编号越界。',start=start,end=end,surface_count=count)
    if q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','Gaussian 波长编号越界。',wavelength=q.wavelength)
    if not paraxial and q.field>backend.system.SystemData.Fields.NumberOfFields:
        raise ZemaxError('INDEX_OUT_OF_RANGE','Skew Gaussian 视场编号越界。',field=q.field)
    operands=PARAXIAL if paraxial else SKEW
    native_ids={key:backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,code) for key,code in operands.items()}
    axes=['X','Y'] if q.orientation=='Both' else [q.orientation]
    def flow(task):
        unit=task['context']['lens_units']
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_gaussian_merit_operands',
            actual_settings=dict(request=q.model_dump(),source='explicit native GetOperandValue arguments',
                                 configuration=task['context']['configuration']),
            native_operands=operands,length_unit=unit,divergence_unit='radians',
            position_definition='waist-to-surface distance in following optical space',
            waist_input_definition='embedded TEM00 waist' if paraxial else 'ideal beam waist before starting surface',
            coordinate_frame='meridional X/Y planes' if paraxial else 'native pupil-ray-defined moving X/Y directions',
            beam_radius_definition='native GBPS surface beam size' if paraxial else
                'native GBSS intercept size; oblique planar Y-field beam size includes 1/cos(chief angle) projection',
            resource_ownership='active optical system; no separate analysis or tool instance opened',series=[])
        models=[('m2_scaled' if paraxial and q.m2>1 else 'TEM00',q)]
        if paraxial and q.m2>1:models.insert(0,('embedded_TEM00',q.model_copy(update={'m2':1.})))
        for beam_model,query in models:
            for axis in axes:
                for surface in range(start,end+1):
                    arguments=native_arguments(query,surface,axis)
                    row=dict(index=len(task['rows']),surface=surface,axis=axis,beam_model=beam_model,native_arguments=arguments,native_values={})
                    for key,code in native_ids.items():
                        backend._cancel_boundary(task)
                        try:
                            value=float(backend.system.MFE.GetOperandValue(code,*arguments))
                        except Exception as exc:
                            raise ZemaxError('NATIVE_ERROR','Gaussian 原生操作数查询失败。',
                                operand=operands[key],surface=surface,axis=axis,arguments=arguments,
                                native_exception=str(exc),native_exception_type=type(exc).__name__) from exc
                        row['native_values'][key]=str(value)
                        if not math.isfinite(value):
                            if key=='phase_radius' and math.isinf(value):row[key]=None;row['phase_radius_state']='infinite'
                            else:raise ZemaxError('INVALID_RESULT_DATA','Gaussian 原生操作数返回非有限值。',
                                operand=operands[key],surface=surface,axis=axis,native_value=str(value),arguments=arguments)
                        else:row[key]=value
                        yield
                    for key in ['beam_radius','waist_radius','divergence_rad']:
                        if row[key]<=0:raise ZemaxError('INVALID_RESULT_DATA','Gaussian 未返回有效正值。',quantity=key,native_row=row)
                    if not paraxial:
                        row['rayleigh_range']=row['waist_radius']/math.tan(row['divergence_rad'])
                        row['rayleigh_range_source']='derived from native waist_radius/tan(divergence_rad)'
                    row['state']='succeeded';task['rows'].append(row)
        for beam_model,query in models:
            for axis in axes:
                rows=[row for row in task['rows'] if row['axis']==axis and row['beam_model']==beam_model]
                for quantity in ['beam_radius','waist_radius','phase_radius','position_from_waist','divergence_rad','rayleigh_range']:
                    values=[[row[quantity]] for row in rows]
                    task['payload']['series'].append(dict(series=len(task['payload']['series']),description=beam_model+' '+axis+' '+quantity,beam_model=beam_model,
                        labels=[beam_model+' '+axis+' '+quantity+' ('+('radians' if quantity=='divergence_rad' else unit)+')'],x_label='Surface',x_unit='index',
                        value_units=['radians' if quantity=='divergence_rad' else unit],x=[row['surface'] for row in rows],y=values,
                        invalid_count=sum(v[0] is None for v in values),data_source='native Gaussian operand rows'))
    return backend._composite(q.kind,q.model_dump(),flow)
