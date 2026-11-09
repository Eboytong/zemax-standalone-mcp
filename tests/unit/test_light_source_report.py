from pathlib import Path
import pytest
from zemax_mcp.image_viewers import parse_light_source_text
from zemax_mcp.errors import ZemaxError


def report(source='',width=0):
    return f'''光源分析数据列表
光源文件名称 : {source}
旋转角度 : 0.0000
表面 : 2 -
探测器尺寸 : {width:.3f} W X {width:.3f} H 毫米 (2 X 1 pixels)
峰值照度 : 0 Lumens/cm^2
通过功率 : 0 Lumens
光源功率 : 0 Lumens
x像素 y像素 R G B Trix Triy Triz
1 1 0 0 0 0.000E+00 0.000E+00 0.000E+00
2 1 0 0 0 0.000E+00 0.000E+00 0.000E+00
'''


def test_blank_finite_source_is_unavailable_despite_complete_zero_table():
    parsed=parse_light_source_text(report())
    assert not parsed['available'] and parsed['reason']=='source_or_detector_not_defined'
    assert parsed['row_count']==2 and parsed['input_file']==''
    assert parsed['quantities']['source_power']==dict(value=0.,unit='Lumens')
    assert parsed['input_identity_verified'] is False


def test_named_input_is_reported_without_claiming_verified_identity():
    parsed=parse_light_source_text(report('controlled.dat',1))
    assert parsed['available'] and parsed['input_identity_verified'] is False
    assert parsed['width']==1 and parsed['size_unit']=='毫米'


@pytest.mark.parametrize('transform',[
    lambda s:s.replace('2 1 0 0 0','1 1 0 0 0'),
    lambda s:s.replace('2 1 0 0 0','3 1 0 0 0'),
    lambda s:s.replace('2 1 0 0 0','2 1 256 0 0'),
    lambda s:s.replace('2 1 0 0 0','2 1 nope 0 0'),
    lambda s:s.replace('0.000E+00','NaN'),
    lambda s:s[:s.index('2 1 0 0 0')],
])
def test_invalid_finite_table_is_rejected(transform):
    with pytest.raises(ZemaxError) as exc:parse_light_source_text(transform(report()))
    assert exc.value.code=='INVALID_RESULT_DATA'


def test_saved_native_finite_report():
    root=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
    folder=root/'.local/evidence/development/D005/light-source-finite-20261109'
    reports=list(folder.glob('*.txt'))
    if not reports:pytest.skip('retained local native evidence absent')
    parsed=parse_light_source_text(reports[0].read_text(encoding='utf-16'))
    assert parsed['nx']==parsed['ny']==40 and parsed['row_count']==1600
    assert not parsed['available'] and parsed['input_file']==''
    assert all(all(row[key]==0 for key in ('R','G','B','Trix','Triy','Triz')) for row in parsed['rows'])
