"""Read the detector's own facet data without a visualization mesh."""
import math
from .errors import ZemaxError


def read_facet_geometry(row, frame):
    data=row.GetFacetedObjectData()
    if data is None:raise ZemaxError('DETECTOR_GEOMETRY_UNAVAILABLE','原生对象未返回面数据。')
    previous_face=int(data.CurrentFace);previous_global=bool(data.ConvertToGlobal)
    faces=[]
    try:
        data.ConvertToGlobal=frame=='global'
        if bool(data.ConvertToGlobal)!=(frame=='global'):raise ZemaxError('SETTING_REJECTED','面坐标系未被采用。')
        count=int(data.NumberOfFaces)
        if not 0<count<=1000000:raise ZemaxError('INVALID_DETECTOR_DATA','无有效原生面或超过1000000面。',faces=count)
        for index in range(count):
            data.CurrentFace=index
            if int(data.CurrentFace)!=index:raise ZemaxError('DETECTOR_GEOMETRY_READ_FAILED','原生面游标未采用请求。',face=index)
            size=int(data.NumberOfVertices)
            if size!=3:raise ZemaxError('UNSUPPORTED_DETECTOR_GEOMETRY','Surface几何需要三角面。',face=index,vertices=size)
            vertices=[];normals=[]
            for vertex in range(size):
                for method,destination in ((data.GetVertex,vertices),(data.GetVertexNormal,normals)):
                    result=method(vertex,0.,0.,0.)
                    if not result or not result[0]or len(result)!=4:raise ZemaxError('DETECTOR_GEOMETRY_READ_FAILED','原生顶点/法线读取失败。',face=index,vertex=vertex)
                    value=[float(v)for v in result[1:]]
                    if not all(math.isfinite(v)for v in value):raise ZemaxError('INVALID_DETECTOR_DATA','原生几何包含非有限值。',face=index,vertex=vertex)
                    destination.append(value)
            u=[b-a for a,b in zip(vertices[0],vertices[1])];v=[b-a for a,b in zip(vertices[0],vertices[2])]
            cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            area=math.sqrt(sum(x*x for x in cross))/2
            if not math.isfinite(area)or area<=0:raise ZemaxError('INVALID_DETECTOR_DATA','退化三角面。',face=index)
            flux=float(data.Flux);irradiance=float(data.Irradiance)
            faces.append(dict(face=index,vertices=vertices,vertex_normals=normals,area=area,
                centroid=[sum(x[i]for x in vertices)/3 for i in range(3)],
                facet_flux=flux if math.isfinite(flux)else None,facet_irradiance=irradiance if math.isfinite(irradiance)else None))
    finally:
        try:
            data.CurrentFace=previous_face;data.ConvertToGlobal=previous_global
            if int(data.CurrentFace)!=previous_face or bool(data.ConvertToGlobal)!=previous_global:raise RuntimeError('cursor/frame not restored')
        except Exception as exc:raise ZemaxError('DETECTOR_GEOMETRY_RESTORE_FAILED','面数据游标或坐标系未恢复。',reason=str(exc))from exc
    return faces
