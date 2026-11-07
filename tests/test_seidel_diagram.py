import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import configure_seidel_diagram


@pytest.mark.parametrize('patch', [{'plot_scale': -1}, {'plot_scale': float('nan')},
                                   {'plot_scale': float('inf')}, {'wavelength': 1}])
def test_seidel_diagram_invalid_request(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': 'seidel_diagram', **patch})


def test_seidel_diagram_configuration_and_worker_roundtrip():
    req = RunAnalysis(request={'kind': 'seidel_diagram', 'ignore_chromatic': True,
                               'ignore_distortion': True, 'plot_scale': .25})
    assert RunAnalysis.model_validate(req.model_dump()) == req
    settings = {}
    configure_seidel_diagram(req.request, lambda k, v: settings.__setitem__(k, v))
    assert settings == dict(IgnoreChromatic=True, IgnoreDistortion=True,
                            SuppressFrame=False, PlotScale=.25)
