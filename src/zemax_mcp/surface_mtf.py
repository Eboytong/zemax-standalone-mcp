"""Frequency-grid semantics for the installed FFT/Huygens surface MTF outlets."""
import math
from .errors import ZemaxError


def describe_surface_mtf(data,request,frequency_unit):
    if not data.get('grids'):
        raise ZemaxError('NO_RESULT_DATA','曲面MTF没有原生频率网格。',native_messages=data.get('native_messages',[]))
    data.update(analysis_kind=request['kind'],frequency_unit=frequency_unit,mtf_type=request['mtf_type'])
    for g in data['grids']:
        if g['nx']<2 or g['ny']<2 or g['dx']<=0 or g['dy']<=0 or any(not math.isfinite(g[k])for k in ['dx','dy','min_x','min_y']):
            raise ZemaxError('INVALID_RESULT_DATA','曲面MTF频率网格尺寸或步长无效。')
        if len(g['values'])!=g['ny'] or any(len(row)!=g['nx']for row in g['values']):
            raise ZemaxError('INVALID_RESULT_DATA','曲面MTF数组与原生尺寸不一致。')
        g['native_axes']={k:g[k]for k in ['min_x','min_y','dx','dy']}
        g['native_axis_labels']={k:g.get(k) for k in ['x_label','y_label']}
        g['native_value_label']=g['value_label']
        if request['kind']=='huygens_surface_mtf':
            cx,cy=g['nx']//2,g['ny']//2
            g.update(min_x=-cx*g['dx'],min_y=-cy*g['dy'],
                     origin_source='v242 shifted Huygens OTF center; native minima incorrectly place DC outside the grid')
        else:
            cx=round(-g['min_x']/g['dx']);cy=round(-g['min_y']/g['dy'])
            if not (0<=cx<g['nx'] and 0<=cy<g['ny']):
                raise ZemaxError('INVALID_RESULT_DATA','FFT曲面MTF零频点不在原生网格内。',native_axes=g['native_axes'])
        g.update(x_label='Spatial frequency X',y_label='Spatial frequency Y',
                 axis_labels_source='surface MTF frequency-grid definition; native labels retained separately',
                 x_unit=frequency_unit,y_unit=frequency_unit,value_unit='dimensionless',
                 value_quantity=request['mtf_type'],array_order='values[y][x]',
                 zero_frequency_index=dict(x=cx,y=cy),
                 frequency_sampling='native Dx/Dy retained; Huygens origin calibrated at shifted DC')
    if request['kind']=='fft_surface_mtf':
        data['display_controls']=dict(rotation=request['rotation'],scale_factor=request['scale_factor'],scope='native plot view; frequency data remain in native system axes')
    return data
