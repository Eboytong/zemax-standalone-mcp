import math
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.manufacturing_geometry import (
    ManufacturingGeometry, differential, paired_thickness, run_manufacturing_geometry,
    sample_points, sphere_sag, summarize)


@pytest.mark.parametrize('patch',[
    dict(aperture_radius=0),dict(samples=6),dict(samples=True),dict(samples=103),
    dict(back_surface=1),dict(limits=dict(min_edge_thickness=1)),
    dict(reference=dict(kind='specified_sphere')),dict(reference=dict(radius=20)),
    dict(derivative_step=1),dict(center_x=float('nan')),dict(limits=dict(max_slope_rad=2))])
def test_request_bounds(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='manufacturing_geometry',surface=1,aperture_radius=2)|patch)


def test_native_differential_sphere_and_biaxial_polynomial():
    d=differential(lambda x,y:sphere_sag(20,x,y),1.,2.,.002)
    assert d['sag']==pytest.approx(20-math.sqrt(395),abs=1e-14)
    assert d['slope_x']==pytest.approx(1/math.sqrt(395),abs=1e-9)
    assert d['slope_y']==pytest.approx(2/math.sqrt(395),abs=1e-9)
    assert d['principal_curvature_min']==pytest.approx(.05,abs=1e-7)
    assert d['principal_curvature_max']==pytest.approx(.05,abs=1e-7)
    d=differential(lambda x,y:.02*x*x+.03*y*y+.01*x*y,0.,0.,.001)
    assert d['principal_curvature_min']==pytest.approx(.05-math.sqrt(.0002),abs=1e-9)
    assert d['principal_curvature_max']==pytest.approx(.05+math.sqrt(.0002),abs=1e-9)


def test_decentered_back_surface_thickness_uses_same_physical_line():
    eye=[[1,0,0],[0,1,0],[0,0,1]]
    front=(eye,[0,0,0]);back=(eye,[.7,-.3,3.])
    d=paired_thickness(lambda x,y:.02*x*x+.03*y*y,1.,2.,.1,front,back)
    assert d==pytest.approx(3+.02*.3**2+.03*2.3**2-.1,abs=1e-10)


def fake_backend(sag=lambda x,y:.02*(x*x+y*y)):
    native=NS(GetSag=lambda _,x,y:(True,sag(x,y),0),
              GetGlobalMatrix=lambda _:(True,1,0,0,0,1,0,0,0,1,0,0,0))
    row=NS(Type='Standard',Radius=25,SemiDiameter=2)
    b=NS(_require_sequential=lambda:None,_row=lambda _:row,
         system=NS(LDE=native,SystemData=NS(Units=NS(LensUnits='Millimeters')),
                   MCE=NS(CurrentConfiguration=1)))
    b._cancel_boundary=lambda t:None
    def composite(kind,settings,factory):
        task=dict(task_id='test',rows=[])
        for _ in factory(task):pass
        return task
    b._composite=composite
    return b


def test_grid_masks_outside_disk_and_reports_thresholds():
    q=ManufacturingGeometry(kind='manufacturing_geometry',surface=1,aperture_radius=2,
        sampling='grid',samples=5,meridians=8,refine=True,
        limits=dict(max_abs_sag=.01,max_slope_rad=.2),
        reference=dict(kind='specified_sphere',radius=0))
    result=run_manufacturing_geometry(fake_backend(),q)
    assert result['summary']['samples_per_axis']==9
    assert result['payload']['grids'][0]['values'][0][0] is None
    assert result['payload']['thresholds'][0]['state']=='violated'
    assert result['payload']['thresholds'][1]['state']=='satisfied'
    assert result['summary']['metrics']['max_abs_sag']['value']==pytest.approx(.08)
    assert result['restoration']['required'] is False
    assert result['payload']['convergence']['absolute_change']['max_abs_sag']<1e-12


def test_cancellation_propagates_and_raw_native_error_preserved():
    q=ManufacturingGeometry(kind='manufacturing_geometry',surface=1,aperture_radius=2)
    b=fake_backend()
    def cancel(_):raise RuntimeError('cancelled by task')
    b._cancel_boundary=cancel
    with pytest.raises(RuntimeError,match='cancelled by task'):run_manufacturing_geometry(b,q)
    def fail(x,y):raise OSError('native detail')
    with pytest.raises(ZemaxError) as exc:run_manufacturing_geometry(fake_backend(fail),q)
    assert exc.value.details['native_message']=='native detail'


def test_invalid_domain_retains_location_and_prevents_threshold_pass():
    q=ManufacturingGeometry(kind='manufacturing_geometry',surface=1,aperture_radius=2,
        samples=5,meridians=4,refine=False,limits=dict(max_abs_departure=1),
        reference=dict(kind='specified_sphere',radius=1))
    result=run_manufacturing_geometry(fake_backend(),q)
    assert result['summary']['invalid_count']>0
    assert result['payload']['thresholds'][0]['state']=='unverified'
    assert any(r.get('reason')=='reference_sphere_domain' for r in result['rows'])


def test_grid_center_and_explicit_rim_are_included():
    q=ManufacturingGeometry(kind='manufacturing_geometry',surface=1,aperture_radius=2,
        center_x=.2,center_y=-.1,sampling='grid',samples=5)
    points=list(sample_points(q,5))
    assert any(r['radius']==0 for r in points)
    assert sum(r['edge'] for r in points)>=q.meridians
