from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.wavefront_topics import (configure_zernike_field, configure_interferogram,
                                       check_interferogram_configurations, describe_wavefront_topic)


@pytest.mark.parametrize('patch', [
    {'coefficients': []}, {'coefficients': [4, 4]}, {'coefficients': [5, 4]},
    {'coefficients': [0, 1]}, {'coefficients': [232]},
    {'coefficient_type': 'Fringe', 'coefficients': [38]},
    {'obscuration': .1}, {'coefficient_type': 'Annular', 'obscuration': 1},
    {'scale_minimum': 2, 'scale_maximum': 1}, {'field_density': 1},
    {'scale_minimum': float('inf')}, {'wavelength': 0},
])
def test_zernike_field_typed_limits(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': 'zernike_coefficients_vs_field', **patch})


@pytest.mark.parametrize('coefficients', [[0], [1, 5, 6, 7], [231]])
def test_zernike_field_selection_and_worker_roundtrip(coefficients):
    req = RunAnalysis(request={'kind': 'zernike_coefficients_vs_field', 'coefficients': coefficients})
    assert RunAnalysis.model_validate(req.model_dump()) == req
    settings = {}
    configure_zernike_field(req.request, lambda k, v: settings.__setitem__(k, v))
    assert settings['Coefficients'] == ','.join(map(str, range(1,232) if coefficients==[0] else coefficients))
    assert settings['ZernikeCoefficientType'] == 'Standard'
    assert settings['FieldScanDirection'] == 'Plus_Y'
    assert settings['SampleSize'] == 'S_64x64'


@pytest.mark.parametrize('patch', [
    {'beam_1': 'Configuration_21'}, {'beam_2': 1}, {'surface': 0},
    {'x_tilt': float('nan')}, {'subaperture_radius': 0}, {'subaperture_x': 2},
    {'ref_beam_1_to_vertex': True, 'scale_factor': 2},
])
def test_interferogram_typed_limits(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': 'interferogram', **patch})


def test_interferogram_beams_match_native_configuration_count():
    q = RunAnalysis(request={'kind': 'interferogram', 'beam_2': 'Configuration_2'}).request
    with pytest.raises(ZemaxError) as exc:
        check_interferogram_configurations(q, 1)
    assert exc.value.code == 'INDEX_OUT_OF_RANGE'
    assert exc.value.details['setting'] == 'beam_2'
    check_interferogram_configurations(q, 2)
    settings = {}
    configure_interferogram(q, lambda k, v: settings.__setitem__(k, v))
    assert settings['Beam_1'] == 'Reference'
    assert settings['Beam_2'] == 'Configuration_2'
    assert settings['Subaperture_R'] == 1
    assert 'ContourFormat' not in settings
    assert RunAnalysis.model_validate(RunAnalysis(request=q).model_dump()).request == q


def test_zernike_field_results_keep_native_term_labels():
    data = dict(series=[dict(labels=['Z4', 'Z7'], x=[0, 1], y=[[1, 2], [3, 4]])])
    describe_wavefront_topic(data, dict(kind='zernike_coefficients_vs_field', coefficients=[4, 7], coefficient_type='Standard'))
    assert data['series'][0]['native_labels'] == ['Z4', 'Z7']
    assert data['series'][0]['value_units'] == ['waves', 'waves']
    with pytest.raises(ZemaxError) as exc:
        describe_wavefront_topic({'series': []}, dict(kind='zernike_coefficients_vs_field'))
    assert exc.value.code == 'NO_RESULT_DATA'


def test_interferogram_preserves_fringe_definition():
    req = RunAnalysis(request={'kind': 'interferogram', 'use_exit_pupil': False}).request
    data = {}
    describe_wavefront_topic(data, req.model_dump())
    assert data['pupil_coordinates'] == 'normalized entrance pupil'
    assert data['scale_factor_unit'] == 'fringes per wave OPD'
    assert 'value_units' not in data


@pytest.mark.parametrize('requested',[[4,6],[0]])
def test_native_zernike_table_mapping(requested):
    from zemax_mcp.wavefront_topics import zernike_field_text_series
    s=zernike_field_text_series('视场：\t4\t6\t\n0.0 -1e-1 0.2\n20.0 0.3 -0.4\n',requested)
    assert s['coefficient_terms']==[4,6]
    assert s['x']==[0,20] and s['y']==[[-.1,.2],[.3,-.4]]
    assert s['labels']==['Z4','Z6']


@pytest.mark.parametrize('table,requested',[
    ('视场： 4 6\n0 1\n',[4,6]),
    ('视场： 4 6\n0 nan 1\n',[4,6]),
    ('视场： 4 6\n0 1 2\n',[4,5]),
    ('视场： 4 4\n0 1 2\n',[4]),
])
def test_native_zernike_table_rejects_inconsistent_data(table,requested):
    from zemax_mcp.wavefront_topics import zernike_field_text_series
    with pytest.raises(ZemaxError)as e:zernike_field_text_series(table,requested)
    assert e.value.code=='INVALID_RESULT_DATA'


def test_no_native_zernike_table():
    from zemax_mcp.wavefront_topics import zernike_field_text_series
    assert zernike_field_text_series('native failed',[4])is None
    assert zernike_field_text_series('视场： 4\n',[4])is None


def test_native_zernike_minus_scan_preserves_distance():
    from zemax_mcp.wavefront_topics import zernike_field_text_series
    s=zernike_field_text_series('视场： 4\n0 1\n20 2\n',[4]);s['x_unit']='degrees'
    data=dict(series=[s])
    describe_wavefront_topic(data,dict(kind='zernike_coefficients_vs_field',coefficient_type='Standard',coefficients=[4],field_scan='Minus_X'))
    assert s['native_x']==[0,20] and s['x']==[0,-20]
    assert s['field_coordinates']==[dict(x=0,y=0),dict(x=-20,y=0)]


def test_headerless_table_uses_confirmed_setting_order():
    from zemax_mcp.wavefront_topics import zernike_field_text_series
    s=zernike_field_text_series('波长:0.48um\n0.0 1 2\n20.0 3 4\n',[0],[1,2])
    assert s['coefficient_terms']==[1,2] and s['native_term_header']is None
    assert s['y']==[[1,2],[3,4]]


def test_interferogram_grid_preserves_native_axes_and_exterior_fill():
    from zemax_mcp.analysis_models import RunAnalysis
    q=RunAnalysis(request=dict(kind='interferogram')).request.model_dump()
    values=[[1.,.5,1.],[1.,0.,1.]]
    grid=dict(nx=3,ny=2,values=values,x_label='None',y_label='None',value_label='None',
              min_x=-1,min_y=-1,dx=1,dy=2)
    data=dict(grids=[grid])
    describe_wavefront_topic(data,q)
    assert grid['values'] is values and grid['native_axes']['x_label']=='None'
    assert grid['value_unit']=='dimensionless' and grid['array_order']=='values[y][x]'
    assert 'finite exterior fill' in grid['pupil_validity']


def test_interferogram_grid_dimension_conflict():
    from zemax_mcp.analysis_models import RunAnalysis
    q=RunAnalysis(request=dict(kind='interferogram')).request.model_dump()
    with pytest.raises(ZemaxError) as caught:
        describe_wavefront_topic(dict(grids=[dict(nx=3,ny=2,values=[[1,2,3]])]),q)
    assert caught.value.code=='INVALID_RESULT_DATA'
