"""Settings for the installed surface slope and phase slope analyses."""

SLOPE_ANALYSES = {
    'surface_slope': 'SurfaceSlope',
    'surface_slope_cross': 'SurfaceSlopeCross',
    'surface_phase_slope': 'SurfacePhaseSlope',
    'surface_phase_slope_cross': 'SurfacePhaseSlopeCross',
}


def configure_surface_slope(q, put):
    put('Sampling', q.sampling)
    put('Data', q.data_type)
    if q.kind.endswith('_cross'):
        put('Angle', q.angle)
    else:
        put('ShowAs', q.show_as)
        if q.contour_format is not None:
            put('ContourFormat', q.contour_format)
    if q.kind.startswith('surface_phase_'):
        for name, value in [('RemovePiston', q.remove_piston), ('RemoveTiltX', q.remove_tilt_x),
                            ('RemoveTiltY', q.remove_tilt_y), ('RemovePower', q.remove_power)]:
            put(name, value)
    else:
        put('RemoveOption', q.remove_option)
        if q.remove_option == 'BestFitSphere':
            criterion = q.best_fit_sphere or 'MinimumVolume'
            put('BestFitSphereOption', criterion)
            if criterion == 'MinimumVolume':
                put('ReverseDirection', q.reverse_direction or False)
        put('ConsiderOffAxisAperture', q.consider_off_axis_aperture)


def describe_surface_slope(data, request, lens_unit):
    geometric = request['kind'] in {'surface_slope', 'surface_slope_cross'}
    value_unit = 'dimensionless sag derivative' if geometric else 'cycles per lens unit'
    data.update(analysis_kind=request['kind'], surface=request['surface'],
                data_type=request['data_type'],
                value_unit_source='analytic sag-derivative reference on native sphere/conic' if geometric
                else 'Binary2 analytic phase derivative divided by 2*pi; native v242 numerical reference')
    for grid in data.get('grids', []):
        grid.update(x_unit=lens_unit, y_unit=lens_unit, reference='off-axis aperture local X/Y'if request.get('consider_off_axis_aperture')else'surface local X/Y',
                    value_unit=value_unit, array_order='values[y][x]')
    for series in data.get('series', []):
        derivative = 'sag derivative' if geometric else 'phase derivative / (2*pi)'
        series.update(coordinate_unit=lens_unit, x_unit=lens_unit,
                      value_units=[lens_unit, value_unit],
                      axis_definition=f'XData=surface X; YData columns=[surface Y, selected {derivative}]',
                      value_unit_source=data['value_unit_source'])
