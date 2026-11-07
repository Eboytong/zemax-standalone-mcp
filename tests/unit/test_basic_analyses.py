import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.basic_analyses import parse_native_tables

@pytest.mark.parametrize('payload',[dict(kind='grid_distortion'),dict(kind='single_ray_trace',hx=2),dict(kind='seidel_coefficients',wavelength=0),dict(kind='cardinal_points',orientation='XY')])
def test_invalid_basic_requests(payload):
    with pytest.raises(ValidationError):RunAnalysis(request=payload)

def test_seidel_special_rows_and_units():
    text='Seidel\nSurface SPHA S1 COMA S2\n1 1.0 2.0\nSTOP 3.0 4.0\nSum 4.0 6.0\n\nWave\nSurface W040 W131\n1 .1 .2\nSum .1 .2'
    rows=parse_native_tables(text,'seidel_coefficients')['rows']
    assert len(rows)==5 and rows[1]['coefficients']['SPHA']==3
    assert rows[-1]['unit']=='waves'

def test_grid_percent_and_coordinates():
    r=parse_native_tables('i j X Y R PX PY RX RY distortion\n0 1 0 1 1 0 2 0 2.1 5.0%','grid_distortion')
    assert r['rows'][0]['distortion_percent']==5
    assert r['scatter'][1]['points'][0]['y']==2.1
