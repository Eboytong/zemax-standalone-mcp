"""Documented version-1 binary and text ZBF sample readers."""
import itertools
import math
import struct
from .files import input_path
from .errors import ZemaxError


def sample_coordinates(index,nx,ny,dx,dy,unit):
    ix,iy=index%nx,index//nx
    return dict(ix=ix,iy=iy,x=(ix-nx/2)*dx,y=(iy-ny/2)*dy,length_unit=unit)


def read_beam(path,start=0,count=200,include_coordinates=False):
    if type(start) is not int or start<0 or type(count) is not int or not 1<=count<=1000:
        raise ZemaxError("INVALID_ARGUMENT","start必须是非负整数，count必须为1至1000的整数。")
    if type(include_coordinates)is not bool:raise ZemaxError("INVALID_ARGUMENT","include_coordinates必须为布尔值。")
    path=input_path(str(path),{".zbf"})
    with path.open("rb") as stream:text_format=stream.read(1)==b"A"
    rows=[]
    try:
        with path.open("r",encoding="ascii") if text_format else path.open("rb") as stream:
            if text_format:
                if stream.readline().strip()!="A":raise ValueError("文本ZBF必须以单独的A行开始")
                tokens=(token for line in stream for token in line.split())
                integers=[int(next(tokens)) for _ in range(9)]
                d=[float(next(tokens).replace("D","E").replace("d","e")) for _ in range(20)]
            else:
                header=stream.read(196)
                if len(header)!=196:raise ValueError("ZBF二进制头不完整")
                integers=list(struct.unpack("<9i",header[:36]));d=struct.unpack("<20d",header[36:])
            version,nx,ny,pol,units,*_=integers
            if version!=1 or nx<=0 or ny<=0 or nx*ny>16777216 or pol not in {0,1} or units not in range(4):
                raise ZemaxError("UNSUPPORTED_BEAM_FORMAT","支持手册定义的version=1二进制及文本ZBF。",version=version)
            if not all(math.isfinite(v) for v in d[:12]):raise ValueError("光束头包含非有限参数")
            total=nx*ny
            if start>total:raise ZemaxError("INDEX_OUT_OF_RANGE","光束样本起点越界。")
            end=min(total,start+count)
            for component in range(1+pol):
                if text_format:
                    # Each component is a separate full complex-field block.
                    for _ in itertools.islice(tokens,2*start):pass
                    pairs=[(float(next(tokens).replace("D","E").replace("d","e")),
                            float(next(tokens).replace("D","E").replace("d","e"))) for _ in range(end-start)]
                    if component<pol:
                        for _ in itertools.islice(tokens,2*(total-end)):pass
                else:
                    stream.seek(196+16*(component*total+start))
                    raw=stream.read(16*(end-start))
                    if len(raw)!=16*(end-start):raise ValueError("当前页复场数据不完整")
                    pairs=struct.iter_unpack("<dd",raw)
                for j,(real,imag) in enumerate(pairs):
                    prefix="ex" if component==0 else "ey"
                    if component==0:rows.append(dict(index=start+j))
                    rows[j].update({prefix+"_real":real if math.isfinite(real) else None,
                                    prefix+"_imag":imag if math.isfinite(imag) else None})
    except (ValueError,StopIteration,UnicodeError,struct.error) as exc:
        raise ZemaxError("INVALID_BEAM_FILE",str(exc),path=str(path)) from exc
    unit=["Millimeters","Centimeters","Inches","Meters"][units]
    if include_coordinates:
        for row in rows:row.update(sample_coordinates(row["index"],nx,ny,d[0],d[1],unit))
    return dict(path=str(path),format_version=version,format="zbf_text" if text_format else "zbf_binary",
        nx=nx,ny=ny,polarized=bool(pol),length_unit=["Millimeters","Centimeters","Inches","Meters"][units],
        dx=d[0],dy=d[1],pilot_x=dict(z=d[2],rayleigh=d[3],waist=d[4]),
        pilot_y=dict(z=d[5],rayleigh=d[6],waist=d[7]),wavelength_in_medium=d[8],index=d[9],
        receiver_efficiency_raw=d[10],system_efficiency_raw=d[11],
        coupling_interpretation="文件中的零值也用于未计算耦合；须结合生成时设置解释。",
        rows=rows,total=total,next_start=end if end<total else None,
        invalid_count=sum(v is None for row in rows for key,v in row.items() if key.endswith(("_real","_imag"))),
        sample_order="X fastest; first sample is negative X, negative Y",
        coordinates_included=include_coordinates,
        coordinate_definition=dict(frame="beam local XY",formula="ix=index%nx; iy=index//nx; x=(ix-nx/2)*dx; y=(iy-ny/2)*dy",unit=unit),
        source="OpticStudio 2024 R2 sections 3.3.3.11.6.1 and 3.3.3.11.6.2")


def iter_beam_samples(path,include_coordinates=False):
    """Stream complete complex fields for CSV without retaining the full beam."""
    info=read_beam(path,0,1);path=input_path(str(path),{".zbf"})
    text=info["format"]=="zbf_text";total=info["total"];polarized=info["polarized"]
    try:
        with path.open("r",encoding="ascii") if text else path.open("rb") as ex:
            with path.open("r",encoding="ascii") if text else path.open("rb") as ey:
                if text:
                    ex.readline();ey.readline()
                    xt=(v for line in ex for v in line.split());yt=(v for line in ey for v in line.split())
                    for _ in itertools.islice(xt,29):pass
                    for _ in itertools.islice(yt,29+2*total):pass
                    def pair(tokens):return tuple(float(next(tokens).replace("D","E").replace("d","e"))for _ in range(2))
                else:
                    ex.seek(196);ey.seek(196+16*total)
                for i in range(total):
                    values=pair(xt) if text else struct.unpack("<dd",ex.read(16))
                    row=dict(index=i,ex_real=values[0],ex_imag=values[1])
                    if polarized:
                        values=pair(yt) if text else struct.unpack("<dd",ey.read(16))
                        row.update(ey_real=values[0],ey_imag=values[1])
                    if include_coordinates:
                        row.update(sample_coordinates(i,info["nx"],info["ny"],info["dx"],info["dy"],info["length_unit"]))
                    yield {key:(value if isinstance(value,str)or math.isfinite(value)else None)for key,value in row.items()}
    except (ValueError,StopIteration,UnicodeError,struct.error,RuntimeError)as exc:
        raise ZemaxError("INVALID_BEAM_FILE","复场数据无法读取。",path=str(path),reason=str(exc))from exc
