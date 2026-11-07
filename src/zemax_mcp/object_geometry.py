"""Paged native faceted object geometry with borrowed cursor/frame restoration."""
import math
from .errors import ZemaxError
from .data import unwrap

MAX_VERTICES=100000


def vector(data,name,index,face):
    result=getattr(data,name)(index,0.,0.,0.)
    if not result or len(result)!=4 or not result[0]:raise ZemaxError('OBJECT_GEOMETRY_READ_FAILED','原生顶点或法线读取失败。',method=name,face=face,vertex=index)
    value=[float(v)for v in result[1:]]
    if not all(math.isfinite(v)for v in value):raise ZemaxError('INVALID_RESULT_DATA','原生顶点或法线包含非有限数值。',method=name,face=face,vertex=index)
    return value


def read_page(row,q,global_rotation=None):
    data=unwrap(row.GetFacetedObjectData())
    if data is None:raise ZemaxError('OBJECT_GEOMETRY_UNAVAILABLE','原生对象未提供IFaceData。',object=q.object,required_setting='type_settings.ObjectIsADetector=true',condition_source='native GetFacetedObjectData contract; caller explicitly enables detector mode')
    total=int(data.NumberOfFaces)
    if total<0:raise ZemaxError('INVALID_RESULT_DATA','原生面数量为负数。',total=total)
    if q.start>total:raise ZemaxError('INDEX_OUT_OF_RANGE','对象面分页起点越界。',start=q.start,total=total)
    result=dict(object=q.object,object_type=str(row.Type),start=q.start,total=total,rows=[],frame=q.frame,source='INCERow.GetFacetedObjectData/IFaceData',
        representation='native faceted object; tessellation depends on object and native settings',face_index='zero based native CurrentFace',cursor_restored=True)
    end=min(total,q.start+q.count);result['next_start']=end if end<total else None
    if total==0:return result
    previous_face=int(data.CurrentFace);previous_global=bool(data.ConvertToGlobal);operation_error=None;vertices_read=0
    try:
        data.ConvertToGlobal=q.frame=='global'
        if bool(data.ConvertToGlobal)!=(q.frame=='global'):raise ZemaxError('SETTING_REJECTED','原生对象面坐标系未采用。',frame=q.frame)
        for face in range(q.start,end):
            data.CurrentFace=face
            if int(data.CurrentFace)!=face:raise ZemaxError('SETTING_REJECTED','原生面游标未采用。',face=face,actual=int(data.CurrentFace))
            count=int(data.NumberOfVertices)
            if not 3<=count<=10000 or vertices_read+count>MAX_VERTICES:raise ZemaxError('RESULT_TOO_LARGE','单面或本页面顶点数量超出界限。',face=face,vertices=count,page_vertices=vertices_read,limit=MAX_VERTICES)
            points=[vector(data,'GetVertex',i,face)for i in range(count)]
            normals=[vector(data,'GetVertexNormal',i,face)for i in range(count)]
            native_normals=normals
            if q.frame=='global':
                if global_rotation is None:raise ZemaxError('OBJECT_TRANSFORM_UNAVAILABLE','全局法线需要对象旋转矩阵。')
                data.ConvertToGlobal=False
                if data.ConvertToGlobal:raise ZemaxError('SETTING_REJECTED','局部法线坐标系未采用。')
                local_normals=[vector(data,'GetVertexNormal',i,face)for i in range(count)]
                data.ConvertToGlobal=True
                if not data.ConvertToGlobal:raise ZemaxError('SETTING_REJECTED','全局坐标系恢复未采用。')
                normals=[[sum(global_rotation[i][j]*n[j]for j in range(3))for i in range(3)]for n in local_normals]
            vertices_read+=count
            item=dict(face=face,vertices=points,vertex_normals=normals,vertex_count=count,vertex_mean=[sum(p[i]for p in points)/count for i in range(3)])
            if q.frame=='global':item.update(native_vertex_normals=native_normals,normal_source='object rotation applied to native local normal; translation excluded')
            if count==3:
                u=[b-a for a,b in zip(points[0],points[1])];v=[b-a for a,b in zip(points[0],points[2])]
                cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                area=math.hypot(*cross)/2
                if not math.isfinite(area)or area<=0:raise ZemaxError('INVALID_RESULT_DATA','原生三角面退化。',face=face)
                item['triangle_area']=area
            if q.include_radiometry:
                item['radiometry']={name:(value if math.isfinite(value)else None)for name in ['Flux','Irradiance','AbsorbedFlux','AbsorbedIrradiance']for value in [float(getattr(data,name))]}
            result['rows'].append(item)
        result['vertices_read']=vertices_read
    except Exception as exc:
        operation_error=exc
        raise
    finally:
        try:
            data.ConvertToGlobal=previous_global;data.CurrentFace=previous_face
            if bool(data.ConvertToGlobal)!=previous_global or int(data.CurrentFace)!=previous_face:raise RuntimeError('native cursor/frame readback mismatch')
        except Exception as restore_error:
            original=operation_error.as_dict()if isinstance(operation_error,ZemaxError)else dict(type=type(operation_error).__name__,message=str(operation_error))if operation_error else None
            raise ZemaxError('OBJECT_GEOMETRY_RESTORE_FAILED','原生面游标或坐标系恢复失败。',restore_error=dict(type=type(restore_error).__name__,message=str(restore_error)),operation_error=original,previous_face=previous_face,previous_global=previous_global)from restore_error
    return result


def get_object_geometry(backend,q):
    row=backend._object(q.object)
    rotation=backend._nsc_transform(q.object)['rotation']if q.frame=='global'else None
    try:result=read_page(row,q,rotation)
    except ZemaxError as exc:
        if exc.code=='OBJECT_GEOMETRY_RESTORE_FAILED':backend.requires_reconnect=True
        raise
    units=backend.system.SystemData.Units
    result.update(geometry_unit=str(units.LensUnits),area_unit=str(units.LensUnits)+'^2',context=backend.context())
    if q.include_radiometry:
        result['radiometry_units']=dict(source_units=str(units.SourceUnits),source_prefix=str(units.SourceUnitPrefix),analysis_units=str(units.AnalysisUnits),analysis_prefix=str(units.AnalysisUnitPrefix),definition='raw native IFaceData flux/irradiance/absorbed quantities; detector-specific interpretation applies')
    return result
