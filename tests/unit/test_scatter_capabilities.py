"""Scatter capabilities: reflection contract, placeholder handling and guards.

The first test re-reads the native reflection dump so the adapter cannot drift away
from the installed interface set. The remaining tests are pure offline behaviour.
"""
import json
from pathlib import Path

import pytest

from zemax_mcp.errors import ZemaxError
from zemax_mcp.scatter_capabilities import (
    ANALYSIS_SCATTER_TOGGLES,
    FLOATING_APERTURE,
    LDE_TYPES,
    RESOURCE_QUERY,
    SCATTER_FRACTION_ABSENT,
    SCATTER_FRACTION_HOSTS,
    TYPE_INTERFACE,
    catalog_diagnostics,
    is_placeholder,
    require_capability,
    require_resource,
    valid_names,
)

DUMP = Path(__file__).resolve().parents[2] / 'verification/development/BASE-01/probe/api-interfaces.json'


def dump_interfaces():
    if not DUMP.is_file():
        pytest.skip('native reflection dump not present in this checkout')
    return json.loads(DUMP.read_text(encoding='utf-8'))['interfaces']


def test_type_interface_and_resource_map_match_the_dump():
    interfaces = dump_interfaces()
    for kind, name in TYPE_INTERFACE.items():
        assert name in interfaces, (kind, name)
    for kind, method in RESOURCE_QUERY.items():
        methods = ' '.join(interfaces[TYPE_INTERFACE[kind]]['methods'])
        assert method in methods, (kind, method)


def test_scatter_fraction_hosts_match_the_dump():
    interfaces = dump_interfaces()
    with_fraction = set()
    for kind, name in TYPE_INTERFACE.items():
        props = {p['name'] for p in interfaces[name].get('properties', [])}
        if 'ScatterFraction' in props:
            with_fraction.add(kind)
    assert with_fraction == set(SCATTER_FRACTION_HOSTS)
    assert set(SCATTER_FRACTION_ABSENT) | set(SCATTER_FRACTION_HOSTS) == set(LDE_TYPES)


def test_floating_aperture_is_reflected_as_an_empty_interface():
    interfaces = dump_interfaces()
    entry = interfaces[FLOATING_APERTURE['interface']]
    assert len(entry.get('properties', [])) == FLOATING_APERTURE['property_count'] == 0
    assert len(entry.get('methods', [])) == FLOATING_APERTURE['method_count'] == 0
    assert FLOATING_APERTURE['hosts_scatter'] is False


def test_analysis_scatter_toggles_match_the_dump():
    interfaces = dump_interfaces()
    for name, toggle in ANALYSIS_SCATTER_TOGGLES.items():
        props = {p['name'] for p in interfaces[name].get('properties', [])}
        assert toggle in props, (name, toggle)


@pytest.mark.parametrize('value', ['', '无', ' none ', 'None'])
def test_placeholders_are_recognised(value):
    """Only values with native or documented evidence count as placeholders."""
    assert is_placeholder(value)


@pytest.mark.parametrize('value', ['BrownVinyl.bsdf', 'ABG-EXAMPLE', 'scatter.dll', 'n/a', 'null', '-'])
def test_real_names_are_not_placeholders(value):
    """'n/a', 'null' and '-' have no native evidence and must not be rejected."""
    assert not is_placeholder(value)


def test_placeholder_only_enumeration_is_unsupported():
    with pytest.raises(ZemaxError) as info:
        require_resource('BSDF', 'BrownVinyl.bsdf', ['无'])
    assert info.value.code == 'UNSUPPORTED_SETTING'
    assert info.value.details['placeholder_values'] == ['无']


def test_resource_matching_ignores_case_and_placeholders():
    assert require_resource('User', 'SCATTER.DLL', ['无', 'scatter.dll']) == 'scatter.dll'
    with pytest.raises(ZemaxError) as info:
        require_resource('ABg', 'missing', ['无', 'ABG-EXAMPLE'])
    assert info.value.code == 'INVALID_RESOURCE'
    assert info.value.details['available'] == ['ABG-EXAMPLE']


@pytest.mark.parametrize('kind', SCATTER_FRACTION_ABSENT)
def test_scatter_fraction_guard_rejects_types_without_the_property(kind):
    with pytest.raises(ZemaxError) as info:
        require_capability(kind, 'scatter_fraction')
    assert info.value.code == 'UNSUPPORTED_SETTING'
    assert info.value.details['settings_interface'] == TYPE_INTERFACE[kind]


@pytest.mark.parametrize('kind', SCATTER_FRACTION_HOSTS)
def test_scatter_fraction_guard_accepts_hosting_types(kind):
    assert require_capability(kind, 'scatter_fraction') is None


def test_unknown_type_is_rejected():
    with pytest.raises(ZemaxError) as info:
        require_capability('Reflective', 'type')
    assert info.value.code == 'INVALID_ARGUMENT'


def test_catalog_diagnostics_report_suffix_without_new_hard_rules():
    diagnostics = catalog_diagnostics('sample.isx', ['无', 'sample.isx'])
    assert diagnostics['matched'] is True and diagnostics['suffix_is_isx'] is True
    assert diagnostics['available'] == ['sample.isx']
    odd = catalog_diagnostics('sample.dat', ['sample.dat'])
    assert odd['matched'] is True and odd['suffix_is_isx'] is False


def test_valid_names_preserves_order():
    assert valid_names(['b.bsdf', '无', 'a.bsdf']) == ['b.bsdf', 'a.bsdf']


# --- real adapter paths -----------------------------------------------------
# These drive the actual resource_names / set_scattering code, not the capability table.

class _BsdfSettings:
    def __init__(self, names):
        self._names = names
        self.FileName = ''
        self.ScatterFraction = 0.0
        self.Angle = 0.0

    def GetAvailableFileNames(self):
        return list(self._names)


class _CatalogSettings:
    def __init__(self, files):
        self._files = list(files)
        self._file = ''
        self.Angle = 0.0
        self.SampleSide = 'Front'
        self.Sampling = 'FiveDegrees'

    def GetAvailableFiles(self):
        return list(self._files)

    def SetFile(self, value):
        if value in self._files:
            self._file = value
            return True
        return False

    def GetFile(self):
        return self._file


def _fake_native():
    from types import SimpleNamespace as NS
    return NS(enum=lambda *_: None,
              api=NS(Editors=NS(LDE=NS(SurfaceScatteringTypes=None))))


def _row(settings_object, suffix):
    from types import SimpleNamespace as NS
    events = dict(change=0)
    holder = NS(**{'_S_' + suffix: settings_object})

    def change(_holder):
        events['change'] += 1
        return True

    data = NS(CurrentType='BSDF' if suffix == 'BSDF' else 'ISScatterCatalog',
              CurrentTypeSettings=holder,
              CreateScatteringTypeSettings=lambda *_: holder,
              ChangeScatteringTypeSettings=change)
    return NS(ScatteringData=data), events


@pytest.fixture
def simple_native_setting(monkeypatch):
    import zemax_mcp.detectors as detectors
    monkeypatch.setattr(detectors, 'native_setting',
                        lambda _native, obj, name, value: setattr(obj, name, value))


def test_resource_names_rejects_placeholder_only_enumeration():
    from zemax_mcp.scattering_pages import resource_names
    with pytest.raises(ZemaxError) as info:
        resource_names(_BsdfSettings(['无']), 'BSDF')
    assert info.value.code == 'UNSUPPORTED_SETTING'
    assert info.value.details['placeholder_values'] == ['无']


def test_set_scattering_fails_before_any_write_on_placeholder(simple_native_setting):
    from zemax_mcp.scattering_pages import BSDF, set_scattering
    settings_object = _BsdfSettings(['无'])
    row, events = _row(settings_object, 'BSDF')
    with pytest.raises(ZemaxError) as info:
        set_scattering(_fake_native(), row, BSDF(type='BSDF', file_name='x.bsdf', scatter_fraction=0.2))
    assert info.value.code == 'UNSUPPORTED_SETTING'
    assert info.value.details['placeholder_values'] == ['无']
    assert settings_object.FileName == '' and events['change'] == 0  # nothing written


def test_set_scattering_rejects_unknown_resource_before_write(simple_native_setting):
    from zemax_mcp.scattering_pages import BSDF, set_scattering
    settings_object = _BsdfSettings(['brown.bsdf'])
    row, events = _row(settings_object, 'BSDF')
    with pytest.raises(ZemaxError) as info:
        set_scattering(_fake_native(), row, BSDF(type='BSDF', file_name='missing.bsdf', scatter_fraction=0.2))
    assert info.value.code == 'INVALID_RESOURCE'
    assert info.value.details['available'] == ['brown.bsdf']
    assert settings_object.FileName == '' and events['change'] == 0


def test_set_scattering_adopts_the_native_case_and_reads_back(simple_native_setting):
    from zemax_mcp.scattering_pages import BSDF, set_scattering
    settings_object = _BsdfSettings(['brown.bsdf'])
    row, events = _row(settings_object, 'BSDF')
    set_scattering(_fake_native(), row, BSDF(type='BSDF', file_name='BROWN.BSDF', scatter_fraction=0.2))
    assert settings_object.FileName == 'brown.bsdf'  # exact native name, not the request casing
    assert events['change'] == 1


def test_set_scattering_catalog_uses_the_exact_native_name(simple_native_setting):
    from zemax_mcp.scattering_pages import Catalog, set_scattering
    settings_object = _CatalogSettings(['sample.isx'])
    row, events = _row(settings_object, 'Catalog')
    set_scattering(_fake_native(), row, Catalog(type='ISScatterCatalog', file_name='SAMPLE.ISX'))
    # SetFile receives the exact native name, so GetFile readback cannot conflict on case.
    assert settings_object.GetFile() == 'sample.isx'
    assert events['change'] == 1


def test_set_scattering_rejects_unknown_catalog_file(simple_native_setting):
    from zemax_mcp.scattering_pages import Catalog, set_scattering
    settings_object = _CatalogSettings(['sample.isx'])
    row, events = _row(settings_object, 'Catalog')
    with pytest.raises(ZemaxError) as info:
        set_scattering(_fake_native(), row, Catalog(type='ISScatterCatalog', file_name='other.isx'))
    assert info.value.code == 'INVALID_RESOURCE'
    assert info.value.details['matched_name'] is None and events['change'] == 0
    assert settings_object.GetFile() == ''
