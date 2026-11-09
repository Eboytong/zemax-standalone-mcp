"""Public mode contracts reject alias writes before any NCE mutation."""
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.nsc_models import ObjectPatch
from zemax_mcp.source_spectrum import MODELS, read_settings, requested_values
from tests.support.detectors import backend


def patch(mode, **settings):
    return ObjectPatch(object=1, spectrum=dict(mode=mode, settings=settings)).spectrum


@pytest.mark.parametrize('mode', list(MODELS))
def test_modes_allow_partial_settings(mode):
    assert requested_values(patch(mode)) == {}


@pytest.mark.parametrize('mode,settings', [
    ('BlackBodySpectrum', dict(X=3000)),
    ('BlackBodySpectrum', dict(R=3000)),
    ('CIE1931Tristimulus', dict(TemperatureK=3000)),
    ('CIE1931RGB', dict(X=1)),
    ('SpectrumFile', dict(SpectrumCount=10)),
    ('SpectrumFile', dict(WavelengthFrom=.4)),
    ('SystemWavelengths', dict(WavelengthFrom=.4)),
    ('UniformPowerSpectrum', dict(Fit='override')),
    ('UnknownMode', {}),
])
def test_alias_and_readonly_settings_rejected(mode, settings):
    with pytest.raises(ValidationError):
        patch(mode, **settings)


@pytest.mark.parametrize('settings', [
    dict(TemperatureK=0), dict(TemperatureK=-1), dict(TemperatureK=True),
    dict(TemperatureK=float('nan')), dict(TemperatureK=float('inf')),
    dict(SpectrumCount=True), dict(SpectrumCount=2.5), dict(SpectrumCount=0),
    dict(WavelengthFrom=0), dict(WavelengthTo=-1),
    dict(WavelengthFrom=.7, WavelengthTo=.4), dict(WavelengthFrom=.5, WavelengthTo=.5),
])
def test_invalid_blackbody_values_rejected(settings):
    with pytest.raises(ValidationError):
        patch('BlackBodySpectrum', **settings)


def test_only_requested_values_are_written():
    assert requested_values(patch('BlackBodySpectrum', TemperatureK=3000)) == dict(TemperatureK=3000)


def test_readback_excludes_inactive_aliases():
    obj = NS(TemperatureK=3000., SpectrumCount=20, WavelengthFrom=.4, WavelengthTo=.7,
             Fit='native fit', X=3000., R=3000., u=3000.)
    sources = NS(SourceColor='BlackBodySpectrum', SourceColorSettings=NS(_S_BlackBodySpectrum=obj))
    result = read_settings(sources)
    assert result == dict(mode='BlackBodySpectrum', settings=dict(TemperatureK=3000., SpectrumCount=20,
                         WavelengthFrom=.4, WavelengthTo=.7, Fit='native fit'))


def test_file_readback_includes_native_resolved_sampling():
    obj = NS(SpectrumFile='controlled.spc', SpectrumCount=3, WavelengthFrom=.45,
             WavelengthTo=.65, Fit='file fit', TemperatureK=20)
    result = read_settings(NS(SourceColor='SpectrumFile', SourceColorSettings=NS(_S_SpectrumFile=obj)))
    assert result['settings'] == dict(SpectrumFile='controlled.spc', SpectrumCount=3,
                                      WavelengthFrom=.45, WavelengthTo=.65, Fit='file fit')


def test_native_read_failure_keeps_property_source():
    class Broken:
        SpectrumCount = 20
        WavelengthFrom = .4
        WavelengthTo = .7
        Fit = 'fit'

        @property
        def TemperatureK(self):
            raise RuntimeError('native temperature unavailable')

    result = read_settings(NS(SourceColor='BlackBodySpectrum',
                              SourceColorSettings=NS(_S_BlackBodySpectrum=Broken())))
    assert result['settings']['unavailable_fields'] == dict(TemperatureK='native temperature unavailable')


def test_public_alias_rejection_does_not_start_mutation(tmp_path):
    b = backend(tmp_path)
    mutations = []
    b._mutate = mutations.append
    response = b.dispatch('update_nsc_objects', dict(changes=[
        dict(object=1, spectrum=dict(mode='BlackBodySpectrum', settings=dict(X=3000)))]))
    assert response['ok'] is False
    assert response['error']['code'] == 'INVALID_ARGUMENT'
    assert response['error']['details']['partial_changes_possible'] is False
    assert mutations == []
