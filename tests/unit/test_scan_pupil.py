import math

import pytest
from pydantic import ValidationError

from zemax_mcp.scan_pupil import ScanPupil,conjugates,footprint,global_ray,reflect


def query(**changes):
    return dict(kind='scan_pupil',start_surface=1,tilt_surface=2,mirror_surface=3,return_surface=4,pupil_surface=7,image_surface=8)|changes


@pytest.mark.parametrize('change',[
    dict(start_surface=2),dict(mirror_surface=4),dict(return_surface=5),dict(pupil_surface=4),dict(image_surface=6),
    dict(angles_deg=[1,1]),dict(angles_deg=[16]),dict(ray_density=4),dict(beam_radius=0),dict(probe_slope=1),
    dict(spacing=dict(surface=3,values=[1])),dict(spacing=dict(surface=4,values=[1,1])),
])
def test_contract(change):
    with pytest.raises(ValidationError):ScanPupil.model_validate(query(**change))


def test_reflection_and_physical_global_cosines():
    a=math.radians(3);normal=[math.sin(a),0,math.cos(a)]
    assert reflect([0,0,1],normal)==pytest.approx([-math.sin(2*a),0,-math.cos(2*a)])
    transform=[True,1,0,0,0,1,0,0,0,1,2,3,4]
    r=global_ray(transform,dict(position=[1,2,0],direction=[0,0,1]),-1)
    assert r==dict(position=[3,5,4],direction=[0,0,-1])


def row(state):
    x,y,u,v=state;n=1/math.sqrt(1+u*u+v*v)
    return dict(position=[x,y,0],direction=[u*n,v*n,n],error_code=0,vignette_code=0)


def test_non_degenerate_four_ray_states_recover_4f_matrix():
    states=[[0,0,0,0]]
    for axis in range(4):
        for sign in [1,-1]:
            s=[0,0,0,0];s[axis]=sign*1e-4;states.append(s)
    source=[row(s) for s in states]
    target=[row([-2*s[0]+.25*s[2],-2*s[1]+.25*s[3],-.5*s[2],-.5*s[3]]) for s in states]
    c=conjugates(source,target)
    for a in c['axes']:
        assert a['a']==pytest.approx(-2) and a['b']==pytest.approx(.25)
        assert a['signed_local_z_to_conjugate']==pytest.approx(.5)
        assert a['magnification']==pytest.approx(-2) and a['state']=='finite'
        assert a['signed_local_z_of_aperture_preimage']==pytest.approx(-.125)
        assert a['aperture_preimage_magnification']==pytest.approx(-.5)


def test_sampled_footprint_counts_clipped_and_failed_rays():
    r=footprint([row([1,0,0,0]),row([-1,0,0,0]),row([0,0,0,0])|dict(vignette_code=2),dict(error_code=3)])
    assert r['throughput']==.5 and r['center']==[0,0] and r['rms_radius']==1
    assert r['vignetted']==1 and r['errors']==1
