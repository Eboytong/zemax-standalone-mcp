"""Native conic and numbered sequential surface axes."""
from .errors import ZemaxError


def parameter_unit(row,number,lens_unit):
    if str(row.Type)=='CoordinateBreak':
        if number in {1,2}:return lens_unit
        if number in {3,4,5}:return 'degrees'
        if number==6:return 'dimensionless'
    return None


def resolve(source,q,native):
    row=source.LDE.GetSurfaceAt(q.surface)
    if q.parameter=='Conic':
        cell=row.ConicCell;index=4;unit='dimensionless'
    elif q.parameter=='TCE':
        cell=row.TCECell;index=5;unit='ppm/Celsius'
    else:
        if native is None:raise ZemaxError('SETTING_UNCONFIRMED','Universal曲面参数需要本机SurfaceColumn元数据。')
        cell=row.GetSurfaceCell(native.enum(native.api.Editors.LDE.SurfaceColumn,'Par'+str(q.parameter_number)))
        index=q.parameter_number+6;unit=parameter_unit(row,q.parameter_number,str(source.SystemData.Units.LensUnits))
    if cell is None or not cell.IsActive or cell.IsReadOnly or str(cell.Solve)not in {'Fixed','Variable'}:raise ZemaxError('INACTIVE_SETTING','Universal曲面扫描单元格须活动、可写且无拾取求解。',surface=q.surface,parameter=q.parameter,parameter_number=q.parameter_number)
    dtype=str(cell.DataType)
    if dtype not in {'Integer','Double'}:raise ZemaxError('UNSUPPORTED_SETTING','Universal曲面参数不是数值类型。',data_type=dtype)
    if dtype=='Integer'and(not float(q.start).is_integer()or not float(q.stop).is_integer()or not((q.stop-q.start)/(q.samples-1)).is_integer()):raise ZemaxError('INVALID_ARGUMENT','Universal曲面整数参数的全部采样点必须为整数。',parameter=q.parameter_number)
    return dict(category_index=0,native_parameter_index=index,native_surface=q.surface,unit=unit,
        unit_source='native surface property definition'if unit else'physical unit not exposed by native parameter metadata',
        surface_type=str(row.Type),parameter_header=str(cell.Header),parameter_data_type=dtype)
