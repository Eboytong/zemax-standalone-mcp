"""Reject invalid general smoke requests before opening an optical instance."""
from pathlib import Path
import pytest
from zemax_mcp.analyses import ANALYSES
from zemax_mcp.analysis_models import RunAnalysis
from tests.support.analysis_scenarios import SPECIALIZED, cooke_request


@pytest.mark.parametrize('kind', sorted(set(ANALYSES) - set(SPECIALIZED)))
def test_cooke_scenario_is_a_valid_public_request(kind):
    assert RunAnalysis(request=cooke_request(kind)).request.kind == kind


def test_specialized_routes_have_existing_native_test_owners():
    assert set(SPECIALIZED) <= set(ANALYSES)
    for kind, (owner, condition) in SPECIALIZED.items():
        assert (Path(__file__).parents[1] / 'native' / owner).is_file(), (kind, owner)
        assert condition


def test_universal_smoke_axes_have_explicit_endpoints_and_independent_surfaces():
    one = cooke_request('universal_plot_1d')
    two = cooke_request('universal_plot_2d')
    assert one['start'] < one['stop']
    assert two['x']['surface'] != two['y']['surface']
    for axis in [two['x'], two['y']]:
        assert axis['start'] < axis['stop']
