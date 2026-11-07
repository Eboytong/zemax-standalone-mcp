import pytest
from types import SimpleNamespace
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.surface_slopes import SLOPE_ANALYSES, configure_surface_slope, describe_surface_slope
from zemax_mcp.analyses import AnalysesMixin
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('kind', SLOPE_ANALYSES)
def test_surface_slope_default_settings_and_roundtrip(kind):
    req = RunAnalysis(request={'kind': kind, 'surface': 1})
    assert RunAnalysis.model_validate(req.model_dump()) == req
    settings = {}
    configure_surface_slope(req.request, lambda k, v: settings.__setitem__(k, v))
    assert settings['Sampling'] == ('S_65' if kind.endswith('_cross') else 'S_65x65')
    assert ('Angle' in settings) == kind.endswith('_cross')
    assert ('ShowAs' in settings) != kind.endswith('_cross')
    if 'phase' in kind:
        assert settings['RemovePower'] is False
        assert 'RemoveOption' not in settings
    else:
        assert settings['RemoveOption'] == 'None'
        assert 'BestFitSphereOption' not in settings


@pytest.mark.parametrize('kind,patch', [
    ('surface_slope', {'angle': 3}),
    ('surface_slope_cross', {'sampling': 'S_65x65'}),
    ('surface_phase_slope', {'sampling': 'S_65'}),
    ('surface_phase_slope_cross', {'angle': float('inf')}),
    ('surface_slope', {'data_type': 'PhaseSlopeX'}),
    ('surface_phase_slope', {'data_type': 'XSlope'}),
    ('surface_slope', {'best_fit_sphere': 'MinimumRMS'}),
    ('surface_slope', {'reverse_direction': False}),
    ('surface_slope', {'remove_option': 'BestFitSphere', 'best_fit_sphere': 'MinimumRMS', 'reverse_direction': True}),
    ('surface_phase_slope', {'remove_option': 'BaseROC'}),
    ('surface_slope_cross', {'contour_format': '0.1'}),
    ('surface_slope', {'surface': 0}),
    ('surface_slope', {'data_type': 'SlopeUnused'}),
])
def test_slope_type_specific_parameters(kind, patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': kind, 'surface': 1, **patch})


def test_sphere_criterion_is_written_after_enabling_removal():
    q = RunAnalysis(request={'kind': 'surface_slope', 'surface': 1,
                             'remove_option': 'BestFitSphere', 'reverse_direction': True}).request
    writes = []
    configure_surface_slope(q, lambda k, v: writes.append((k, v)))
    names = [k for k, _ in writes]
    assert names.index('RemoveOption') < names.index('BestFitSphereOption') < names.index('ReverseDirection')
    assert ('BestFitSphereOption', 'MinimumVolume') in writes
    assert ('ReverseDirection', True) in writes


def test_slope_results_preserve_native_units_and_labels():
    series = dict(x_label='native X', labels=['native Y', 'native slope'], y=[[1, 2]])
    grid = dict(value_label='native slope', values=[[3]])
    data = dict(series=[series], grids=[grid])
    describe_surface_slope(data, dict(kind='surface_slope', surface=2, data_type='XSlope'), 'Millimeters')
    assert data['surface'] == 2
    assert grid['value_label'] == 'native slope'
    assert grid['x_unit'] == 'Millimeters'
    assert series['labels'] == ['native Y', 'native slope']
    assert series['value_units']==['Millimeters','dimensionless sag derivative']
    assert grid['array_order']=='values[y][x]'


@pytest.mark.parametrize('kind', ['surface_phase_slope','surface_phase_slope_cross'])
def test_phase_slope_units_and_cross_coordinates(kind):
    data=dict(grids=[dict(value_label='native label')],series=[dict(labels=['Y','Phase slope'])])
    describe_surface_slope(data,dict(kind=kind,surface=1,data_type='PhaseSlopeX'),'Millimeters')
    assert data['grids'][0]['value_unit']=='cycles per lens unit'
    assert data['grids'][0]['array_order']=='values[y][x]'
    assert data['grids'][0]['value_label']=='native label'
    assert data['series'][0]['value_units']==['Millimeters','cycles per lens unit']
    assert 'phase derivative / (2*pi)' in data['series'][0]['axis_definition']


@pytest.mark.parametrize('kind', SLOPE_ANALYSES)
@pytest.mark.parametrize('failure', ['surface', 'setting'])
def test_slope_preflight_and_setting_rejection_close(monkeypatch, kind, failure):
    import zemax_mcp.analyses as module
    import zemax_mcp.detectors as detectors
    events = []
    surface = SimpleNamespace(SetSurfaceNumber=lambda _: None, GetSurfaceNumber=lambda: 1)
    settings = SimpleNamespace(Surface=surface)
    tool = SimpleNamespace(GetSettings=lambda: settings)

    class Backend(AnalysesMixin):
        native = SimpleNamespace(api=SimpleNamespace(Analysis=SimpleNamespace(AnalysisIDM=None)),
                                 enum=lambda _, name: name)
        system = SimpleNamespace(Analyses=SimpleNamespace(New_Analysis=lambda _: events.append('open') or tool))
        def _require_sequential(self, focused):
            assert focused is False
        def _row(self, index):
            if failure == 'surface':
                raise ZemaxError('INDEX_OUT_OF_RANGE', 'surface outside model')
        def _release_owned(self, obj):
            assert obj is tool
            events.append('close')

    def reject(*args):
        raise ZemaxError('SETTING_REJECTED', 'native setting refused', setting=args[2])
    monkeypatch.setattr(module, 'unwrap', lambda obj: obj)
    monkeypatch.setattr(detectors, 'checked_setting', reject)
    with pytest.raises(ZemaxError) as exc:
        Backend().run_analysis(RunAnalysis(request={'kind': kind, 'surface': 1}))
    if failure == 'surface':
        assert exc.value.code == 'INDEX_OUT_OF_RANGE'
        assert events == []
    else:
        assert exc.value.code == 'SETTING_REJECTED'
        assert exc.value.details['setting'] == 'Sampling'
        assert events == ['open', 'close']
