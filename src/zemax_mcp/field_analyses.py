"""Geometric field diagnostics using the owned native batch ray tracer."""
import math

from .errors import ZemaxError
from .models import BatchRays


def pupil_grid(density):
    return [(x/density,y/density) for y in range(-density,density+1)
            for x in range(-density,density+1) if x*x+y*y <= density*density]


def normalized_field(fields, field, normalization):
    if normalization == 'Radial':
        scale=max((math.hypot(f['x'],f['y']) for f in fields),default=0)
        return (field['x']/scale,field['y']/scale) if scale else (0.,0.)
    sx=max((abs(f['x']) for f in fields),default=0)
    sy=max((abs(f['y']) for f in fields),default=0)
    return (field['x']/sx if sx else 0.,field['y']/sy if sy else 0.)


def footprint_visible(target, full, surface, delete_vignetted):
    if target.get('error_code') != 0 or not target.get('position'):
        return False
    clipped=target.get('vignette_code')
    if clipped and clipped < surface:
        return False
    return not delete_vignetted or (full.get('error_code') == 0 and full.get('vignette_code') == 0)


def sampled_analysis(backend, q):
    backend._require_sequential()
    settings=backend.get_system_settings(None)
    fields=settings['fields'];waves=settings['wavelengths']
    if q.kind == 'footprint':
        backend._row(q.surface)
        if q.field > len(fields) or q.wavelength > len(waves):
            raise ZemaxError('INDEX_OUT_OF_RANGE','视场或波长编号越界。')
    elif settings['field_type'] != 'Angle':
        raise ZemaxError('UNSUPPORTED_SETTING','渐晕扫描需要角度视场。')
    # These AnalysisIDM entries have no typed settings in the local 24.2 DLL.
    # Refuse an unverified CFG setting rather than silently use GUI defaults.
    reason=dict(code='UNSUPPORTED_SETTING',message='本机此专题没有可回读的专用设置接口；使用原生批量追迹。')
    if q.method == 'native':
        raise ZemaxError('UNSUPPORTED_SETTING','本机此专题的设置采用尚无可靠回读路径。',analysis=q.kind)
    def flow(task):
        saved=[]
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_batch_ray_trace',
            fallback_reason=reason if q.method=='auto' else None,series=[],scatter=[],
            sampling=dict(pattern='square grid clipped to unit disk',ray_density=q.ray_density),
            units=dict(position=settings['lens_units'],pupil='normalized',throughput='fraction'))
        payload=task['payload'];grid=pupil_grid(q.ray_density)
        task['summary']={'launched':0,'passed':0,'errors':0,'vignetted':0,'missing':0}
        try:
            if q.kind=='vignetting' and q.remove_vignetting_factors:
                for i in range(1,len(fields)+1):
                    f=backend.system.SystemData.Fields.GetField(i)
                    for key in ('VDX','VDY','VCX','VCY','VAN'):
                        value=float(getattr(f,key));saved.append((f,key,value))
                        setattr(f,key,0.)
                        if float(getattr(f,key)) != 0.:raise ZemaxError('SETTING_REJECTED','清除渐晕因子未采用。',setting=key)
            payload["effective_system_settings"]=backend.get_system_settings(None)
            jobs=[]
            if q.kind=='vignetting':
                primary=next(w['number'] for w in waves if w['primary'])
                maximum=max(math.hypot(f['x'],f['y']) for f in fields)
                for i in range(q.field_density):
                    value=maximum*i/(q.field_density-1)
                    hx,hy=normalized_field(fields,dict(x=0.,y=value),settings['field_normalization'])
                    nearest=min(fields,key=lambda f:f['x']**2+(f['y']-value)**2)
                    area=1. if q.remove_vignetting_factors else abs((1-nearest['vcx'])*(1-nearest['vcy']))
                    jobs.append((dict(field_coordinate=value,wavelength=primary,pupil_area_factor=area),hx,hy,primary))
            else:
                for f in fields:
                    if q.field and f['number']!=q.field:continue
                    hx,hy=normalized_field(fields,f,settings['field_normalization'])
                    for w in waves:
                        if not q.wavelength or w['number']==q.wavelength:
                            jobs.append((dict(field=f['number'],wavelength=w['number']),hx,hy,w['number']))
            image=backend.system.LDE.NumberOfSurfaces-1
            curve=[]
            for job_number,(metadata,hx,hy,wave) in enumerate(jobs):
                rows=[];points=[];passed=0
                for start in range(0,len(grid),10000):
                    backend._cancel_boundary(task)
                    samples=grid[start:start+10000]
                    req=BatchRays(rays=[dict(hx=hx,hy=hy,px=x,py=y,wavelength=wave) for x,y in samples],target_surface=image)
                    full=yield from backend._child_job(task,backend.run_batch_ray_trace,req)
                    full_rows=full['rows']
                    targets=full_rows
                    if q.kind=='footprint' and q.surface!=image:
                        at=yield from backend._child_job(task,backend.run_batch_ray_trace,req.model_copy(update={'target_surface':q.surface}))
                        targets=at['rows']
                    for n,(r,t) in enumerate(zip(full_rows,targets)):
                        okay=r['state']=='succeeded';passed+=int(okay)
                        summary=task['summary'];summary['launched']+=1
                        summary['passed' if okay else 'errors' if r['state']=='error' else 'missing' if r['state']=='missing' else 'vignetted']+=1
                        row=dict(t,index=len(task['rows'])+len(rows),sample_index=start+n,**metadata,
                                 image_error_code=r.get('error_code'),image_vignette_code=r.get('vignette_code'))
                        if q.kind=='footprint':
                            visible=footprint_visible(t,r,q.surface,q.delete_vignetted)
                            row['visible']=visible
                            if visible:points.append(dict(x=t['position'][0],y=t['position'][1],value=wave))
                        rows.append(row)
                task['rows'].extend(rows)
                if q.kind=='vignetting':curve.append([metadata['field_coordinate'],passed/len(grid)*metadata['pupil_area_factor']])
                else:payload['scatter'].append(dict(description='Footprint',x_label='local X',y_label='local Y',
                    x_unit=settings['lens_units'],y_unit=settings['lens_units'],surface=q.surface,points=points,launched=len(grid),visible=len(points),throughput=len(points)/len(grid),**metadata))
                task['progress']=int(100*(job_number+1)/len(jobs));yield
            if curve:payload['series']=[dict(series=0,description='Geometric pupil throughput',x_label='Y field',x_unit='degrees',
                labels=['throughput'],value_units=['fraction'],x=[r[0] for r in curve],y=[[r[1]] for r in curve])]
        finally:
            failures=[]
            for f,key,value in reversed(saved):
                try:
                    setattr(f,key,value)
                    if float(getattr(f,key))!=value:raise ValueError('readback mismatch')
                except Exception as exc:failures.append(dict(setting=key,error=str(exc)))
            task['restoration']=dict(required=bool(saved),restored=not failures,errors=failures)
            if failures:
                backend.requires_reconnect=True
                raise ZemaxError('RESTORE_FAILED','渐晕因子恢复失败。',errors=failures)
    return backend._composite(q.kind,q.model_dump(),flow)
