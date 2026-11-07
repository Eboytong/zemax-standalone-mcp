from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import AnalysesMixin, configure_rms_wavelength, map_rms_wavelength_series
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('patch', [
    {'rings': 3}, {'method': 'GaussQuad', 'sampling': 'S_64x64'},
    {'method': 'GaussQuad', 'rings': 21}, {'wavelength_density': 21},
    {'wavelength_density': 105}, {'plot_scale': float('inf')},
    {'plot_scale': -1}, {'wavelength': 0}, {'field': -1},
])
def test_invalid_rms_wavelength_request(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': 'rms_vs_wavelength', **patch})


@pytest.mark.parametrize('method,extra,density', [
    ('RectArray', {}, 'RayDens_64x64'),
    ('RectArray', {'sampling': 'S_256x256'}, 'RayDens_256x256'),
    ('GaussQuad', {}, 'RayDens_3'),
    ('GaussQuad', {'rings': 20}, 'RayDens_20'),
])
def test_settings_sampling_and_enum_alias(method, extra, density):
    req = RunAnalysis(request={'kind': 'rms_vs_wavelength', 'method': method,
                               'data_type': 'StrehlRatio', 'wavelength_density': 100, **extra})
    assert RunAnalysis.model_validate(req.model_dump()) == req
    settings = {}
    configure_rms_wavelength(req.request, lambda k, v: settings.__setitem__(k, v))
    assert settings == dict(Method=method, RayDensity=density, WaveDensity='WaveDens_100',
                            Data='StrehlRation', ReferTo='Centroid', UseDashes=False,
                            ShowDiffractionLimit=False, UsePolarization=False, PlotScale=0)


@pytest.mark.parametrize('metric,unit', [('Wavefront', 'waves'), ('StrehlRatio', 'dimensionless'),
                                        ('SpotRadius', 'micrometers'), ('Spot_X', 'micrometers'),
                                        ('Spot_Y', 'micrometers')])
def test_series_preserves_native_labels_and_wavelength_axis(metric, unit):
    data = {'series': [dict(x=[.4, .7], y=[[1, 2], [3, 4]], labels=['Field 1', 'Field 2'])]}
    map_rms_wavelength_series(data, {'data_type': metric, 'field': 0})
    series = data['series'][0]
    assert series['x_unit'] == 'micrometers'
    assert series['value_units'] == [unit, unit]
    assert series['native_labels'] == ['Field 1', 'Field 2']
    assert series['actual_point_count'] == 2
    assert series['y'] == [[1, 2], [3, 4]]


def test_missing_series_retains_specific_error():
    with pytest.raises(ZemaxError) as exc:
        map_rms_wavelength_series({'series': []}, {'data_type': 'Wavefront', 'field': 1})
    assert exc.value.code == 'NO_RESULT_DATA'


@pytest.mark.parametrize('rejected', [None, 'RayDensity', 'WaveDensity', 'Data','final:RayDensity'])
def test_native_setup_uses_settings_first_and_releases_on_rejection(monkeypatch, rejected):
    import zemax_mcp.analyses as module
    import zemax_mcp.detectors as detectors

    selector = SimpleNamespace(SetFieldNumber=lambda n: None, GetFieldNumber=lambda: 1)
    settings = SimpleNamespace(Field=selector)
    tool = SimpleNamespace(GetSettings=lambda: settings)
    calls = []

    def factory(native_id):
        calls.append(('factory', native_id))
        return tool

    def put(native, obj, name, value):
        calls.append((name, value))
        if name == rejected:
            raise ZemaxError('SETTING_REJECTED', 'native value rejected', setting=name)

    class Backend(AnalysesMixin):
        native = SimpleNamespace(api=SimpleNamespace(Analysis=SimpleNamespace(AnalysisIDM=object())),
                                 enum=lambda _, name: name)
        system = SimpleNamespace(
            SystemData=SimpleNamespace(Fields=SimpleNamespace(NumberOfFields=2)),
            Analyses=SimpleNamespace(New_Analysis_SettingsFirst=factory,
                                     New_Analysis=lambda _: pytest.fail('wrong factory')))

        def _require_sequential(self, **kwargs): pass
        def _release_owned(self, obj):
            assert obj is tool
            calls.append(('close', True))
        def _start_task(self, *args, **kwargs):
            calls.append(('start', True))
            return {'state': 'running'}

    monkeypatch.setattr(module, 'unwrap', lambda obj: obj)
    monkeypatch.setattr(module, 'scalar_settings', lambda obj: {})
    monkeypatch.setattr(detectors, 'checked_setting', put)
    import zemax_mcp.imaging as imaging
    def final_check(native,obj,name,value):
        calls.append(('final_readback',name))
        if rejected=='final:'+name:
            raise ZemaxError('SETTING_REJECTED','final combination changed',setting=name)
    monkeypatch.setattr(imaging,'check',final_check)
    q = RunAnalysis(request={'kind': 'rms_vs_wavelength', 'field': 1}).request
    backend = Backend()
    if rejected:
        with pytest.raises(ZemaxError) as exc:
            backend.run_analysis(SimpleNamespace(request=q))
        assert exc.value.details['setting'] == rejected.removeprefix('final:')
        assert calls[-1] == ('close', True)
        assert ('start', True) not in calls
    else:
        assert backend.run_analysis(SimpleNamespace(request=q)) == {'state': 'running'}
        assert calls[-1] == ('start', True)
        assert len([c for c in calls if c[0]=='final_readback'])==9
    assert calls[0] == ('factory', 'RMSLambdaDiagram')
