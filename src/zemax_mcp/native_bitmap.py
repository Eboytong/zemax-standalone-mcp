"""Read installed native uncompressed RGB BMP output in pixel coordinates."""
import struct
from pathlib import Path
from .errors import ZemaxError


def read_bitmap(path,limit=4_000_000):
    path=Path(path)
    with path.open('rb')as stream:
        header=stream.read(54)
        if len(header)!=54 or header[:2]!=b'BM':raise ZemaxError('INVALID_RESULT_DATA','原生输出不是完整BMP文件。',path=str(path))
        offset=struct.unpack_from('<I',header,10)[0]
        size,w,h,planes,bits,compression=struct.unpack_from('<IiiHHI',header,14)
        if size<40 or planes!=1 or bits not in [24,32]or compression!=0:
            raise ZemaxError('UNSUPPORTED_RESULT_FORMAT','原生BMP像素格式不受支持。',bits=bits,compression=compression,dib_size=size)
        if w<=0 or h==0 or w*abs(h)>limit or offset<14+size:
            raise ZemaxError('INVALID_RESULT_DATA','原生BMP尺寸或像素偏移无效。',width=w,height=h,pixel_limit=limit)
        ny=abs(h);stride=((w*bits+31)//32)*4
        stream.seek(offset);raw=stream.read(stride*ny)
        if len(raw)!=stride*ny:raise ZemaxError('INVALID_RESULT_DATA','原生BMP像素数据不完整。',path=str(path))
    planes={c:[]for c in 'RGB'};step=bits//8
    for y in range(ny):
        row=raw[y*stride:(y+1)*stride]
        for c,index in [('R',2),('G',1),('B',0)]:planes[c].append([row[x*step+index]for x in range(w)])
    if h<0:
        for values in planes.values():values.reverse()
    return dict(nx=w,ny=ny,channels=planes,bits_per_pixel=bits,native_row_order='top_down'if h<0 else'bottom_up',array_order='values[y][x]',coordinate_definition='output pixel centers; X right, Y up',dx=1,dy=1,min_x=.5,min_y=.5)
