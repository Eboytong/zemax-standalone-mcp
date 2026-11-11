import math

import pytest

from zemax_mcp.errors import ZemaxError
from zemax_mcp.glass_reference import glass_contributions,paraxial


def test_thin_lens_focus_petzval_and_color_derivative():
    rows=[dict(curvature=.02,thickness=0),dict(curvature=-.02,thickness=50)]
    indices=[[1,1.52,1],[1,1.515,1],[1,1.51,1]]
    result=glass_contributions(rows,indices,[dict(first_surface=1,last_surface=2)],1,2)
    phi=(1.515-1)*.04
    assert result['reference']['effective_focal_length']==pytest.approx(1/phi,rel=1e-12)
    assert result['reference']['petzval_curvature']==pytest.approx(-phi/1.515,rel=1e-12)
    assert result['groups'][0]['axial_color']==pytest.approx(.04/(phi*phi)*.01,rel=1e-12)
    assert result['groups'][0]['lateral_color']==0
    assert result['exact_paraxial_axial_color']==pytest.approx(1/(.51*.04)-1/(.52*.04),rel=1e-12)


def test_cemented_groups_keep_independent_dispersion_sensitivities():
    rows=[dict(curvature=.02,thickness=3),dict(curvature=-.025,thickness=2),dict(curvature=-1/150,thickness=90)]
    n=[1,1.5168,1.62005,1]
    values=[[1,n[1]+.004,n[2]+.008,1],n,[1,n[1]-.004,n[2]-.008,1]]
    groups=[dict(first_surface=1,last_surface=2),dict(first_surface=2,last_surface=3)]
    result=glass_contributions(rows,values,groups,1,2)
    assert sum(c['petzval_curvature'] for c in result['groups'])==pytest.approx(result['reference']['petzval_curvature'],rel=1e-12)
    for group,row in zip(groups,result['groups']):
        first,last=group['first_surface'],group['last_surface'];epsilon=1e-6
        lo=n[:];hi=n[:]
        for i in range(first,last):lo[i]-=epsilon;hi[i]+=epsilon
        a,c=paraxial(rows,hi,1,2),paraxial(rows,lo,1,2)
        for metric,key in [('back_focal_distance','axial_sensitivity'),('chief_image_height','lateral_sensitivity')]:
            assert row[key]==pytest.approx((a[metric]-c[metric])/(2*epsilon),rel=1e-6,abs=1e-8)
        assert math.isfinite(row['petzval_curvature'])


def test_singular_and_nonuniform_group():
    with pytest.raises(ZemaxError):paraxial([dict(curvature=0,thickness=1)],[1,1],1,0)
    rows=[dict(curvature=.02,thickness=3),dict(curvature=-.025,thickness=2),dict(curvature=-1/150,thickness=90)]
    with pytest.raises(ZemaxError):glass_contributions(rows,[[1,1.5,1.6,1]]*3,[dict(first_surface=1,last_surface=3)],1,0)
