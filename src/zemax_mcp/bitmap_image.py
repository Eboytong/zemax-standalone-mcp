"""Documented GBM configuration and native RGB report result adapter."""
import math
import re
import uuid
from pathlib import Path

from .data import unwrap
from .errors import ZemaxError
from .native_bitmap import read_bitmap

LIMIT = 4_000_000
NUMBER = r'([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)'


def parse_bitmap_report(text):
    def match(pattern):
        found = re.search(pattern, text, re.I|re.M)
        if not found:
            raise ZemaxError('INVALID_RESULT_DATA','几何位图报告缺少必要设置或RGB表。',pattern=pattern)
        return found
    source = match(r'^(?:输入文件|Input file)\s*:\s*(.+)$').group(1).strip()
    rotation = float(match(r'^(?:旋转角度|Rotation(?: angle)?)\s*:\s*'+NUMBER).group(1))
    field = match(r'^(?:物高|Field (?:Y )?size)\s*:\s*'+NUMBER+r'\s*(\S+)')
    surface = int(match(r'^(?:面|Surface)\s*:\s*(\d+)').group(1))
    rays = int(match(r'^(?:光线/像素|Rays/Pixel)\s*:\s*(\d+)').group(1))
    pixel = match(r'^(?:像素大小|Pixel size)\s*:\s*'+NUMBER+r'\s*W\s*X\s*'+NUMBER+r'\s*H\s*(\S+)')
    size = match(r'^(?:像尺寸|Image size)\s*:\s*'+NUMBER+r'\s*W\s*X\s*'+NUMBER+r'\s*H.*?\((\d+)\s*X\s*(\d+)')
    nx, ny = int(size.group(3)), int(size.group(4))
    if nx<1 or ny<1 or nx*ny>LIMIT:
        raise ZemaxError('INVALID_RESULT_DATA','几何位图报告尺寸无效。',nx=nx,ny=ny)
    header = match(r'^\s*xpix\s+ypix\s+R\s+G\s+B\s*$')
    sections = re.split(r'(?im)^\s*(?:正常化强度值|Normalized intensity values)\s*:\s*$',text[header.end():],maxsplit=1)
    values = {channel:[[None]*nx for _ in range(ny)] for channel in 'RGB'}
    seen = set()
    for line in sections[0].splitlines():
        if not line.strip():
            continue
        entry = re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*',line)
        if not entry:
            raise ZemaxError('INVALID_RESULT_DATA','几何位图RGB数据行格式无效。',line=line)
        x,y,*rgb = map(int,entry.groups())
        if not 1<=x<=nx or not 1<=y<=ny or (x,y) in seen or any(v>255 for v in rgb):
            raise ZemaxError('INVALID_RESULT_DATA','几何位图RGB索引重复、越界或通道值越界。',row=[x,y,*rgb])
        seen.add((x,y))
        # Native bitmap controls establish report y=1 is the top image row.
        for channel, value in zip('RGB',rgb,strict=True):
            values[channel][ny-y][x-1] = value
    if len(seen)!=nx*ny:
        raise ZemaxError('INVALID_RESULT_DATA','几何位图RGB数据不完整。',expected=nx*ny,actual=len(seen))
    intensity = None
    if len(sections)==2:
        lines=[line for line in sections[1].splitlines() if line.strip()]
        if len(lines)!=ny:
            raise ZemaxError('INVALID_RESULT_DATA','几何位图正常化强度表行数无效。',expected=ny,actual=len(lines))
        intensity=[]
        for index,line in enumerate(lines,1):
            try:row=[float(value) for value in line.split()]
            except ValueError as exc:
                raise ZemaxError('INVALID_RESULT_DATA','几何位图正常化强度行格式无效。',row=index,line=line) from exc
            if len(row)!=nx or any(not math.isfinite(value) or value<0 for value in row):
                raise ZemaxError('INVALID_RESULT_DATA','几何位图正常化强度尺寸或数值无效。',row=index,expected=nx,actual=len(row))
            intensity.append(row)
        intensity.reverse()
    efficiency_match=re.search(r'^(?:效率|Efficiency)\s*:\s*(\S+)\s*%',text,re.I|re.M)
    efficiency=None
    if efficiency_match:
        try:efficiency=float(efficiency_match.group(1))
        except ValueError as exc:
            raise ZemaxError('INVALID_RESULT_DATA','几何位图原生效率格式无效。',value=efficiency_match.group(1)) from exc
        if not math.isfinite(efficiency):
            raise ZemaxError('INVALID_RESULT_DATA','几何位图原生效率为非有限数值。',value=efficiency_match.group(1))
    numeric = [rotation,float(field.group(1)),float(pixel.group(1)),float(pixel.group(2)),float(size.group(1)),float(size.group(2))]
    if not all(math.isfinite(v) for v in numeric):
        raise ZemaxError('INVALID_RESULT_DATA','几何位图报告设置包含非有限值。')
    return dict(input_file=source,rotation=rotation,field_size=float(field.group(1)),field_unit=field.group(2),
                surface=surface,rays_per_pixel=rays,nx=nx,ny=ny,
                x_pixel_size=float(pixel.group(1)),y_pixel_size=float(pixel.group(2)),
                pixel_unit=pixel.group(3),width=float(size.group(1)),height=float(size.group(2)),channels=values,
                normalized_intensity=intensity,efficiency_percent=efficiency)


def verify_bitmap_settings(parsed, expected):
    errors = []
    for name, value in expected.items():
        actual = parsed.get(name)
        same = actual==value
        if isinstance(value,float) and isinstance(actual,(float,int)):
            # Header field/rotation precision 4 decimals; pixel sizes 3 decimals.
            tolerance = 5.1e-4 if name in {'x_pixel_size','y_pixel_size'} else 5.1e-5
            same = math.isfinite(actual) and abs(actual-value)<=tolerance
        if not same:
            errors.append(dict(setting=name,requested=value,actual=actual))
    if errors:
        raise ZemaxError('SETTING_REJECTED','几何位图原生报告未确认最终请求设置。',differences=errors)


def collect_bitmap_image(backend,task):
    native = unwrap(task['native'].GetResults())
    path = backend.directory/(task['task_id']+'_native.txt')
    if native is None or not native.IsValid:
        raise ZemaxError('ANALYSIS_FAILED','几何位图原生结果无效。')
    if not native.GetTextFile(str(path)):
        raise ZemaxError('EXPORT_FAILED','几何位图原生RGB文本导出失败。',path=str(path))
    try:
        parsed = parse_bitmap_report(path.read_text(encoding='utf-16'))
        verify_bitmap_settings(parsed,task['settings']['expected_readback'])
        output = task['settings']['native_output_file']
        bitmap = read_bitmap(output,LIMIT)
        if bitmap['nx']!=parsed['nx'] or bitmap['ny']!=parsed['ny'] or bitmap['channels']!=parsed['channels']:
            raise ZemaxError('INVALID_RESULT_DATA','几何位图RGB文本与原生显示像素不一致。',native_output=output)
    except ZemaxError as exc:
        exc.details['native_text'] = str(path)
        raise
    header = {key:value for key,value in parsed.items() if key not in {'channels','normalized_intensity'}}
    task['settings']['actual_readback'] = header
    grids = [dict(grid=i,channel=channel,nx=parsed['nx'],ny=parsed['ny'],
                  values=parsed['channels'][channel],min_x=.5,min_y=.5,dx=1,dy=1,
                  x_label='Display pixel X',y_label='Display pixel Y',
                  x_unit='output_pixel',y_unit='output_pixel',value_unit='8-bit display RGB',
                  description='Native geometric bitmap '+channel,invalid_count=0,
                  array_order='values[y][x]; X right, Y up',
                  data_source='native RGB text; native BMP correspondence confirmed')
             for i,channel in enumerate('RGB')]
    if parsed['normalized_intensity'] is not None:
        grids.append(dict(grid=3,channel='I',quantity='native_normalized_intensity',nx=parsed['nx'],ny=parsed['ny'],
            values=parsed['normalized_intensity'],min_x=.5,min_y=.5,dx=1,dy=1,
            x_label='Display pixel X',y_label='Display pixel Y',x_unit='output_pixel',y_unit='output_pixel',
            value_unit='native normalized intensity',description='Native geometric bitmap normalized intensity',invalid_count=0,
            array_order='values[y][x]; X right, Y up',data_source='native normalized intensity text table',
            normalization='native reported values; no conversion from clipped RGB'))
    return dict(analysis_kind='geometric_bitmap_image',structured_data_available=True,grids=grids,series=[],
                computation_method='native GeometricBitmapImageAnalysis; documented GBM CFG and RGB text',
                actual_settings=task['settings'],native_header=header,
                input_selection=dict(identity_verified=True,path=task['settings']['input_resource'],
                                     reported_name=parsed['input_file'],source='GBM_INPUT and native report'),
                normalization='native display normalization; 8-bit RGB values',
                normalized_intensity_available=parsed['normalized_intensity'] is not None,
                native_efficiency=dict(value=parsed['efficiency_percent'],unit='percent',
                    source='native report header',independently_verified=False),
                physical_pixel_sizes=dict(x=parsed['x_pixel_size'],y=parsed['y_pixel_size'],unit=parsed['pixel_unit']),
                physical_origin_verified=False,
                native_messages=[dict(code=str(native.GetMessageAt(i).ErrorCode),text=str(native.GetMessageAt(i).Text))
                                 for i in range(int(native.NumberOfMessages))],
                artifacts=[dict(kind='native_text',path=str(path)),dict(kind='native_image',path=output)])


def run_bitmap_image(backend,request):
    from .imaging import new_analysis
    backend._require_sequential(focused=True)
    system = backend.get_system_settings(None)
    if system['lens_units']!='Millimeters':
        raise ZemaxError('UNIT_MISMATCH','当前GBM报告适配要求毫米镜头单位。',actual=system['lens_units'])
    source = Path(request.input_file)
    if not source.is_absolute():
        if len(source.parts)!=1:
            raise ZemaxError('INVALID_RESOURCE','位图使用Images资源名或绝对路径。',path=request.input_file)
        source = Path(str(backend.native.application.ImagesDir))/source
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() not in {'.bmp','.jpg','.jpeg','.png'}:
        raise ZemaxError('INVALID_RESOURCE','几何位图输入必须是存在的BMP/JPG/PNG文件。',path=str(source))
    surface = request.surface if request.surface is not None else backend.system.LDE.NumberOfSurfaces-1
    backend._row(surface)
    output = backend.directory/('bitmap_'+uuid.uuid4().hex+'.bmp')
    cfg = backend.directory/('bitmap_'+uuid.uuid4().hex+'.CFG')
    expected = dict(input_file=str(source),surface=surface,field_size=request.field_size,
                    rotation=request.rotation,rays_per_pixel=request.rays_per_pixel,nx=request.x_pixels,
                    ny=request.y_pixels,x_pixel_size=request.x_pixel_size,y_pixel_size=request.y_pixel_size)
    actual = dict(kind=request.kind,requested=request.model_dump(),input_resource=str(source),
                  native_output_file=str(output),cfg_path=str(cfg),cfg_operations=[],expected_readback=expected,
                  remaining_settings='native defaults for settings without confirmed documented keys')
    tool = new_analysis(backend,'GeometricBitmapImageAnalysis')
    try:
        native = unwrap(tool.GetSettings())
        actual['native_settings_type'] = str(native.GetType().FullName)
        if not native.SaveTo(str(cfg)):
            raise ZemaxError('CFG_EXPORT_FAILED','几何位图配置导出失败。',path=str(cfg))
        entries = dict(GBM_INPUT=str(source),GBM_OUTPUT=str(output),GBM_SURFACE=surface,
                       GBM_FIELDSIZE=request.field_size,GBM_ROTATION=request.rotation,GBM_RAYS=request.rays_per_pixel,
                       GBM_XPIX=request.x_pixels,GBM_YPIX=request.y_pixels,
                       GBM_XSIZ=request.x_pixel_size,GBM_YSIZ=request.y_pixel_size)
        for key,value in entries.items():
            accepted = bool(native.ModifySettings(str(cfg),key,str(value)))
            actual['cfg_operations'].append(dict(key=key,value=value,accepted=accepted))
            if not accepted:
                raise ZemaxError('SETTING_REJECTED','几何位图配置键被拒绝。',setting=key,requested=value)
        if not native.LoadFrom(str(cfg)):
            raise ZemaxError('CFG_LOAD_FAILED','几何位图配置加载失败。',path=str(cfg))
    except Exception:
        if not backend._close_task_native(dict(native=tool)):
            backend.requires_reconnect = True
        raise
    return backend._start_task('analysis',tool,actual,analysis=True,collector=lambda task:collect_bitmap_image(backend,task))
