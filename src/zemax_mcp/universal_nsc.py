"""Confirmed pure-NSC Universal position selectors."""
import re
from contextlib import contextmanager
from .errors import ZemaxError

POSITIONS={name:(i,attr)for i,(name,attr)in enumerate([
    ('XPosition','XPosition'),('YPosition','YPosition'),('ZPosition','ZPosition'),
    ('TiltX','TiltAboutX'),('TiltY','TiltAboutY'),('TiltZ','TiltAboutZ')])}


def parameter_unit(row,number,lens_unit):
    return lens_unit if str(row.Type)=='Rectangle'and number in {1,2}else None


@contextmanager
def selected_group(source,q):
    if str(source.Mode)=='NonSequential':
        if q.nsc_surface is not None:raise ZemaxError('INVALID_ARGUMENT','纯NSC系统不接受nsc_surface。')
        yield (1,3)
        return
    if q.nsc_surface is None:raise ZemaxError('INVALID_ARGUMENT','混合NSC轴需要显式nsc_surface。')
    groups=[i for i in range(1,int(source.LDE.NumberOfSurfaces)-1)if str(source.LDE.GetSurfaceAt(i).Type)=='NonSequential']
    if q.nsc_surface not in groups:raise ZemaxError('INVALID_NSC_GROUP','Universal指定曲面不是NSC组。',requested=q.nsc_surface,available_groups=groups)
    n=source.NCE;previous=int(n.ActiveSurface);operation_error=None
    try:
        if previous!=q.nsc_surface:
            accepted=bool(n.SetActiveSurface(q.nsc_surface))
            if not accepted or int(n.ActiveSurface)!=q.nsc_surface:raise ZemaxError('NSC_GROUP_SELECTION_FAILED','Universal元数据组选择未采用。',requested=q.nsc_surface,actual=int(n.ActiveSurface))
        yield (q.nsc_surface,3+groups.index(q.nsc_surface))
    except Exception as exc:
        operation_error=exc.as_dict()if isinstance(exc,ZemaxError)else dict(message=str(exc))
        raise
    finally:
        if int(n.ActiveSurface)!=previous:
            try:
                accepted=bool(n.SetActiveSurface(previous))
                if not accepted or int(n.ActiveSurface)!=previous:raise RuntimeError('NSC metadata group restoration not adopted')
            except Exception as exc:raise ZemaxError('RESTORE_FAILED','Universal元数据原活动NSC组恢复失败。',restore_surface=previous,native_error=str(exc),operation_error=operation_error)from exc


def resolve(source,q,native=None):
    with selected_group(source,q)as(group,category):
        return resolve_selected(source,q,native,group,category)


def resolve_selected(source,q,native,group,category):
    n=source.NCE
    if q.object>int(n.NumberOfObjects):raise ZemaxError('INDEX_OUT_OF_RANGE','Universal NSC对象编号越界。',object=q.object,count=int(n.NumberOfObjects))
    row=n.GetObjectAt(q.object)
    if q.parameter=='ObjectParameter':
        if native is None:raise ZemaxError('SETTING_UNCONFIRMED','Universal NSC对象参数需要本机ObjectColumn元数据。')
        index=q.parameter_number+5;attr='Par'+str(q.parameter_number)
        cell=row.GetObjectCell(native.enum(native.api.Editors.NCE.ObjectColumn,attr))
        unit=parameter_unit(row,q.parameter_number,str(source.SystemData.Units.LensUnits))
        if cell is not None and cell.IsActive:
            dtype=str(cell.DataType)
            if dtype not in {'Integer','Double'}:raise ZemaxError('UNSUPPORTED_SETTING','Universal NSC对象参数不是数值类型。',parameter=q.parameter_number,data_type=dtype)
            if dtype=='Integer'and(not float(q.start).is_integer()or not float(q.stop).is_integer()or not((q.stop-q.start)/(q.samples-1)).is_integer()):raise ZemaxError('INVALID_ARGUMENT','Universal NSC整数参数的全部采样点必须为整数。',parameter=q.parameter_number)
    else:
        index,attr=POSITIONS[q.parameter];cell=getattr(row,attr+'Cell')
        unit='degrees'if index>=3 else str(source.SystemData.Units.LensUnits)
    if cell is None or not cell.IsActive or cell.IsReadOnly or str(cell.Solve)not in {'Fixed','Variable','None'}:raise ZemaxError('INACTIVE_SETTING','Universal NSC单元格须活动、可写且无拾取求解。',object=q.object,parameter=q.parameter,solve=str(cell.Solve)if cell is not None else None)
    return dict(category_index=category,native_parameter_index=index,native_surface=q.object,
        object_type=str(row.Type),unit=unit,unit_source='native object property definition'if unit else'physical unit not exposed by native parameter metadata',
        native_attribute=attr,parameter_header=str(cell.Header),nsc_group=group)


def verify(axis,q):
    letter=q.parameter[-1]if q.parameter.startswith('Tilt')else q.parameter[0]
    label=(r'(?:参数|Parameter)\s*'+str(q.parameter_number)+r'\s*(?=物体|对象|Object)'if q.parameter=='ObjectParameter'else letter+r'\s*(?:倾斜|Tilt)'if q.parameter.startswith('Tilt')else letter+r'\s*(?:位置|Position)')
    if not re.search(label,axis,re.I)or not re.search(r'(?:物体|对象|Object)\s*'+str(q.object)+r'\s*$',axis,re.I):
        raise ZemaxError('SETTING_REJECTED','Universal NSC对象或位置参数未采用。',native_axis=axis,object=q.object,parameter=q.parameter)
