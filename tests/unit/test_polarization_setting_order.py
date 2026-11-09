"""System Jones updates must not cross an invalid zero-amplitude state."""
from types import SimpleNamespace

import pytest

from zemax_mcp.errors import ZemaxError
from zemax_mcp.modeling import ModelingMixin
from zemax_mcp.models import SystemPatch


@pytest.mark.parametrize('initial,requested', [
    ((1., 0.), (0., 1.)), ((0., 1.), (1., 0.)),
    ((1., 0.), (.6, .8)), ((0., 1.), (.6, .8)),
])
@pytest.mark.parametrize('unpolarized', [False, True])
def test_jones_switch_enables_nonzero_component_before_clearing_other(monkeypatch, initial, requested, unpolarized):
    class Jones:
        def __init__(self):
            object.__setattr__(self, 'Jx', initial[0])
            object.__setattr__(self, 'Jy', initial[1])
            object.__setattr__(self, 'Unpolarized', unpolarized)
            self.writes = []

        def __setattr__(self, name, value):
            if name in {'Jx', 'Jy'}:
                assert not self.Unpolarized, 'native Jones setters are inactive in unpolarized mode'
                other = self.Jy if name == 'Jx' else self.Jx
                if value == other == 0:
                    raise AssertionError('native rejected a zero Jones vector')
                self.writes.append((name, value))
            object.__setattr__(self, name, value)

    monkeypatch.setattr('zemax_mcp.modeling.apply_pages', lambda *a, **kw: None)
    monkeypatch.setattr('zemax_mcp.detectors.native_setting', lambda native, obj, name, value: setattr(obj, name, value))
    pol = Jones()
    backend = ModelingMixin()
    backend.native = None
    backend.system = SimpleNamespace(SystemData=SimpleNamespace(Polarization=pol, RayAiming=None))
    backend._apply_settings_extension(SystemPatch(polarization=dict(jx=requested[0], jy=requested[1])))
    assert (pol.Jx, pol.Jy) == requested
    assert pol.Unpolarized == unpolarized


def test_final_jones_combination_is_read_back_after_native_cross_update(monkeypatch):
    class Jones:
        Jx = 0.
        Jy = 1.
        Unpolarized = False

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)
            if name == 'Jy':
                object.__setattr__(self, 'Jx', .5)

    monkeypatch.setattr('zemax_mcp.modeling.apply_pages', lambda *a, **kw: None)
    monkeypatch.setattr('zemax_mcp.detectors.native_setting', lambda native, obj, name, value: setattr(obj, name, value))
    backend = ModelingMixin()
    backend.native = None
    backend.system = SimpleNamespace(SystemData=SimpleNamespace(Polarization=Jones(), RayAiming=None))
    with pytest.raises(ZemaxError) as error:
        backend._apply_settings_extension(SystemPatch(polarization=dict(jx=1., jy=0.)))
    assert error.value.code == 'SETTING_REJECTED'
