"""Native RMS settings and five-plane spot statistics."""
from .analyses import native_setting
from .detectors import check_setting_readback
from .errors import ZemaxError
from .models import Spot


def rms_settings(native,s,q):
    def put(name,value):
        native_setting(native,s,name,value)
        prop=s.GetType().GetProperty(name)
        if prop.PropertyType.IsEnum:
            if not getattr(s,name).Equals(native.enum(prop.PropertyType,value)):
                raise ZemaxError('SETTING_REJECTED','RMS枚举未采用。',setting=name)
        else:check_setting_readback(s,name,value)
    for name,value in [('Data','StrehlRation' if q.data_type=='StrehlRatio' else q.data_type),('Method',q.method),('ReferTo',q.reference),('UseDashes',False),('PlotScale',0.),('ShowDiffractionLimit',q.show_diffraction_limit)]:put(name,value)
    put('RayDensity','RayDens_'+str(q.rings or 3) if q.method=='GaussQuad' else 'RayDens_'+(q.sampling or 'S_64x64').removeprefix('S_'))
    if q.kind=='rms_vs_field':
        for name,value in [('Orientation',q.orientation),('FieldDensity','FieldDens_'+str(q.field_density)),('RemoveVignettingFactors',q.remove_vignetting_factors)]:put(name,value)
    else:
        for name,value in [('FocusDensity','FocusDens_'+str(q.focus_density)),('MinimumFocus',q.minimum_focus),('MaximumFocus',q.maximum_focus)]:put(name,value)


def rms_map_settings(native,s,q):
    desired={}
    def put(name,value):
        native_setting(native,s,name,value)
        desired[name]=value
        check(name,value)
    def check(name,value):
        prop=s.GetType().GetProperty(name)
        actual=getattr(s,name)
        expected=native.enum(prop.PropertyType,value) if prop.PropertyType.IsEnum else value
        if prop.PropertyType.IsEnum:
            matches=actual.Equals(expected)
        elif isinstance(value,bool):
            matches=bool(actual)==value
        elif isinstance(value,int):
            matches=int(actual)==value
        else:
            matches=abs(float(actual)-float(value))<=max(1e-12,abs(float(value))*1e-12)
        if not matches:
            raise ZemaxError('SETTING_REJECTED','RMS Field Map setting did not match on readback.',setting=name,requested=value,actual=str(actual))
    put('Data','StrehlRation' if q.data_type=='StrehlRatio' else q.data_type)
    put('MethodType',q.method)
    put('RayDensity','RayDens_'+str(q.rings or 3) if q.method=='GaussQuad' else 'RayDens_'+(q.sampling or 'S_64x64').removeprefix('S_'))
    put('ReferTo',q.reference)
    put('ShowAs',q.show_as)
    put('UsePolarization',q.use_polarization)
    put('RemoveVignettingFactors',q.remove_vignetting_factors)
    put('X_FieldSampling',q.x_field_sampling)
    put('Y_FieldSampling',q.y_field_sampling)
    put('X_FieldSize',q.x_field_size)
    put('Y_FieldSize',q.y_field_size)
    put('PlotScale',0.)
    for name,value in desired.items():check(name,value)


def map_rms_grid(grid,request,system,lens_units):
    from .errors import ZemaxError
    if grid['nx']!=request['x_field_sampling'] or grid['ny']!=request['y_field_sampling']:
        raise ZemaxError('INVALID_RESULT_DATA','RMS Field Map grid size differs from requested sampling.',expected_x=request['x_field_sampling'],expected_y=request['y_field_sampling'],actual_x=grid['nx'],actual_y=grid['ny'])
    metric=request['data_type']
    unit='waves' if metric=='Wavefront' else 'dimensionless' if metric=='StrehlRatio' else 'micrometers'
    if metric in {'SpotRadius','Spot_X','Spot_Y'}:
        scale={'Millimeters':1000.,'Centimeters':10000.,'Meters':1e6,'Inches':25400.}[lens_units]
        grid['values']=[[None if value is None else value*scale for value in row]for row in grid['values']]
        grid.update(native_value_unit=lens_units,native_to_value_scale=scale)
    field_unit='degrees' if system['field_type']=='Angle' else lens_units
    fields=system.get('fields',[])
    center=next((f for f in fields if f['number']==request['field']),None)
    if center is None:
        raise ZemaxError('INVALID_RESULT_DATA','RMS Field Map reference field metadata is missing.',field=request['field'])
    grid['native_axes']={k:grid[k] for k in ('min_x','min_y','dx','dy')}
    grid['min_x']+=center['x']
    grid['min_y']+=center['y']
    grid.update(analysis_kind='rms_field_map',x_unit=field_unit,y_unit=field_unit,value_unit=unit,data_type=metric,
        x_field_size=request['x_field_size'],y_field_size=request['y_field_size'],
        field=request['field'],wavelength_selection=request['wavelength'],
        array_order='values[y][x]',field_center=dict(x=center['x'],y=center['y']),
        coordinate_definition='native field offsets plus selected physical reference field')
    return grid


def through_focus_spot(backend,q):
    backend._require_sequential(focused=True)
    if q.field>backend.system.SystemData.Fields.NumberOfFields or q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','视场或波长越界。')
    def flow(task):
        original=yield from backend._child_job(task,backend._run_general_analysis,q)
        task['payload']=dict(analysis_kind=q.kind,native_analysis_task=original['task']['task_id'],
            native_artifacts=original.get('artifacts',[]),native_text_exported=original.get('native_text_exported',True),native_export_error=original.get('native_export_error'),computation_method='native ThroughFocusSpot plus five standard-spot evaluations',
            radius_unit='micrometers',reference_coordinate_unit=task['context']['lens_units'])
        source,work=backend.source_path,backend.work_path
        snapshot=backend._checkpoint('through_focus_spot_baseline')
        task['baseline']=dict(path=snapshot,context=backend.context())
        factor={'Millimeters':.001,'Centimeters':.0001,'Inches':.001/25.4,'Meters':.000001}[task['context']['lens_units']]
        try:
            for multiplier in (-2,-1,0,1,2):
                backend._cancel_boundary(task)
                backend._restore_model(task,snapshot,source,work)
                offset=q.delta_focus_um*multiplier
                row=backend._row(backend.system.LDE.NumberOfSurfaces-2)
                cell=row.ThicknessCell
                initial=float(cell.DoubleValue)
                cell.MakeSolveFixed()
                if str(cell.Solve)!='Fixed':raise ZemaxError('SETTING_REJECTED','临时厚度求解未采用Fixed。')
                cell.DoubleValue=initial+offset*factor
                if abs(float(cell.DoubleValue)-(initial+offset*factor))>1e-10:raise ZemaxError('SETTING_REJECTED','焦移未采用。')
                req=Spot(reference=q.reference,field=q.field,wavelength=q.wavelength,pattern=q.pattern,ray_density=q.ray_density,use_polarization=q.use_polarization)
                result=yield from backend._child_job(task,backend.run_spot_analysis,req)
                for metric in result['metrics']:
                    task['rows'].append(dict(index=len(task['rows']),delta_focus_um=offset,delta_focus=offset*factor,
                        child_task_id=result['task']['task_id'],**metric))
                task['progress']=int(100*(multiplier+3)/5);yield
            series=[]
            for field in sorted({r['field_number'] for r in task['rows']}):
                rows=[r for r in task['rows'] if r['field_number']==field]
                series.append(dict(series=len(series),description='Field '+str(field),x_label='Defocus',x_unit='micrometers',
                    labels=['RMS radius','GEO radius'],value_units=['micrometers']*2,x=[r['delta_focus_um'] for r in rows],y=[[r['rms_radius'],r['geo_radius']] for r in rows]))
            task['payload']['series']=series
        finally:backend._restore_model(task,snapshot,source,work)
    return backend._composite(q.kind,q.model_dump(),flow)
