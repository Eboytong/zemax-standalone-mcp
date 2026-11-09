from types import SimpleNamespace as N

import pytest
from zemax_mcp.errors import ZemaxError
from zemax_mcp.phase_copy import uses_copy, check_header, check_optical_cells, freeze_geometry, PhaseCopyOwner, check_trace_witnesses
from zemax_mcp.polarization_topics import PhaseAberration


def test_default_and_explicit_methods():
    assert not uses_copy(PhaseAberration(kind='phase_aberration'))
    assert uses_copy(PhaseAberration(kind='phase_aberration', field=2))
    assert uses_copy(PhaseAberration(kind='phase_aberration', method='system_copy'))
    with pytest.raises(ZemaxError, match='直接选择'):
        uses_copy(PhaseAberration(kind='phase_aberration', method='native', wavelength=1))


def cell_snapshot(radius=20., material='N-BK7'):
    return [dict(surface=1, surface_type='Standard', cells=dict(
        radius=dict(value=radius, data_type='Double'),
        material=dict(value=material, data_type='String')))]


def test_geometry_rounding_and_material_identity():
    assert check_optical_cells(cell_snapshot(), cell_snapshot(20. + 1e-13))['passed']
    for actual in (cell_snapshot(20.01), cell_snapshot(material='F2'), []):
        with pytest.raises(ZemaxError) as caught:
            check_optical_cells(cell_snapshot(), actual)
        assert caught.value.code == 'SETTING_REJECTED'
    assert check_optical_cells(cell_snapshot(float('inf')), cell_snapshot(float('inf')))['passed']
    with pytest.raises(ZemaxError):
        check_optical_cells(cell_snapshot(float('inf')), cell_snapshot(float('-inf')))


def header():
    return dict(input_header=dict(field_position=dict(x=None, y=5.), wavelength_um=.4861,
        jones=dict(jx=1., jy=1., x_phase_deg=17., y_phase_deg=73.)))


@pytest.mark.parametrize('change,code', [
    ('x', 'SETTING_UNCONFIRMED'), ('y', 'SETTING_REJECTED'),
    ('wave', 'SETTING_REJECTED'), ('jones', 'SETTING_REJECTED')])
def test_report_identity_refusal(change, code):
    field, wave, pol = dict(x=0., y=5.), dict(wavelength_um=.4861327), dict(jx=1., jy=1., x_phase=17., y_phase=73.)
    if change in field:
        field[change] += 1
    elif change == 'wave':
        wave['wavelength_um'] = .6562725
    else:
        pol['jy'] = .5
    with pytest.raises(ZemaxError) as caught:
        check_header(header(), field, wave, pol)
    assert caught.value.code == code


def test_report_rounding_and_wrapped_phase():
    parsed = header()
    actual = check_header(parsed, dict(x=0., y=5.), dict(wavelength_um=.4861327),
                          dict(jx=1., jy=1., x_phase=377., y_phase=73.))
    assert actual is parsed['input_header']


class Cell:
    DataType = 'Double'
    IsReadOnly = False
    def __init__(self, solve, value, accepts=True):
        self.Solve, self.DoubleValue, self.accepts = solve, value, accepts
    def MakeSolveFixed(self):
        if self.accepts:
            self.Solve = 'Fixed'
        return self.accepts


def backend_for(cells):
    return N(_cells=lambda row: cells.items(), _cell_value=lambda c: c.DoubleValue), N(
        LDE=N(NumberOfSurfaces=1, GetSurfaceAt=lambda i: N()))


def test_freezes_dependency_solves_preserving_evaluated_values():
    cells = dict(radius=Cell('MarginalRayAngle', -18.37), thickness=Cell('Fixed', 20.))
    backend, system = backend_for(cells)
    result = freeze_geometry(backend, system)
    assert result == [dict(surface=0, cell='radius', previous_solve='MarginalRayAngle', value=-18.37, actual=-18.37)]
    assert cells['radius'].Solve == 'Fixed'


def test_freeze_rejection_preserves_failure_location():
    backend, system = backend_for(dict(radius=Cell('MarginalRayAngle', -18.37, accepts=False)))
    with pytest.raises(ZemaxError) as caught:
        freeze_geometry(backend, system)
    assert caught.value.details['cell'] == 'radius'
    assert caught.value.code == 'SETTING_REJECTED'


def test_owned_analysis_and_system_close_receipts_and_retry():
    calls = []
    receipt = {}
    owned = PhaseCopyOwner(N(Close=lambda save: calls.append(('system', save)) or True), receipt)
    owned.tool = N(Close=lambda: calls.append(('analysis',)) or False)
    assert owned.Close() is False
    assert receipt == dict(analysis_closed=False, system_closed=False)
    assert calls == [('analysis',)]
    owned.tool.Close = lambda: calls.append(('analysis',)) or True
    assert owned.Close() is True
    assert receipt == dict(analysis_closed=True, system_closed=True)
    assert owned.Close() is True and len(calls) == 3


@pytest.mark.parametrize('close_fails', [False, True])
def test_setup_failure_closes_copy_and_preserves_original(monkeypatch, close_fails):
    from zemax_mcp import phase_copy
    closed = []
    original = ZemaxError('SETTING_REJECTED', 'controlled freeze refusal', surface=6)
    monkeypatch.setattr(phase_copy, 'optical_cells', lambda backend, system: [])
    def freeze(backend, system):
        raise original
    monkeypatch.setattr(phase_copy, 'freeze_geometry', freeze)
    copy = N(SystemID=2, MCE=N(CurrentConfiguration=1), Close=lambda save: closed.append(save) or not close_fails)
    settings = dict(fields=[dict(number=1, x=0., y=0.)], configuration=1,
                    wavelengths=[dict(number=1, primary=True, wavelength_um=.55)],
                    polarization=dict(jx=0., jy=1., x_phase=0., y_phase=0.))
    def release(owned):
        if not owned.Close():
            raise ZemaxError('CLEANUP_FAILED', 'controlled close refusal')
    backend = N(_require_sequential=lambda: None, get_system_settings=lambda req: settings,
                system=N(SystemID=1, CopySystem=lambda: copy), _release_owned=release)
    with pytest.raises(ZemaxError) as caught:
        phase_copy.run_phase_copy(backend, PhaseAberration(kind='phase_aberration', field=1))
    assert caught.value is original and original.details['surface'] == 6
    assert closed == [False]
    assert ('cleanup_error' in original.details) == close_fails


def test_ray_mapping_requires_matching_geometry_and_error_states():
    source = [dict(ray=1, error=0, vignette=0, position_direction=[1., 2., 3., 0., 0., 1.])]
    assert check_trace_witnesses(source, source)['passed']
    for change in (dict(error=1), dict(vignette=2), dict(position_direction=[1.01, 2., 3., 0., 0., 1.])):
        with pytest.raises(ZemaxError) as caught:
            check_trace_witnesses(source, [dict(source[0], **change)])
        assert caught.value.code == 'SETTING_REJECTED'
    invalid = [dict(ray=1, error=2, vignette=0, position_direction=None)]
    with pytest.raises(ZemaxError):
        check_trace_witnesses(invalid, invalid)
