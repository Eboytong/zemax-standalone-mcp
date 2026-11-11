import math

import pytest
from pydantic import ValidationError

from zemax_mcp.confocal import ConfocalResponse,disk_pixel_area,grid_metrics,half_width
from zemax_mcp.errors import ZemaxError


def request(**kw):
    return dict(kind='confocal_response',illumination=dict(model='a.zos'),detection=dict(model='b.zos'),
        offsets_mm=[-2,-1,0,1,2],pinhole_diameters_um=[1,20])|kw


@pytest.mark.parametrize('changes',[
    dict(offsets_mm=[0,1]),dict(offsets_mm=[0,0,1,2,3]),dict(pinhole_diameters_um=[0]),
    dict(pinhole_diameters_um=[1,1]),dict(image_delta_um=0),dict(offsets_mm=[-2,-1,0,1,float('inf')]),
    dict(budget_seconds=0),dict(detection_magnification=0),dict(image_sampling='S_512x512'),
    dict(image_sampling='S_256x256',offsets_mm=list(range(20))),
])
def test_request_boundaries(changes):
    with pytest.raises(ValidationError):ConfocalResponse.model_validate(request(**changes))


def test_circle_pixel_areas_tile_analytic_disk():
    for radius in [.01,.5,1.7,3]:
        area=sum(disk_pixel_area(x-.5,x+.5,y-.5,y+.5,radius) for x in range(-4,5) for y in range(-4,5))
        assert area==pytest.approx(math.pi*radius**2,abs=1e-12)
        assert disk_pixel_area(-radius,radius,-radius,radius,radius)==pytest.approx(math.pi*radius**2)


def test_finite_pixel_pinhole_and_unit_power_density():
    g=dict(nx=5,ny=7,min_x=-2,min_y=-3,dx=1,dy=1,values=[[2.]*5 for _ in range(7)])
    r=grid_metrics(g,[.1,2])
    assert r['raw_total_um2']==70 and r['axis_density_per_um2']==1/35
    for p in r['pinholes']:assert p['fraction']==pytest.approx(math.pi*(p['diameter_um']/2)**2/35)
    with pytest.raises(ZemaxError):grid_metrics(g,[8])
    g['values'][0][0]=None
    with pytest.raises(ZemaxError):grid_metrics(g,[])


def test_interpolated_fwhm_and_missing_brackets():
    x=[i/100 for i in range(-300,301)];y=[math.exp(-v*v) for v in x]
    r=half_width(x,y)
    assert r['state']=='bracketed' and r['fwhm_mm']==pytest.approx(2*math.sqrt(math.log(2)),abs=3e-5)
    assert half_width([0,1],[1,.8])['state']=='range_incomplete'
    assert half_width([0,1],[0,0])['state']=='zero_response'
