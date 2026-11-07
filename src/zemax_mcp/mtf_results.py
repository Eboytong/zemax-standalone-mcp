"""MTF frequency identity and physical map metadata."""
import math
import re
from .errors import ZemaxError


def curve_frequency(description, frequencies):
    numbers=[float(x) for x in re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?',description)]
    matched=[f for f in frequencies if any(abs(n-f)<=.000051 for n in numbers)]
    if len(matched)!=1:
        raise ZemaxError('INVALID_RESULT_DATA','曲线频率映射无法确认。',description=description,frequencies=frequencies)
    return matched[0]


def map_grid(grid, request, system):
    nx,ny=request['x_pixels'],request['y_pixels']
    array=grid['values']
    if len(array)!=ny or any(len(row)!=nx for row in array):
        raise ZemaxError('INVALID_RESULT_DATA','原生网格尺寸不符合Y/X排列。',nx=nx,ny=ny)
    grid['native_axes']={k:grid[k] for k in ('nx','ny','min_x','min_y','dx','dy','array_order')}
    ref=request['reference_field']
    center=next((f for f in system['fields'] if f['number']==ref),dict(x=0.,y=0.))
    dx,dy=grid['dx'],grid['dy']
    if not all(math.isfinite(v) for v in (grid['min_x'],grid['min_y'],dx,dy)) or dx<=0 or dy<=0:
        raise ZemaxError('INVALID_RESULT_DATA','原生网格坐标无效。')
    grid.update(nx=nx,ny=ny,min_x=grid['min_x'],
        min_y=grid['min_y'],dx=dx,dy=dy,
        x_unit='degrees' if system['field_type']=='Angle' else system['lens_units'],
        y_unit='degrees' if system['field_type']=='Angle' else system['lens_units'],
        value_unit='dimensionless',frequency=request['frequency'],frequency_unit=system['mtf_units'],
        data_type=request['data_type'],reference_field=ref,array_order='values[y][x]',coordinate_definition='native physical field sample coordinates')

    if request['kind']=='geometric_mtf_map':grid['diffraction_limit_correction']='applied by native map; validated against corrected single-field geometric MTF'
