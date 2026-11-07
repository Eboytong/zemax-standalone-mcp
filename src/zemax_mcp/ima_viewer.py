"""Documented IMA/BIM intensities and the formal ImageSimulation source view."""
import math
import struct
import uuid
from pathlib import Path
from typing import Literal
from pydantic import field_validator
from .schema import Request, PositiveIndex
from .errors import ZemaxError

CELL_LIMIT = 4_000_000


class ImaBimViewer(Request):
    kind: Literal['ima_bim_viewer']
    input_file: str
    map_index: PositiveIndex = 1
    method: Literal['native_source_bitmap', 'file'] = 'native_source_bitmap'

    @field_validator('input_file')
    @classmethod
    def filename(cls, value):
        if not value.strip() or any(c in value for c in '/\\:') or Path(value).suffix.lower() not in {'.ima', '.bim'}:
            raise ValueError('input_file须为Images目录内的IMA/BIM文件名。')
        return value


def parse_image(raw, suffix, map_index=1):
    """Return selected full-precision plane with X right/Y up, as documented."""
    def invalid(reason):
        raise ZemaxError('INVALID_RESOURCE_DATA', 'IMA/BIM输入无效。', reason=reason)
    def dimensions(nx, ny, maps):
        if not (2 <= nx <= 8000 and nx == ny and 1 <= maps <= 32767):
            invalid('本机格式要求2..8000的方形网格和正图层数。')
        if nx*ny*maps > CELL_LIMIT:
            invalid('图像总样本数超过结构化读取上限。')
        if map_index < 1 or map_index > maps:
            raise ZemaxError('INDEX_OUT_OF_RANGE', '图层编号越界。', requested=map_index, maps=maps)
    if suffix.lower() == '.bim':
        if len(raw) < 8:invalid('BIM缺少两个int32尺寸。')
        nx, ny = struct.unpack_from('<ii', raw)
        maps = 1
        dimensions(nx, ny, maps)
        if len(raw) != 8+nx*ny*8:invalid('BIM长度与float64像素数不一致。')
        pixels = struct.unpack_from('<'+str(nx*ny)+'d', raw, 8)
        form = 'BIM float64 bottom-up'
    elif suffix.lower() == '.ima':
        if raw[:2] == b'\0\0':
            if len(raw) < 6:invalid('二进制IMA缺少三个int16头字段。')
            _, nx, maps = struct.unpack_from('<hhh', raw)
            ny = nx
            dimensions(nx, ny, maps)
            if len(raw) != 6+nx*ny*maps:invalid('二进制IMA长度与uint8图层数不一致。')
            start = 6+(map_index-1)*nx*ny
            pixels = raw[start:start+nx*ny]
            form = 'IMA binary uint8 top-down'
        else:
            try:
                lines = raw.decode('ascii').splitlines()
                nx = int(lines[0]);ny = nx;maps = 1
            except (UnicodeError, ValueError, IndexError):invalid('文本IMA缺少ASCII尺寸。')
            dimensions(nx, ny, maps)
            if len(lines) != ny+1 or any(len(row) != nx or any(c not in '0123456789' for c in row) for row in lines[1:]):
                invalid('文本IMA要求N行，每行N个0..9数字。')
            pixels = [int(c) for row in lines[1:] for c in row]
            form = 'IMA ASCII digits top-down'
    else:invalid('扩展名必须为IMA或BIM。')
    if any(not math.isfinite(v) or v < 0 for v in pixels):invalid('像素强度必须有限且非负。')
    values = [list(pixels[i*nx:(i+1)*nx]) for i in range(ny)]
    if suffix.lower() == '.ima':values.reverse()
    peak = max(pixels)
    return dict(nx=nx, ny=ny, maps=maps, map_index=map_index, format=form, peak=peak,
                values=values, normalized=[[v/peak if peak else 0. for v in row] for row in values])


def run_viewer(b, q):
    b._require_work()
    root = Path(str(b.native.application.ImagesDir))
    matches = [p for p in root.iterdir() if p.is_file() and p.name.casefold() == q.input_file.casefold()]
    if len(matches) != 1:
        raise ZemaxError('INVALID_RESOURCE', 'Images目录中找不到唯一输入文件。', requested=q.input_file, directory=str(root))
    path = matches[0]
    try:
        if path.stat().st_size > 8*CELL_LIMIT+8:
            raise ZemaxError('INVALID_RESOURCE_DATA', '图像文件超过结构化读取上限。', cell_limit=CELL_LIMIT)
        image = parse_image(path.read_bytes(), path.suffix, q.map_index)
    except OSError as exc:
        raise ZemaxError('RESOURCE_READ_FAILED', str(exc), path=str(path)) from exc
    if q.method == 'native_source_bitmap':
        b._require_sequential(focused=True)
    def flow(task):
        b._cancel_boundary(task)
        payload = task['payload'] = dict(analysis_kind=q.kind, computation_method=q.method,
            input_identity=dict(path=str(path), format=image['format'], maps=image['maps'], map_index=q.map_index),
            actual_settings=dict(request=q.model_dump(), configuration=task['context']['configuration']),
            normalization=dict(source='selected documented file plane', peak=image['peak'], zero_input=image['peak']==0),
            series=[], grids=[], native_task_id=None)
        if q.method == 'native_source_bitmap':
            from .analysis_models import ImageSimulation
            from .imaging import run_imaging
            native_path = path
            extracted = image['maps'] not in (1, 3)
            if extracted:
                native_path = root/('mcp_viewer_'+uuid.uuid4().hex+'.BIM')
            original_error = None
            try:
                if extracted:
                    pixels = [v for row in image['values'] for v in row]
                    native_path.write_bytes(struct.pack('<ii', image['nx'], image['ny'])+struct.pack('<'+str(len(pixels))+'d', *pixels))
                payload['native_input_identity'] = dict(path=str(native_path), source='selected documented plane converted to BIM float64' if extracted else 'original file')
                child = yield from b._child_job(task, lambda req: run_imaging(b, req), ImageSimulation(kind='image_simulation', input_file=native_path.name,
                    wavelength=1, show_as='SourceBitmap', oversampling='None', guard_band='None', aberrations='None', psf_x_points=3, psf_y_points=3))
            except BaseException as exc:
                original_error = exc
                raise
            finally:
                if extracted:
                    try:
                        native_path.unlink(missing_ok=True)
                        payload['temporary_input_removed'] = True
                    except OSError as exc:
                        cleanup = dict(path=str(native_path), reason=str(exc))
                        payload['temporary_input_cleanup_error'] = cleanup
                        if isinstance(original_error, ZemaxError):
                            original_error.details['temporary_input_cleanup_error'] = cleanup
                        elif original_error is None:
                            raise ZemaxError('RESOURCE_CLEANUP_FAILED', '临时源图删除失败。', **cleanup) from exc
            grids = child.get('grids', [])
            if len(grids) != 3 or any((g['nx'], g['ny']) != (image['nx'], image['ny']) for g in grids):
                raise ZemaxError('INVALID_RESULT_DATA', '原生源图尺寸或RGB通道与文件不一致。', native_task_id=child['task']['task_id'])
            actual = child['task']['settings']['native']
            if actual['InputFile'] != native_path.name or actual['ShowAs'] != 'SourceBitmap':
                raise ZemaxError('SETTING_REJECTED', '原生源图输入身份未采用。', actual=actual)
            payload.update(native_task_id=child['task']['task_id'], native_settings=actual,
                native_channel='RGB'[q.map_index-1] if image['maps']==3 else 'R/G/B identical',
                native_display_definition='8-bit RGB source display; separate from full-precision per-map normalization')
        display_grids = grids if q.method == 'native_source_bitmap' else []
        for iy, row in enumerate(image['values']):
            b._cancel_boundary(task)
            for ix, value in enumerate(row):
                task['rows'].append(dict(index=iy*image['nx']+ix, x=ix, y=iy, map_index=q.map_index, intensity=value, normalized_intensity=image['normalized'][iy][ix]))
            yield
        for n, key in enumerate(['values', 'normalized']):
            payload['grids'].append(dict(grid=n, nx=image['nx'], ny=image['ny'], min_x=0, min_y=0, dx=1, dy=1,
                x_label='Pixel X', y_label='Pixel Y', x_unit='pixel', y_unit='pixel',
                value_unit='relative intensity', description='File intensity' if n==0 else 'Peak-normalized file intensity',
                array_order='values[y][x]; bottom-left pixel center index (0,0)', values=image[key]))
        for grid in display_grids:
            payload['grids'].append({**grid, 'grid':len(payload['grids']), 'source':'native SourceBitmap 8-bit display'})
        task['summary'] = dict(pixels=image['nx']*image['ny'], map_index=q.map_index, peak=image['peak'])
    return b._composite(q.kind, q.model_dump(), flow, require_sequential=q.method!='file')
