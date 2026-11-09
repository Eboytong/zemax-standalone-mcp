import math
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.material_index import uses_index,derivative_stencil

BASE=dict(kind='dispersion_vs_wavelength',catalog='SCHOTT',glasses=['N-BK7'],method='finite_difference')


def test_default_and_explicit_derivative_dispatch_and_roundtrip():
    default=RunAnalysis(request=dict(kind='dispersion_vs_wavelength'))
    assert not uses_index(RunAnalysis.model_validate(default.model_dump()).request)
    q=RunAnalysis(request=BASE)
    assert uses_index(q.request) and RunAnalysis.model_validate(q.model_dump())==q


@pytest.mark.parametrize('patch',[dict(glasses=[]),dict(glasses=['A','a']),dict(samples=1),dict(samples=2002),
    dict(minimum_wavelength_um=0),dict(temperature_c=30),dict(minimum_dispersion=.1,maximum_dispersion=-.1),
    dict(minimum_dispersion=float('inf')),dict(minimum_index=1.5),dict(method='index')])
def test_derivative_request_boundaries(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=BASE|patch)


@pytest.mark.parametrize('wave',[.4,.40005,.6,.79995,.8])
@pytest.mark.parametrize('power',range(5))
def test_fourth_order_stencil_matches_polynomial_derivatives(wave,power):
    nodes,weights=derivative_stencil(wave,.4,.8)
    assert min(nodes)>=.4 and max(nodes)<=.8 and len(nodes)==5
    actual=math.fsum(w*x**power for x,w in zip(nodes,weights))
    expected=power*wave**(power-1) if power else 0
    assert abs(actual-expected)<1e-8
