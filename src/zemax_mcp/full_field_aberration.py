"""Full-field Standard Zernike map identity and physical coordinate metadata."""
from .errors import ZemaxError


COMPONENTS={
    'Defocus':'Standard Zernike coefficient 4',
    'PrimaryAstigmatism':'sqrt(Standard coefficient 5 squared + coefficient 6 squared)',
    'PrimaryComa':'sqrt(Standard coefficient 7 squared + coefficient 8 squared)',
}
DISPLAYS={
    'Absolute':'signed coefficient or nonnegative component magnitude at each valid field point',
    'Relative':'absolute component minus arithmetic mean over valid sampled field points',
    'Average':'arithmetic mean of absolute component over valid sampled field points; same mask retained',
}


def describe_full_field(data,request,system_settings):
    if not data.get('grids'):
        raise ZemaxError('NO_RESULT_DATA','Full Field Aberration 没有原生网格。',native_messages=data.get('native_messages',[]))
    unit='degrees' if system_settings.get('field_type')=='Angle' else system_settings.get('lens_units')
    component=COMPONENTS.get(request['aberration_type'],f"Standard Zernike coefficient {request.get('aberration_number')}")
    data.update(analysis_kind='full_field_aberration',computation_method='native_analysis',
                coefficient_definition=component,display=request['display'],display_definition=DISPLAYS[request['display']],
                field_shape=request['field_shape'])
    for grid in data['grids']:
        expected=(request['x_field_sampling'],request['y_field_sampling'])
        actual=(grid['nx'],grid['ny'])
        if actual!=expected or len(grid['values'])!=actual[1] or any(len(row)!=actual[0] for row in grid['values']):
            raise ZemaxError('INVALID_RESULT_DATA','Full Field Aberration 网格与请求尺寸不符。',expected=expected,actual=actual)
        grid['native_axes']={k:grid.get(k) for k in ['min_x','min_y','dx','dy','x_label','y_label','value_label']}
        grid.update(x_label='Field X',y_label='Field Y',value_label=component,
                    x_unit=unit,y_unit=unit,value_unit='waves',array_order='values[y][x]',
                    coefficient_definition=component,
                    coordinate_source='native MinX/MinY/Dx/Dy; signed Standard term checked against independent ray OPD fit',
                    field_width_convention='v242 XFieldWidth/YFieldWidth are half extents; native coordinates retained',
                    display=request['display'],display_definition=DISPLAYS[request['display']],field_shape=request['field_shape'])
    return data
