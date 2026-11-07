from zemax_mcp.config import PROJECT_ROOT
import math,json
from pathlib import Path
import pytest
from zemax_mcp.sag_fit import infer_removed_sphere,slope_sphere_curvature
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('curvature',[0,.025,-.025])
def test_identify_sphere_and_data_piston(curvature):
    points=[]
    for y in [0,1,2.5,5]:
        raw=.0126*y*y;sphere=.02+curvature*y*y/(1+math.sqrt(1-(curvature*y)**2))
        points.append((y,raw,raw-sphere))
    fit=infer_removed_sphere(points)
    assert fit['curvature']==pytest.approx(curvature,abs=1e-14)
    assert fit['data_piston']==pytest.approx(.02)
    if curvature:
        y=2.;s=curvature*y/math.sqrt(1-(curvature*y)**2)
        assert slope_sphere_curvature(y,.1,.1-s)==pytest.approx(curvature)

def test_inconsistent_native_sphere_is_rejected():
    with pytest.raises(ZemaxError):infer_removed_sphere([(0,0,0),(1,.1,0),(2,.5,0)])

def test_native_criterion_samples_reconstruct_reported_spheres():
    root=PROJECT_ROOT
    query=json.loads((root/'development/evidence/MF-01/probe423-criteria/probe.json').read_text(encoding='utf-8'))
    fits=[]
    for item in query['criterion_queries']:
        fit=infer_removed_sphere([(r['y'],r['sag'][1],r['SSAG'])for r in item['rows']]);fits.append(fit)
        assert fit['maximum_residual']<1e-10
    assert fits[1]['radius']==pytest.approx(39.8007821253,abs=1e-8)
    assert fits[2]['data_piston']==0
    # Reverse SSAG changes the sphere; the corresponding SSLP flag kept the old slope sphere.
    reverse=query['criterion_queries'][3]['rows'][1]
    slope_c=slope_sphere_curvature(reverse['y'],.0252*reverse['y'],reverse['SSLP'])
    assert abs(slope_c-fits[3]['curvature'])>1e-8


@pytest.mark.parametrize('allow_offset,criterion',[(False,1),(True,2)])
def test_independent_full_disk_rms_fit_matches_native_sphere(allow_offset,criterion):
    from tests.support.sag_rms_reference import fit_paraboloid
    root=PROJECT_ROOT
    native=json.loads((root/'development/evidence/MF-01/probe423-criteria/probe.json').read_text(encoding='utf-8'))
    samples=native['criterion_queries'][criterion]['rows']
    sphere=infer_removed_sphere([(r['y'],r['sag'][1],r['SSAG'])for r in samples])
    reference=fit_paraboloid(.0126,5.,allow_offset)
    assert abs(reference['radius']-sphere['radius'])<5e-6
    negative=fit_paraboloid(-.0126,5.,allow_offset)
    assert negative['radius']==pytest.approx(-reference['radius'],abs=5e-6)
    assert negative['offset']==pytest.approx(-reference['offset'],abs=1e-9)
    assert reference['offset']>0 if allow_offset else reference['offset']==0
