"""Identify native Moore-Elliott grids from their descriptions."""
from .errors import ZemaxError


def describe_contrast_loss(data,request,mtf_units):
    grids=data.get('grids',[])
    if not grids:
        raise ZemaxError('NO_RESULT_DATA','Contrast Loss returned no native grids.')
    identities=set()
    for grid in grids:
        description=grid.get('description','').casefold()
        direction=('Tangential' if 'tangential' in description or '子午' in description else
                   'Sagittal' if 'sagittal' in description or '弧矢' in description else None)
        quantity=('phase' if 'phase' in description or '相位' in description else
                  'contrast_loss' if 'contrast loss' in description or '对比度损失' in description else None)
        if direction is None or quantity is None or (direction,quantity) in identities:
            raise ZemaxError('INVALID_RESULT_DATA','Contrast Loss grid identity is missing or duplicated.',
                             native_descriptions=[g.get('description') for g in grids])
        identities.add((direction,quantity))
        nx,ny=grid['nx'],grid['ny']
        if len(grid['values'])!=ny or any(len(row)!=nx for row in grid['values']):
            raise ZemaxError('INVALID_RESULT_DATA','Contrast Loss grid dimensions do not match values.',nx=nx,ny=ny)
        grid['native_axes']={key:grid.get(key) for key in ('x_label','y_label','value_label','min_x','min_y','dx','dy')}
        grid.update(direction=direction,value_quantity=quantity,array_order='values[y][x]',
                    x_label='Pupil X',y_label='Pupil Y',x_unit='normalized pupil',y_unit='normalized pupil',
                    value_label=direction+' '+quantity.replace('_',' '),
                    value_unit='degrees' if quantity=='phase' else 'dimensionless',
                    invalid_definition='native nonfinite value; paired rays can fall outside pupil')
    if identities!={(d,q) for d in ['Tangential','Sagittal'] for q in ['phase','contrast_loss']}:
        raise ZemaxError('INVALID_RESULT_DATA','Contrast Loss requires phase and loss grids for both directions.',
                         actual_identities=sorted(identities))
    data.update(analysis_kind='contrast_loss',frequency_unit=mtf_units,
                result_definition='native Moore-Elliott phase and contrast loss; grids identified by native description',
                frequency_requested=request['frequency'],automatic_frequency_definition='zero selects 5 percent of native cutoff',
                display_normalize=request['normalize'],display_show_opd=request['show_opd'],
                normalization='Normalize controls native circle display scale; raw loss grids retained')
    return data
