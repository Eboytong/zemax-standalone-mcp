import struct
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.native_bitmap import read_bitmap
from zemax_mcp.errors import ZemaxError


def bitmap(path,bits=24,height=2):
    w=3;stride=(w*bits+31)//32*4;rows=[]
    for color in [(255,0,0),(0,0,255)]:
        b,g,r=color;row=bytes([b,g,r]+([0]if bits==32 else[]))*w
        rows.append(row+bytes(stride-len(row)))
    if height<0:rows.reverse()
    data=b''.join(rows)
    path.write_bytes(struct.pack('<2sIHHI',b'BM',54+len(data),0,0,54)+struct.pack('<IiiHHIIiiII',40,w,height,1,bits,0,len(data),0,0,0,0)+data)


@pytest.mark.parametrize('bits,height',[(24,2),(24,-2),(32,2),(32,-2)])
def test_bmp_row_order_and_channels(tmp_path,bits,height):
    path=tmp_path/'native.bmp';bitmap(path,bits,height)
    result=read_bitmap(path)
    assert (result['nx'],result['ny'])==(3,2)
    assert result['channels']['B']==[[255]*3,[0]*3]
    assert result['channels']['R']==[[0]*3,[255]*3]
    assert result['array_order']=='values[y][x]'


@pytest.mark.parametrize('mode',['truncated','limit','compression'])
def test_invalid_native_output(tmp_path,mode):
    path=tmp_path/'native.bmp';bitmap(path)
    if mode=='truncated':path.write_bytes(path.read_bytes()[:-1])
    if mode=='compression':
        data=bytearray(path.read_bytes());struct.pack_into('<I',data,30,1);path.write_bytes(data)
    with pytest.raises(ZemaxError):read_bitmap(path,limit=1 if mode=='limit'else 100)


def test_native_bmp_export_produces_real_png(tmp_path):
    from zemax_mcp.plotting import export_image
    path=tmp_path/'native.bmp';bitmap(path)
    output=tmp_path/'export.png'
    result=export_image(dict(artifacts=[dict(kind='native_image',path=str(path))]),NS(source='native',item=0),output)
    assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert result['image_source']=='native'
