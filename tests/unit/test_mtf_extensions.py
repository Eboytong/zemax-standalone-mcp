import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.mtf_results import curve_frequency,map_grid
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[dict(kind='fft_mtf_map'),dict(kind='fft_mtf_map',x_field_width=1,y_field_width=1,y_pixels=2),dict(kind='fft_mtf_map',x_field_width=-1,y_field_width=2),dict(kind='huygens_mtf_vs_field',scatter_rays=True),dict(kind='geometric_mtf_vs_field',image_delta=1)])
def test_invalid_requests(payload):
    with pytest.raises(ValidationError):RunAnalysis(request=payload)

def test_frequency_identity():
    assert curve_frequency('空间频率数据: 10.0000 周期每 mm.',[50,10,30])==10
    with pytest.raises(ZemaxError):curve_frequency('unknown',[10])
    with pytest.raises(ZemaxError):curve_frequency('10.0000',[10,10.00001])

def test_map_pixel_centers():
    q=dict(kind='fft_mtf_map',x_pixels=7,y_pixels=5,x_field_width=14,y_field_width=10,reference_field=2,frequency=50,data_type='Average')
    g=dict(values=[[0]*7 for _ in range(5)],nx=7,ny=5,min_x=-3,min_y=0,dx=2,dy=2,array_order='native')
    map_grid(g,q,dict(fields=[dict(number=2,x=3,y=4)],field_type='Angle',lens_units='Millimeters',mtf_units='CyclesPerMillimeter'))
    assert (g['min_x'],g['min_y'],g['dx'],g['dy'])==(-3,0,2,2)
