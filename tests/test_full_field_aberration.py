import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import ANALYSES


def test_full_field_aberration_defaults_and_dispatch():
    request = RunAnalysis(request={"kind": "full_field_aberration"}).request
    assert request.field_shape == "Rectangular"
    assert request.aberration_type == "Defocus"
    assert request.aberration_number is None
    assert ANALYSES[request.kind] == "FullFieldAberration"


def test_specified_term_requires_number():
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "full_field_aberration", "aberration_type": "SpecifiedTerm"})


def test_aberration_number_only_applies_to_specified_term():
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "full_field_aberration", "aberration_number": 7})


@pytest.mark.parametrize("patch", [
    {"field_shape": "Circular"},
    {"decomposition": "Fringe"},
    {"aberration_type": "Spherical"},
    {"aberration_type": "SpecifiedTerm", "aberration_number": 0},
    {"maximum_term": 0},
    {"x_field_sampling": 1},
    {"pupil_sampling": "S_16x16"},
    {"show_as": "Bitmap"},
    {"display": "Sum"},
    {"x_field_width": 0},
])
def test_full_field_aberration_rejects_invalid_native_settings(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind": "full_field_aberration", **patch})


def test_full_field_map_metadata_keeps_non_square_native_axes():
    from zemax_mcp.full_field_aberration import describe_full_field
    q=RunAnalysis(request=dict(kind='full_field_aberration',x_field_sampling=7,y_field_sampling=5,
        aberration_type='SpecifiedTerm',aberration_number=5)).request.model_dump()
    g=dict(nx=7,ny=5,min_x=-4,min_y=-2,dx=4/3,dy=1,
           x_label='None',y_label='None',value_label='None',values=[[0]*7 for _ in range(5)])
    result=describe_full_field(dict(grids=[g]),q,dict(field_type='Angle',lens_units='Millimeters'))
    assert result['coefficient_definition']=='Standard Zernike coefficient 5'
    assert g['value_unit']=='waves' and g['x_unit']=='degrees'
    assert g['native_axes']['y_label']=='None' and g['min_y']==-2
    assert g['array_order']=='values[y][x]'


def test_full_field_map_dimension_conflict_rejected():
    from zemax_mcp.full_field_aberration import describe_full_field
    from zemax_mcp.errors import ZemaxError
    q=RunAnalysis(request=dict(kind='full_field_aberration',x_field_sampling=7,y_field_sampling=5)).request.model_dump()
    with pytest.raises(ZemaxError) as caught:
        describe_full_field(dict(grids=[dict(nx=5,ny=7,values=[[0]*5 for _ in range(7)])]),q,{})
    assert caught.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('display',['Absolute','Relative','Average'])
def test_full_field_display_annotation_preserves_native_mask_and_values(display):
    from zemax_mcp.full_field_aberration import describe_full_field
    q=RunAnalysis(request=dict(kind='full_field_aberration',display=display,x_field_sampling=3,y_field_sampling=2)).request.model_dump()
    values=[[None,.2,.1],[.3,0,None]]
    g=dict(nx=3,ny=2,min_x=-1,min_y=-1,dx=1,dy=2,values=values)
    result=describe_full_field(dict(grids=[g]),q,dict(field_type='ObjectHeight',lens_units='Centimeters'))
    assert g['values']is values and g['x_unit']=='Centimeters'
    assert result['display_definition']==g['display_definition']
