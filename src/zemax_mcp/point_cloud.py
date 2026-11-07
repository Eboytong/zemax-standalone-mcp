"""Native LDE point-cloud export; method arguments have no native setting getters."""
from pathlib import Path
from .schema import Request, Index
from .errors import ZemaxError
from .files import output_path
from .speos import OwnedCopyTool
from typing import Annotated, Literal
from pydantic import Field, model_validator


class PointCloudExport(Request):
    surface: Index
    path: str
    overwrite: bool = False
    x_sampling: Annotated[int, Field(strict=True, ge=2, le=4096)] = 21
    y_sampling: Annotated[int, Field(strict=True, ge=2, le=4096)] = 21
    include_surface_normals: bool = True
    format: Literal['ASCII', 'Binary', 'CompressedBinary'] = 'ASCII'

    @model_validator(mode='after')
    def budget(self):
        if self.x_sampling*self.y_sampling > 1048576:
            raise ValueError('点云单次采样预算为1048576个网格点。')
        return self


def read_header(path):
    header={}
    with Path(path).open('rb') as stream:
        for _ in range(64):
            line=stream.readline(8193)
            if len(line)>8192 or not line:
                raise ZemaxError('INVALID_POINT_CLOUD','PCD头未完整读取。',path=str(path))
            try: text=line.decode('ascii').strip()
            except UnicodeDecodeError as exc:
                raise ZemaxError('INVALID_POINT_CLOUD','PCD头不是ASCII文本。',path=str(path)) from exc
            if not text or text.startswith('#'): continue
            key,*value=text.split()
            if key in header: raise ZemaxError('INVALID_POINT_CLOUD','PCD头字段重复。',field=key)
            header[key]=value
            if key=='DATA': break
        else: raise ZemaxError('INVALID_POINT_CLOUD','PCD头超过64行。')
    try:
        fields=header['FIELDS']
        width,height,points=(int(header[k][0]) for k in ['WIDTH','HEIGHT','POINTS'])
        data=header['DATA'][0]
        if not {'x','y','z'}.issubset(fields) or min(width,height,points)<0 or width*height!=points:
            raise ValueError('coordinates or dimensions')
        if data not in ['ascii','binary','binary_compressed']:raise ValueError('DATA')
    except (KeyError,ValueError,IndexError) as exc:
        raise ZemaxError('INVALID_POINT_CLOUD','PCD头缺少有效坐标、尺寸或数据格式。',header=header) from exc
    return dict(fields=fields,width=width,height=height,points=points,data=data,native_header=header)


def export(backend,q):
    backend._require_sequential()
    backend._require_work()
    system=backend.system
    if q.surface>=system.LDE.NumberOfSurfaces:
        raise ZemaxError('INDEX_OUT_OF_RANGE','点云曲面编号越界。',surface=q.surface)
    path=output_path(q.path,{'.pcd'},q.overwrite)
    fmt=backend.native.enum(backend.native.api.Editors.LDE.PointCloudFileFormat,q.format)
    if not system.LDE.CanExportPointCloud(q.surface):
        raise ZemaxError('POINT_CLOUD_UNAVAILABLE','原生接口报告该曲面不能导出点云。',surface=q.surface)
    copy=system.CopySystem()
    if copy is None:raise ZemaxError('COPY_FAILED','未能创建点云导出副本。')
    owned=OwnedCopyTool(copy)
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        message=copy.LDE.RunTool_ExportPointCloudFile(q.surface,str(path),q.x_sampling,q.y_sampling,q.include_surface_normals,fmt)
        native_message=None if message is None else dict(code=str(message.ErrorCode),text=str(message.Text))
        if message is not None and int(message.ErrorCode)!=0:
            raise ZemaxError('POINT_CLOUD_EXPORT_FAILED','原生点云导出失败。',native_message=native_message)
    except Exception as original:
        try:backend._release_owned(owned)
        except Exception as cleanup:
            backend.requires_reconnect=True
            error=original if isinstance(original,ZemaxError) else ZemaxError('POINT_CLOUD_EXPORT_FAILED',str(original),native_type=type(original).__name__)
            error.details['cleanup_error']=cleanup.as_dict() if isinstance(cleanup,ZemaxError) else dict(message=str(cleanup))
            raise error from original
        raise
    backend._release_owned(owned)
    if not path.is_file():raise ZemaxError('NO_RESULT_DATA','点云导出未生成文件。',path=str(path),native_message=native_message)
    header=read_header(path)
    if header['points']==0:raise ZemaxError('NO_RESULT_DATA','PCD没有有效点。',path=str(path),header=header)
    if (header['width'],header['height'])!=(q.x_sampling,q.y_sampling):
        raise ZemaxError('SETTING_REJECTED','PCD网格未采用请求采样。',requested=[q.x_sampling,q.y_sampling],actual=[header['width'],header['height']])
    expected={'ASCII':'ascii','Binary':'binary','CompressedBinary':'binary_compressed'}[q.format]
    if header['data']!=expected:
        raise ZemaxError('SETTING_REJECTED','PCD文件未采用请求格式。',requested=q.format,actual=header['data'])
    has_normals={'normal_x','normal_y','normal_z'}.issubset(header['fields'])
    if q.include_surface_normals!=has_normals:
        raise ZemaxError('SETTING_REJECTED','PCD法线字段未采用请求设置。',fields=header['fields'])
    return dict(path=str(path),requested=q.model_dump(),header=header,native_message=native_message,
                lens_units=str(system.SystemData.Units.LensUnits),model_revision=backend.revision,
                setting_readback='Method arguments have no native getters; organized WIDTH/HEIGHT, DATA and normal fields checked from native output.',
                coordinate_definition='Selected surface local coordinates in current lens units; organized Y-major grid with X varying fastest, sampled at cell centers; native aperture-invalid sag/normals remain NaN in PCD.',
                copy_closed=owned.system_closed,system_tool_count=0,
                execution='synchronous LDE method; no native task cancellation interface',
                artifacts=[dict(kind='point_cloud',path=str(path))])
