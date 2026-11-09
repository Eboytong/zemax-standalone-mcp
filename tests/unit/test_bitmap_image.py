from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.bitmap_image import parse_bitmap_report, verify_bitmap_settings, run_bitmap_image
from zemax_mcp.errors import ZemaxError


def report():
    return '''输入文件 : source.BMP
旋转角度: 90.0000
物高 : 1.0000 度
面 : 7 -
光线/像素 : 10
像素大小 : 0.020 W X 0.030 H 毫米
像尺寸 : 0.060 W X 0.060 H 毫米 (3 X 2像素)
xpix ypix R G B
1 1 10 20 30
1 2 11 21 31
2 1 40 50 60
2 2 41 51 61
3 1 70 80 90
3 2 71 81 91
'''


def test_gbm_contract_retains_confirmed_semantics_and_rejects_geometric_image_options():
    q=RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file='source.bmp',
        rays_per_pixel=20,x_pixels=17,y_pixels=11,x_pixel_size=.02,y_pixel_size=.03))
    assert RunAnalysis.model_validate(q.model_dump())==q
    for name,value in [('rays_x1000',1),('number_of_pixels',33),('wavelength',1),('field',1),
                       ('use_polarization',True),('x_pixels',True),('rays_per_pixel',0),
                       ('x_pixel_size',float('nan')),('y_pixel_size',0),('rotation',float('inf'))]:
        with pytest.raises(ValidationError):
            RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file='source.bmp',**{name:value}))
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file='source.bmp',x_pixels=4096,y_pixels=4096))


def test_non_square_rgb_table_maps_columns_and_top_down_rows_to_y_up():
    parsed=parse_bitmap_report(report())
    assert (parsed['nx'],parsed['ny'])==(3,2)
    assert parsed['channels']['R']==[[11,41,71],[10,40,70]]
    assert parsed['channels']['B']==[[31,61,91],[30,60,90]]
    verify_bitmap_settings(parsed,dict(input_file='source.BMP',rotation=90.,surface=7,nx=3,ny=2))
    normalized=parse_bitmap_report(report()+'\n正常化强度值:\n0.0 0.5 1.0\n0 0 0\n')
    assert normalized['channels']==parsed['channels']
    assert normalized['normalized_intensity']==[[0.,0.,0.],[0.,.5,1.]]


@pytest.mark.parametrize('table',['0 0 0\n','0 0\n0 0 0\n','0 0 0\n0 nan 0\n',
    '0 0 0\n0 inf 0\n','0 0 0\n0 -1 0\n','0 0 0\n0 broken 0\n','0 0 0\n0 0 0\n0 0 0\n'])
def test_normalized_intensity_rejects_incomplete_or_invalid_native_table(table):
    with pytest.raises(ZemaxError) as exc:
        parse_bitmap_report(report()+'\nNormalized intensity values:\n'+table)
    assert exc.value.code=='INVALID_RESULT_DATA'


def test_native_intensity_retains_unclipped_values_and_raw_efficiency():
    parsed=parse_bitmap_report('Efficiency : 122.157 %\n'+report()+'\nNormalized intensity values:\n0 2.5 1e-3\n0 0 0\n')
    assert parsed['normalized_intensity'][1]==[0.,2.5,.001]
    assert parsed['efficiency_percent']==122.157
    assert parse_bitmap_report(report())['normalized_intensity'] is None


@pytest.mark.parametrize('value',['nan','inf','broken'])
def test_native_efficiency_rejects_invalid_header(value):
    with pytest.raises(ZemaxError) as exc:parse_bitmap_report('Efficiency : '+value+' %\n'+report())
    assert exc.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('change',[
    lambda x:x.replace('3 2 71 81 91',''),
    lambda x:x+'1 1 0 0 0\n',
    lambda x:x.replace('3 2 71 81 91','4 2 71 81 91'),
    lambda x:x.replace('3 2 71 81 91','3 2 256 81 91'),
    lambda x:x.replace('3 2 71 81 91','3 2 nope 81 91'),
    lambda x:x.replace('3 X 2','99999 X 99999'),
    lambda x:x.replace('xpix ypix R G B','missing table'),
])
def test_malformed_rgb_result_is_rejected(change):
    with pytest.raises(ZemaxError) as exc:parse_bitmap_report(change(report()))
    assert exc.value.code=='INVALID_RESULT_DATA'


def test_final_readback_uses_report_precision_and_returns_all_differences():
    parsed=parse_bitmap_report(report())
    verify_bitmap_settings(parsed,dict(x_pixel_size=.0204,rotation=90.00004))
    with pytest.raises(ZemaxError) as exc:
        verify_bitmap_settings(parsed,dict(input_file='other.bmp',surface=6,x_pixel_size=.023))
    assert exc.value.code=='SETTING_REJECTED'
    assert len(exc.value.details['differences'])==3


@pytest.mark.parametrize('close_ok',[True,False])
def test_setting_rejection_closes_native_and_preserves_original_error(tmp_path,monkeypatch,close_ok):
    source=tmp_path/'source.bmp';source.write_bytes(b'not read before native')
    native=NS(GetType=lambda:NS(FullName='AS_Default'),SaveTo=lambda p:True,ModifySettings=lambda *args:False)
    tool=NS(GetSettings=lambda:native)
    closed=[]
    backend=NS(directory=tmp_path,requires_reconnect=False,
        _require_sequential=lambda **kwargs:None,get_system_settings=lambda _:dict(lens_units='Millimeters'),
        system=NS(LDE=NS(NumberOfSurfaces=8)),_row=lambda _:None,
        _close_task_native=lambda owner:closed.append(owner) or close_ok)
    monkeypatch.setattr('zemax_mcp.imaging.new_analysis',lambda *args:tool)
    q=RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file=str(source))).request
    with pytest.raises(ZemaxError) as exc:run_bitmap_image(backend,q)
    assert exc.value.code=='SETTING_REJECTED' and exc.value.details['setting']=='GBM_INPUT'
    assert len(closed)==1 and backend.requires_reconnect is (not close_ok)


def test_missing_resource_is_rejected_before_creating_analysis(tmp_path,monkeypatch):
    backend=NS(_require_sequential=lambda **kwargs:None,
        get_system_settings=lambda _:dict(lens_units='Millimeters'))
    monkeypatch.setattr('zemax_mcp.imaging.new_analysis',lambda *args:pytest.fail('unexpected native creation'))
    q=RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file=str(tmp_path/'missing.bmp'))).request
    with pytest.raises(ZemaxError) as exc:run_bitmap_image(backend,q)
    assert exc.value.code=='INVALID_RESOURCE'
