"""Observed finite-conjugate LightSourceAnalysis RGB/tristimulus text outlet."""
import math
import re
from .errors import ZemaxError

NUMBER = r'([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)'


def parse_finite_light_source(text):
    def get(pattern):
        found=re.search(pattern,text,re.M|re.I)
        if not found:
            raise ZemaxError('ANALYSIS_TEXT_UNKNOWN_SHAPE','光源分析报告缺少已确认字段。',pattern=pattern)
        return found
    source=get(r'^(?:光源文件名称|Source file name)\s*:[ \t]*(.*)$').group(1).strip()
    rotation=float(get(r'^(?:旋转角度|Rotation(?: angle)?)\s*:\s*'+NUMBER).group(1))
    surface=int(get(r'^(?:表面|Surface)\s*:\s*(\d+)').group(1))
    size=get(r'^(?:探测器尺寸|Detector size)\s*:\s*'+NUMBER+r'\s*W\s*X\s*'+NUMBER+r'\s*H\s*(\S+)\s*\((\d+)\s*X\s*(\d+)\s*pixels\)')
    width,height=float(size.group(1)),float(size.group(2))
    nx,ny=int(size.group(4)),int(size.group(5))
    if nx<1 or ny<1 or nx*ny>4_000_000 or not all(math.isfinite(v) for v in (width,height,rotation)):
        raise ZemaxError('INVALID_RESULT_DATA','光源分析探测器尺寸无效。',nx=nx,ny=ny)
    quantities={}
    for name,labels in [('peak_illuminance','峰值照度|Peak illuminance'),('transmitted_power','通过功率|Transmitted power'),('source_power','光源功率|Source power')]:
        value=get(r'^(?:'+labels+r')\s*:\s*'+NUMBER+r'\s*([^\r\n]+)')
        numeric=float(value.group(1))
        if not math.isfinite(numeric):
            raise ZemaxError('INVALID_RESULT_DATA','光源分析通量数值无效。',quantity=name)
        quantities[name]=dict(value=numeric,unit=value.group(2).strip())
    heading=get(r'^\s*(?:x像素|xpix(?:el)?)\s+(?:y像素|ypix(?:el)?)\s+R\s+G\s+B\s+Trix\s+Triy\s+Triz\s*$')
    rows=[];seen=set()
    table=re.split(r'(?im)^\s*(?:正常化强度值|Normalized intensity values)\s*:\s*$',text[heading.end():],maxsplit=1)[0]
    for line in table.splitlines():
        if not line.strip():continue
        columns=line.split()
        if len(columns)!=8:
            raise ZemaxError('INVALID_RESULT_DATA','光源RGB/XYZ数据列数错误。',line=line)
        try:
            x,y,r,g,b=map(int,columns[:5]);xyz=list(map(float,columns[5:]))
        except ValueError as exc:
            raise ZemaxError('INVALID_RESULT_DATA','光源RGB/XYZ数据格式错误。',line=line) from exc
        if not 1<=x<=nx or not 1<=y<=ny or (x,y) in seen or any(v<0 or v>255 for v in (r,g,b)) or not all(math.isfinite(v) for v in xyz):
            raise ZemaxError('INVALID_RESULT_DATA','光源RGB/XYZ数据索引或数值错误。',line=line)
        seen.add((x,y));rows.append(dict(x_pixel=x,y_pixel=y,R=r,G=g,B=b,Trix=xyz[0],Triy=xyz[1],Triz=xyz[2]))
    if len(rows)!=nx*ny:
        raise ZemaxError('INVALID_RESULT_DATA','光源RGB/XYZ数据不完整。',expected=nx*ny,actual=len(rows))
    ready=bool(source) and width>0 and height>0
    return dict(kind='light_source',available=ready,reason=None if ready else 'source_or_detector_not_defined',
                input_file=source,input_identity_verified=False,rotation=rotation,surface=surface,
                nx=nx,ny=ny,width=width,height=height,size_unit=size.group(3),quantities=quantities,
                rows=rows,row_count=len(rows),coordinate_source='native text pixel indices; physical mapping unverified')
