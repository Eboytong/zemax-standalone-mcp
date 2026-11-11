import math

import pytest
from pydantic import ValidationError

from zemax_mcp.merit_program import MeritProgram, OpdTarget, gauss_nodes, pupil_nodes


@pytest.mark.parametrize('count',[2,3,8,32])
def test_gaussian_area_integrates_asymmetric_full_pupil(count):
    nodes=pupil_nodes(OpdTarget(kind='opd',rings=count,arms=32))
    assert sum(n['area_weight'] for n in nodes)==pytest.approx(1,abs=1e-13)
    assert sum(n['area_weight']*n['px'] for n in nodes)==pytest.approx(0,abs=1e-14)
    assert sum(n['area_weight']*n['px']**2 for n in nodes)==pytest.approx(.25,abs=1e-13)
    assert sum(n['area_weight']*(n['px']**2+n['py']**2)**2 for n in nodes)==pytest.approx(1/3,abs=1e-13)
    assert sum(n['area_weight']*n['px']*n['py'] for n in nodes)==pytest.approx(0,abs=1e-14)
    assert min(n['px'] for n in nodes)<0<max(n['px'] for n in nodes)
    assert min(n['py'] for n in nodes)<0<max(n['py'] for n in nodes)


def test_annular_area_and_non_symmetric_polynomial_rms():
    nodes=pupil_nodes(OpdTarget(kind='opd',obscuration=.5,rings=5,arms=24))
    assert sum(n['area_weight']*(n['px']**2+n['py']**2) for n in nodes)==pytest.approx(.625)
    values=[2+.3*n['px']+.5*n['py']+.2*(n['px']**2+n['py']**2) for n in nodes]
    mean=sum(n['area_weight']*v for n,v in zip(nodes,values))
    rms=math.sqrt(sum(n['area_weight']*(v-mean)**2 for n,v in zip(nodes,values)))
    expected=math.sqrt((.3**2+.5**2)*(1+.25)/4+.2**2*(1-.25)**2/12)
    assert rms==pytest.approx(expected,abs=1e-13)


@pytest.mark.parametrize('payload',[{},dict(targets=[dict(kind='opd',rings=1)]),
    dict(targets=[dict(kind='opd',scale_waves=0)]),dict(targets=[dict(kind='opd',hx=2)]),
    dict(targets=[dict(kind='opd',target_waves=float('nan'))]),
    dict(constraints=[dict(operand='CTGT',target=1)]),
    dict(constraints=[dict(operand='EFFL',surface=1,target=10)])])
def test_invalid_merit_contract(payload):
    with pytest.raises(ValidationError):MeritProgram.model_validate(payload)


def test_tool_schema_registration():
    from zemax_mcp.models import COMMAND_MODELS
    assert COMMAND_MODELS['run_merit_program'] is MeritProgram
    q=MeritProgram(targets=[dict(kind='opd')])
    assert not q.apply and q.targets[0].reference=='mean_remove_tilt'
