"""Integrated pupil transmission using formal normalized polarized ray tracing."""
import math
from .errors import ZemaxError

SELECTORS={'field','wavelength','sampling','polarization','include_chief_ray'}


def uses_batch(q):
    explicit=q.model_fields_set & SELECTORS
    if q.method=='native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING','原生Transmission专题没有请求选择器的设置回读。',settings=sorted(explicit))
    return q.method=='ray_trace' or q.method=='auto' and bool(explicit)


def pupil_nodes(intervals):
    half=intervals//2
    return [(x/half,y/half) for y in range(-half,half+1) for x in range(-half,half+1) if x*x+y*y<=half*half]


def transmission_pupil(backend,q):
    from .field_analyses import normalized_field
    from .models import BatchRays
    backend._require_sequential()
    settings=backend.get_system_settings(None)
    all_fields,all_waves=settings['fields'],settings['wavelengths']
    if q.field>len(all_fields) or q.wavelength>len(all_waves):
        raise ZemaxError('INDEX_OUT_OF_RANGE','视场或波长编号越界。')
    fields=[f for f in all_fields if not q.field or f['number']==q.field]
    waves=[w for w in all_waves if not q.wavelength or w['number']==q.wavelength]
    if not fields or not waves:raise ZemaxError('NO_RESULT_DATA','没有可用的视场或波长。')
    weight=math.fsum(w.get('weight',1.) for w in waves)
    if not math.isfinite(weight) or weight<=0:raise ZemaxError('INVALID_ARGUMENT','所选波长的权重和须为有限正数。')
    pol=q.polarization.model_dump() if q.polarization is not None else settings['polarization']
    if q.polarization is None and pol['unpolarized']:
        inputs=[dict(jx=1.,jy=0.,x_phase=0.,y_phase=0.),dict(jx=0.,jy=1.,x_phase=0.,y_phase=0.)]
    else:
        scale=max(pol['jx'],pol['jy'])
        if not math.isfinite(scale) or scale<=0:raise ZemaxError('INVALID_ARGUMENT','偏振Jones输入须为非零有限振幅。')
        jx,jy=pol['jx']/scale,pol['jy']/scale;norm=math.hypot(jx,jy)
        inputs=[dict(jx=jx/norm,jy=jy/norm,x_phase=pol['x_phase'],y_phase=pol['y_phase'])]
    pupils=pupil_nodes(q.sampling)
    image=int(backend.system.LDE.NumberOfSurfaces)-1

    def flow(task):
        payload=dict(analysis_kind=q.kind,computation_method='native_batch_polarized_pupil_trace',
            actual_settings=dict(field_numbers=[f['number'] for f in fields],wavelength_numbers=[w['number'] for w in waves],
                fields=fields,wavelengths=waves,sampling_intervals=q.sampling,sampling_nodes_per_diameter=q.sampling+1,
                pupil_sample_count=len(pupils),pupil_boundary='inclusive disk',target_surface=image,
                configuration=settings['configuration'],polarization_inputs=inputs,
                field_normalization=settings['field_normalization'],aperture_options=settings.get('aperture_options',{}),
                apodization_source='formal ILensDataEditor.GetApodization(px,py) initial power',
                input_source='system readback and formal CreateNormPol/AddRay arguments'),
            fields=[],chief_ray_surfaces=[],series=[],grids=[],ray_trace_tasks=[],structured_data_available=True,
            units=dict(transmission='dimensionless fraction',wavelength='micrometers',pupil='normalized pupil'),
            selection=dict(method='ray_trace',requested_method=q.method),
            fallback_reason='Installed native Transmission settings lack selectable input readback' if q.method=='auto' else None)
        task['payload']=payload

        def trace(rays,surface):
            geometry=yield from backend._child_job(task,backend.run_batch_ray_trace,BatchRays(rays=rays,target_surface=surface))
            payload['ray_trace_tasks'].append(geometry.get('task',{}).get('task_id'))
            traces=[]
            for p in inputs:
                result=yield from backend._child_job(task,backend.run_batch_ray_trace,BatchRays(rays=rays,target_surface=surface,polarization=p))
                payload['ray_trace_tasks'].append(result.get('task',{}).get('task_id'));traces.append(result['rows'])
            if len(geometry['rows'])!=len(rays) or any(len(rows)!=len(rays) for rows in traces):
                raise ZemaxError('INVALID_RESULT_DATA','透射追迹行数不匹配。')
            output=[]
            for i,g in enumerate(geometry['rows']):
                samples=[rows[i] for rows in traces]
                if g['state']=='missing' or any(r['state']=='missing' for r in samples):
                    raise ZemaxError('INVALID_RESULT_DATA','透射追迹结果缺少光线。',index=i)
                passed=g['state']=='succeeded' and all(r['state']=='succeeded' for r in samples)
                value=math.fsum(r['intensity'] for r in samples)/len(samples) if passed else 0.
                if not math.isfinite(value) or value<0:raise ZemaxError('INVALID_RESULT_DATA','透射追迹返回无效强度。',index=i)
                output.append(dict(transmitted_power=value,state=g['state'] if g['state']!='succeeded' else ('succeeded' if passed else 'error'),
                    error_code=g.get('error_code'),vignette_code=g.get('vignette_code'),polarization_error_codes=[r.get('error_code') for r in samples]))
            return output

        for field_index,field in enumerate(fields):
            entry=dict(field_number=field['number'],field_position=dict(x=field['x'],y=field['y']),wavelengths=[],relative_vignetted_pupil_area=abs((1-field.get('vcx',0.))*(1-field.get('vcy',0.))))
            payload['fields'].append(entry)
            hx,hy=normalized_field(all_fields,field,settings['field_normalization'])
            for wave in waves:
                values=[];incident_total=0.
                for start in range(0,len(pupils),4096):
                    backend._cancel_boundary(task)
                    rays=[dict(hx=hx,hy=hy,px=x,py=y,wavelength=wave['number']) for x,y in pupils[start:start+4096]]
                    output=yield from trace(rays,image)
                    for local,row in enumerate(output):
                        x,y=pupils[start+local]
                        incident=float(backend.system.LDE.GetApodization(x,y))
                        if not math.isfinite(incident) or incident<0:raise ZemaxError('INVALID_RESULT_DATA','原生瞳加权返回无效入射功率。',px=x,py=y,value=incident)
                        row['incident_power']=incident
                        row['transmission']=row['transmitted_power']/incident if incident>0 else None
                        incident_total+=incident
                        task['rows'].append(dict(index=len(task['rows']),field_number=field['number'],wavelength_number=wave['number'],
                            px=x,py=y,**row))
                    values.extend(output)
                if incident_total<=0:raise ZemaxError('NO_RESULT_DATA','所有采样点的入射功率均为零。')
                measured=math.fsum(r['transmitted_power'] for r in values)/incident_total
                entry['wavelengths'].append(dict(wavelength_number=wave['number'],wavelength_um=wave['wavelength_um'],transmission=measured,vignetted_transmission=measured*entry['relative_vignetted_pupil_area'],
                    launched=len(pupils),incident_power=incident_total,transmitted_power=math.fsum(r['transmitted_power'] for r in values),succeeded=sum(r['state']=='succeeded' for r in values),vignetted=sum(r['state']=='vignetted' for r in values),
                    errors=sum(r['state']=='error' for r in values)))
                if q.include_chief_ray:
                    chief=dict(field_number=field['number'],wavelength_number=wave['number'],wavelength_um=wave['wavelength_um'],rows=[])
                    payload['chief_ray_surfaces'].append(chief);previous=1.
                    for surface in range(1,image+1):
                        backend._cancel_boundary(task)
                        result=(yield from trace([dict(hx=hx,hy=hy,px=0.,py=0.,wavelength=wave['number'])],surface))[0]
                        total=result['transmitted_power']
                        chief['rows'].append(dict(surface=surface,total=total,relative=total/previous if previous else None,state=result['state']))
                        previous=total
                    chief['final_total']=previous
            entry['total_transmission']=math.fsum(item['transmission']*wave.get('weight',1.) for item,wave in zip(entry['wavelengths'],waves))/weight
            entry['total_vignetted_transmission']=entry['total_transmission']*entry['relative_vignetted_pupil_area']
            payload['series'].append(dict(series=len(payload['series']),description=f'Transmission field {field["number"]}',
                x=[w['wavelength_um'] for w in waves],y=[[v['transmission']] for v in entry['wavelengths']],
                x_label='Wavelength',x_unit='micrometers',y_unit='dimensionless fraction',labels=['Pupil transmission']))
            task['progress']=int(100*(field_index+1)/len(fields));yield
    return backend._composite(q.kind,q.model_dump(),flow)
