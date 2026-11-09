"""Offline Gradium references: GRD/SGRIN parsing, retained residuals, capping rules, metadata states.

No native instance is created here. The retained probe records under
``development/evidence/MA-01`` are read-only inputs; the numeric gates are the
original ones (1e-10 absolute + 1e-9 relative, direction 1e-10).
"""
import json
import math
from pathlib import Path

import pytest

from tests.support.gradium_reference import (
    CURVE_ATOL,
    CURVE_RTOL,
    LOW_ORDER_MAX_RESIDUAL,
    PROBE_RECORDS,
    boundary_hypotheses,
    documented_allowed,
    exact_reference_index,
    exceeds_ends,
    hypothesis_verdicts,
    load_probe_record,
    parse_grd_block,
    parse_grd_blocks,
    parse_sgrin_family,
    probe_conditions,
    reference_index,
    residual_report,
    surface_sag,
)

GRD_SAMPLE = """G14SFN GSF 5.800 4.54 8.25 G5SF
 1.8049459E+000
-6.0008069E-002
-3.0642578E-001
 1.6322532E+000
-7.5292950E+000
 1.9036599E+001
-2.5950589E+001
 1.1587446E+001
 1.1868801E+001
-1.3043293E+001
 9.8394732E-001
 1.6244809E+000
"""

SGRIN_SAMPLE = """GSF
0.38 2.2
0.58756
6 3
-0.0683636 -0.0323639 -0.0286748 -0.0169163 0.00256909 0.0174719
-0.00109783 0.0334663 0.0388098 0.0370413 0.017429 -0.0405421
0.931075 -0.0306245 -0.0392756 -0.0423487 -0.0256629 0.0437821
0.00498103 0.000410271 2.44E-05
0.082168 0.0343531 -0.0337717
110 0.000285988 0.000362547
"""


def test_grd_block_reports_declared_fields():
    block = parse_grd_block(GRD_SAMPLE, 'G14SFN')
    assert block['family'] == 'GSF'
    assert block['maximum_z'] == 5.8
    assert len(block['coefficients']) == 12
    assert block['coefficients'][0] == 1.8049459
    assert block['extra_tokens'] == ['4.54', '8.25', 'G5SF']


@pytest.mark.parametrize('text', [
    'G14SFN GSF 5.800\n1.0\n2.0\n',
    'G14SFN GSF -1.0\n' + '\n'.join(['1.0'] * 12) + '\n',
    'G14SFN GSF 5.8\n' + '\n'.join(['1.0'] * 11) + '\n',
])
def test_grd_block_rejects_unsupported_input(text):
    with pytest.raises(ValueError):
        parse_grd_blocks(text)


def test_grd_block_duplicate_name_rejected():
    with pytest.raises(ValueError):
        parse_grd_blocks(GRD_SAMPLE + GRD_SAMPLE)


def test_sgrin_family_reports_reference_wavelength():
    family = parse_sgrin_family(SGRIN_SAMPLE, 'GSF')
    assert family['reference_wavelength_um'] == 0.58756
    assert (family['minimum_wavelength_um'], family['maximum_wavelength_um']) == (0.38, 2.2)
    assert (family['index_terms'], family['dispersion_terms']) == (6, 3)


def test_reference_index_matches_hand_calculation():
    # Three-term hand check at z=0, offset=0.5, maximum_z=1: 1.5 + 0.1*0.5 - 0.02*0.25.
    assert reference_index([1.5, 0.1, -0.02] + [0.0] * 9, 1.0, 0.5, 0.0) == pytest.approx(1.545, rel=0, abs=1e-15)
    block = parse_grd_block(GRD_SAMPLE, 'G14SFN')
    # Only the first two declared terms of the stock block, hand evaluated.
    first_two = block['coefficients'][:2] + [0.0] * 10
    assert reference_index(first_two, block['maximum_z'], 1.0, 0.0) == pytest.approx(
        1.8049459 - 0.060008069 / 5.8, rel=0, abs=1e-15)
    # Documented offset convention: n(z, offset) == n(z + offset, 0) at equal maximum z.
    full = block['coefficients']
    assert reference_index(full, block['maximum_z'], 1.0, 0.0) == pytest.approx(
        reference_index(full, block['maximum_z'], 0.0, 1.0), rel=0, abs=1e-15)
    # A monomial is computable by hand: n = 1.5 + 1.0*(0.5)**10.
    assert exact_reference_index([1.5] + [0.0] * 9 + [1.0, 0.0], 1.0, 0.5, 0.0) == pytest.approx(1.5009765625)
    assert reference_index([1.5] + [0.0] * 9 + [1.0, 0.0], 1.0, 0.5, 0.0) == 1.5009765625


def test_documented_capping_rules():
    assert exceeds_ends(-0.1, 5.8) == ('left',)
    assert exceeds_ends(5.9, 5.8) == ('right',)
    assert exceeds_ends(1.0, 5.8) == ()
    # Left end is bounded for capping 0 and 1 only; right end for 0 and 2.
    assert [documented_allowed(-0.1, 5.8, capping) for capping in range(4)] == [False, False, True, True]
    assert [documented_allowed(5.9, 5.8, capping) for capping in range(4)] == [False, True, False, True]
    assert [documented_allowed(1.0, 5.8, capping) for capping in range(4)] == [True] * 4


def test_boundary_hypotheses_are_distinguishable():
    hypotheses = boundary_hypotheses()
    assert set(hypotheses) == {'documented', 'negative_offset_rejected', 'labels_swapped'}
    documented = [hypotheses['documented']['allowed'](-0.1, 5.8, capping, -0.2) for capping in range(4)]
    negative = [hypotheses['negative_offset_rejected']['allowed'](-0.1, 5.8, capping, -0.2) for capping in range(4)]
    swapped = [hypotheses['labels_swapped']['allowed'](-0.1, 5.8, capping, -0.2) for capping in range(4)]
    assert documented == [False, False, True, True]
    assert negative == [False] * 4
    assert swapped == [False, True, False, True]
    # Recorded 629 matrix, evaluated at the extreme profile coordinate of the span
    # [offset, offset + thickness]: positive extension 5.6 -> 6.0 is refused by capping
    # 0/2 and accepted by 1/3, which the documented rule reproduces.
    assert [hypotheses['documented']['allowed'](6.0, 5.8, capping) for capping in range(4)] == [False, True, False, True]
    # The four recorded negative-offset disagreements (offset -0.2, capping 2 and 3
    # expected to pass) match the negative-offset hypothesis, not the documented rule.
    observed_629 = [False, False, False, False]
    assert [hypotheses['documented']['allowed'](-0.2, 5.8, capping, -0.2) for capping in range(4)] == [False, False, True, True]
    assert [hypotheses['negative_offset_rejected']['allowed'](-0.2, 5.8, capping, -0.2) for capping in range(4)] == observed_629


def test_surface_sag_sign_and_value():
    assert surface_sag(0.0, -40.0) == 0.0
    assert surface_sag(3.0, -40.0) == pytest.approx(-3.0 ** 2 / (40 * (1 + math.sqrt(1 - (3 / 40) ** 2))))
    assert surface_sag(3.0, 40.0) == pytest.approx(-surface_sag(3.0, -40.0))
    with pytest.raises(ValueError):
        surface_sag(50.0, -40.0)


def test_retained_low_order_residuals_are_floating_point():
    records = {name: load_probe_record(name) for name in PROBE_RECORDS}
    table = residual_report(records)
    low = [row for row in table if row['degree'] <= 9]
    assert low and max(row['maximum_absolute_residual'] for row in low) <= LOW_ORDER_MAX_RESIDUAL


@pytest.mark.parametrize('degree,recorded', [(10, 5.103585e-09), (11, 6.123846e-10)])
def test_retained_high_order_residual_is_reproduced(degree, recorded):
    rows = probe_conditions(load_probe_record('probe638-unit-monomials'), 'probe638-unit-monomials')['rows']
    worst = max((row for row in rows if row['degree'] == degree), key=lambda row: abs(row['residual']))
    assert abs(worst['residual']) == pytest.approx(recorded, rel=1e-6)
    assert worst['normalized_coordinate'] == pytest.approx(0.1)
    # Documented value at the exact dyadic coordinate 0.5 of the same record.
    halves = [row for row in rows if row['degree'] == degree and row['normalized_coordinate'] == 0.5]
    assert halves[0]['native'] == (1.5009765660172871 if degree == 10 else 1.5004882811778535)


def test_e1_verdicts_keep_hypotheses_separate():
    records = {name: load_probe_record(name) for name in PROBE_RECORDS}
    verdicts = hypothesis_verdicts(records)
    assert verdicts['low_order_matches_exact_polynomial'] is True
    assert verdicts['h_b_text_or_coefficient_order_refuted'] is True
    assert verdicts['zmax_invariance']['compared_points'] == 60
    assert verdicts['zmax_invariance']['bit_identical'] is True
    scaling = verdicts['amplitude_scaling']
    assert 0.09 < scaling['ratio_min'] < 0.11 and 0.09 < scaling['ratio_max'] < 0.11
    assert scaling['maximum_absolute_extra_residual'] < 1e-13


def test_curve_gate_is_unchanged():
    assert (CURVE_ATOL, CURVE_RTOL) == (1e-10, 1e-9)


def test_e1_artifact_matches_support(tmp_path):
    """The saved E1 artifact must agree with a fresh replay (artifacts are not gates)."""
    path = Path(__file__).resolve().parents[2] / '.local/gradium/e1-residuals.json'
    if not path.is_file():
        pytest.skip('E1 artifact not generated in this workspace')
    artifact = json.loads(path.read_text(encoding='utf-8'))
    records = {name: load_probe_record(name) for name in PROBE_RECORDS}
    fresh = residual_report(records)
    assert len(artifact['residual_table']) == len(fresh)
    for saved, current in zip(artifact['residual_table'], fresh, strict=True):
        assert saved['record'] == current['record'] and saved['degree'] == current['degree']
        assert saved['maximum_absolute_residual'] == pytest.approx(current['maximum_absolute_residual'], rel=1e-12)


# --- shared metadata patch: declared states, never breaks the curve ---------

def glasscat_tree(tmp_path, grd=GRD_SAMPLE, sgrin=SGRIN_SAMPLE):
    from types import SimpleNamespace
    directory = tmp_path / 'Glasscat'
    directory.mkdir(exist_ok=True)
    if grd is not None:
        (directory / 'PROFILE.GRD').write_text(grd, encoding='utf-8')
    if sgrin is not None:
        (directory / 'SGRIN.DAT').write_text(sgrin, encoding='utf-8')
    return SimpleNamespace(ZemaxDataDir=str(tmp_path))


def custom_grd():
    """A task-owned monomial block with a maximum z that the stock file cannot produce."""
    values = ['0'] * 12
    values[0] = '1.5'
    values[10] = '1'
    return 'MCPE3R1 GSF 2.500\n' + '\n'.join(values) + '\n'


def test_resource_metadata_reports_declared_profile(tmp_path):
    from zemax_mcp.gradium import resource_metadata
    result = resource_metadata(glasscat_tree(tmp_path), 'PROFILE.GRD', 'G14SFN')
    assert result['status'] == 'declared'
    assert result['profile']['maximum_z'] == 5.8
    assert result['profile']['coefficient_count'] == 12
    assert result['profile']['family'] == 'GSF'
    assert result['family']['reference_wavelength_um'] == 0.58756
    assert result['family']['wavelength_range_um'] == [0.38, 2.2]
    assert result['family']['declaration'] == 'candidate'
    assert result['family']['native_binding'] == 'unconfirmed'
    assert result['path_origin'] == 'relative'
    assert 'no profile evaluation' in result['scope']


def test_resource_metadata_accepts_absolute_profile_file(tmp_path):
    from zemax_mcp.gradium import resource_metadata
    application = glasscat_tree(tmp_path)
    folder = tmp_path / 'elsewhere'
    folder.mkdir()
    target = folder / 'MCP_GRADIUM_E3_abs.GRD'
    target.write_text(custom_grd(), encoding='utf-8')
    # A sibling SGRIN.DAT with a different reference wavelength must not be adopted as
    # the native family file: only the Glasscat resource root is documented.
    (folder / 'SGRIN.DAT').write_text(SGRIN_SAMPLE.replace('0.58756', '0.60000'), encoding='utf-8')
    result = resource_metadata(application, str(target), 'MCPE3R1')
    assert result['status'] == 'declared'
    assert result['profile']['maximum_z'] == 2.5
    assert result['profile']['source'] == str(target)
    assert result['path_origin'] == 'absolute'
    assert result['native_resource_root'] == str(tmp_path / 'Glasscat')
    assert result['family']['source'] == str(tmp_path / 'Glasscat' / 'SGRIN.DAT')
    assert result['family']['reference_wavelength_um'] == 0.58756
    assert result['family']['declaration'] == 'candidate'
    assert result['family']['native_binding'] == 'unconfirmed'
    assert 'outside the native resource root' in result['path_note']


def test_resource_metadata_preserves_relative_subdirectory(tmp_path):
    """A relative profile file keeps its own relative identity under Glasscat."""
    from zemax_mcp.gradium import resource_metadata
    application = glasscat_tree(tmp_path)
    sub = tmp_path / 'Glasscat' / 'custom'
    sub.mkdir()
    (sub / 'MCP_GRADIUM_E3_sub.GRD').write_text(custom_grd(), encoding='utf-8')
    result = resource_metadata(application, 'custom/MCP_GRADIUM_E3_sub.GRD', 'MCPE3R1')
    assert result['status'] == 'declared'
    assert result['path_origin'] == 'relative'
    assert result['profile']['source'] == str(sub / 'MCP_GRADIUM_E3_sub.GRD')
    assert result['profile']['maximum_z'] == 2.5
    # The bare file name is not a valid substitute for the real relative identity.
    assert resource_metadata(application, 'MCP_GRADIUM_E3_sub.GRD', 'MCPE3R1')['status'] == 'unavailable'


def test_family_metadata_comes_from_the_resource_root(tmp_path):
    from zemax_mcp.gradium import family_metadata
    root = tmp_path / 'Glasscat'
    root.mkdir()
    (root / 'SGRIN.DAT').write_text(SGRIN_SAMPLE, encoding='utf-8')
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'SGRIN.DAT').write_text(SGRIN_SAMPLE.replace('0.58756', '0.60000'), encoding='utf-8')
    declared = family_metadata('GSF', root)
    assert declared['status'] == 'declared'
    assert declared['reference_wavelength_um'] == 0.58756
    assert declared['source'] == str(root / 'SGRIN.DAT')
    assert declared['declaration'] == 'candidate' and declared['native_binding'] == 'unconfirmed'
    assert 'no native readback' in declared['binding_basis']
    unknown = family_metadata('GZZ', root)
    assert unknown['status'] == 'unavailable' and 'not declared' in unknown['reason']
    assert family_metadata('GSF', None)['status'] == 'unavailable'
    assert family_metadata(None, root)['status'] == 'unavailable'
    # Only an explicitly supplied root is read; nothing is adopted from other folders.
    assert family_metadata('GSF', other)['reference_wavelength_um'] == 0.6


def test_resource_metadata_uses_the_selected_profile_file(tmp_path):
    """A task-owned GRD must be read by name, never attributed to the stock PROFILE.GRD."""
    from zemax_mcp.gradium import resource_metadata
    application = glasscat_tree(tmp_path)
    selected = tmp_path / 'Glasscat' / 'MCP_GRADIUM_E3_test.GRD'
    selected.write_text(custom_grd(), encoding='utf-8')
    result = resource_metadata(application, selected.name, 'MCPE3R1')
    assert result['status'] == 'declared'
    assert result['profile']['maximum_z'] == 2.5
    assert Path(result['profile']['source']).name == selected.name
    assert result['profile']['coefficients'][10] == 1.0
    # The stock block is not consulted when another file is selected.
    stock = resource_metadata(application, selected.name, 'G14SFN')
    assert stock['status'] == 'unavailable'
    assert stock['profile']['available'] == ['MCPE3R1']


@pytest.mark.parametrize('mutation', ['nan_coefficient', 'inf_coefficient', 'nan_maximum_z', 'nan_family_wavelength'])
def test_resource_metadata_rejects_non_finite_values(tmp_path, mutation):
    from zemax_mcp.gradium import resource_metadata
    grd, sgrin = custom_grd(), SGRIN_SAMPLE
    if mutation == 'nan_coefficient':
        grd = grd.replace('\n1\n', '\nnan\n', 1)
    elif mutation == 'inf_coefficient':
        grd = grd.replace('\n1\n', '\ninf\n', 1)
    elif mutation == 'nan_maximum_z':
        grd = grd.replace('2.500', 'nan', 1)
    else:
        sgrin = sgrin.replace('0.38 2.2', 'nan 2.2', 1)
    application = glasscat_tree(tmp_path, grd=grd, sgrin=sgrin)
    result = resource_metadata(application, 'PROFILE.GRD', 'MCPE3R1')
    expected = 'declared' if mutation == 'nan_family_wavelength' else 'unsupported'
    assert result['status'] == expected
    if mutation == 'nan_family_wavelength':
        assert result['family']['status'] == 'unsupported'
        assert 'non-finite' in result['family']['reason']
    else:
        assert 'non-finite' in result['reason']
    # No NaN/Inf may reach the result JSON.
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('application_kind,material,expected', [
    ('none', 'G14SFN', 'unavailable'),
    ('no_glasscat', 'G14SFN', 'unavailable'),
    ('unknown_profile', 'NOPE', 'unavailable'),
    ('unsupported', 'G14SFN', 'unsupported'),
])
def test_resource_metadata_reports_missing_states_without_raising(tmp_path, application_kind, material, expected):
    from types import SimpleNamespace
    from zemax_mcp.gradium import resource_metadata
    if application_kind == 'none':
        application = None
    elif application_kind == 'no_glasscat':
        application = SimpleNamespace(ZemaxDataDir=str(tmp_path / 'absent'))
    elif application_kind == 'unknown_profile':
        application = glasscat_tree(tmp_path)
    else:
        application = glasscat_tree(tmp_path, grd='NOT_A_PROFILE 5.8\n1.0\n')
    result = resource_metadata(application, 'PROFILE.GRD', material)
    assert result['status'] == expected
    assert result['reason']
    if application_kind == 'unknown_profile':
        assert result['profile']['available'] == ['G14SFN']


def test_resource_metadata_never_raises_on_broken_application():
    from types import SimpleNamespace
    from zemax_mcp.gradium import resource_metadata

    class Broken:
        @property
        def ZemaxDataDir(self):
            raise RuntimeError('no data directory')

    result = resource_metadata(Broken(), 'PROFILE.GRD', 'G14SFN')
    assert result['status'] == 'unavailable' and 'no data directory' in result['reason']
    assert resource_metadata(None, '', None)['status'] == 'unavailable'


def test_grin_source_context_keeps_curve_path_when_metadata_unavailable():
    from types import SimpleNamespace as NS
    from zemax_mcp.analyses import grin_source_context
    row = NS(Type='Gradium', Material='G14SFN', Thickness=1., SemiDiameter=2.)
    backend = NS(_row=lambda surface: row, _cell=lambda row, name: NS(DoubleValue=float(name.split('_')[1])),
                 system=NS(MCE=NS(CurrentConfiguration=1),
                           SystemData=NS(Files=NS(GradiumProfile='PROFILE.GRD'))),
                 native=NS(application=NS(ZemaxDataDir='relative/not/absolute')))
    context = grin_source_context(backend, 3)
    gradium = context['gradium']
    assert gradium['axial_offset'] == 2. and gradium['capping'] == 8.
    assert gradium['profile_file'] == 'PROFILE.GRD'
    assert gradium['reference_index_definition']
    assert gradium['resource_metadata']['status'] == 'unavailable'
    assert 'absolute' in gradium['resource_metadata']['reason']
