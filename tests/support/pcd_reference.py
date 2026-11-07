"""Independent PCD float payload reader for native coordinate references."""
import struct
from pathlib import Path


def rows(path,header):
    raw=Path(path).read_bytes();offset=raw.index(b'DATA ');start=raw.index(b'\n',offset)+1;data=raw[start:]
    fields=header['fields'];count=header['points'];width=len(fields)
    if header['data']=='ascii':return [dict(zip(fields,map(float,line.split()),strict=True))for line in data.splitlines()if line.strip()]
    if header['data']=='binary':return [dict(zip(fields,struct.unpack_from('<'+'f'*width,data,i*width*4),strict=True))for i in range(count)]
    compressed,expected=struct.unpack_from('<II',data);data=data[8:8+compressed];out=bytearray();i=0
    while i<len(data):
        code=data[i];i+=1
        if code<32:
            length=code+1;out.extend(data[i:i+length]);i+=length
        else:
            length=code>>5;back=(code&31)<<8
            if length==7:length+=data[i];i+=1
            back+=data[i];i+=1;at=len(out)-back-1
            for _ in range(length+2):out.append(out[at]);at+=1
    assert len(out)==expected==count*width*4
    return [{field:struct.unpack_from('<f',out,(j*count+i)*4)[0]for j,field in enumerate(fields)}for i in range(count)]
