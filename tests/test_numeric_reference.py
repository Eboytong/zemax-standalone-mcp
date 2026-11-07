import pytest
from support.numeric_reference import mtf_text_values, cie_xyz, chromaticities, component_overlap


def test_mtf_display_parser_keeps_field_axis_and_frequency():
    values = mtf_text_values("视场：14.00 (度)\n0.0 1.0 1.0\n50.0 .2 .3\n")
    assert values[14., 50., "T"] == .2
    assert values[14., 50., "S"] == .3
    with pytest.raises(ValueError):
        mtf_text_values("50 .2 .3")


def test_cie_555nm_luminous_efficacy_reference():
    xyz = cie_xyz([(555, 1.)])
    assert xyz[1] == pytest.approx(683)
    assert chromaticities(xyz)["chromaticity_y"] > .5


def test_component_weighted_overlap_spatially_varying_jones():
    assert component_overlap([1, 0], [0, 2j], [0, 1], [2, 0]) == 0
    assert component_overlap([1, 0], [0, 2j], [1, 0], [0, 2j]) == pytest.approx(1)
