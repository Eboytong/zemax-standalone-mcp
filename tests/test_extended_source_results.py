import numpy as np
import pytest

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.extended_source import describe_extended_source
from zemax_mcp.errors import ZemaxError
from support.extended_source_reference import square_energy,airy_energy


def test_analytic_uniform_square_area_limits():
    r=np.array([0,5,10,10*2**.5,20])
    np.testing.assert_allclose(square_energy(r,'Encircled'),[0,np.pi/16,np.pi/4,1,1],atol=1e-14)
    np.testing.assert_allclose(square_energy(r,'Ensquared'),[0,.25,1,1,1])
    np.testing.assert_allclose(square_energy(r,'X_Only'),[0,.5,1,1,1])


def test_airy_quadrature_origin_small_argument_and_energy_monotonicity():
    radius=np.array([0,.01*55/np.pi])
    np.testing.assert_allclose(airy_energy(radius,.55,100),[0,.01**2/4],atol=1e-9,rtol=0)
    values=airy_energy(np.linspace(0,200,200),.55,100)
    assert np.all(np.diff(values)>=-1e-12) and values[-1]<1


@pytest.mark.parametrize('kind',['Encircled','X_Only','Y_Only','Ensquared','X_Distrib','Y_Distrib'])
def test_extended_source_units_native_coordinates_and_source_conditions(kind):
    q=RunAnalysis(request=dict(kind='extended_source_encircled_energy',image_name='square.IMA',data_type=kind)).request.model_dump()
    x=[i*20/396 for i in range(396)];y=[[.5] for _ in x]
    curve=dict(x=x,y=y,labels=['None'])
    data=describe_extended_source(dict(series=[curve]),q,dict(field_type='ObjectHeight',lens_units='Millimeters'))
    assert curve['x'] is x and curve['y'] is y and curve['labels']==[kind]
    assert curve['x_unit']=='micrometers' and data['extended_source_conditions']['field_size_unit']=='Millimeters'
    assert curve['x_label'].startswith('Image' if kind.endswith('Distrib') else 'Native reported')
    assert curve['value_units']==['relative distribution' if kind.endswith('Distrib') else 'fraction']
    if not kind.endswith('Distrib'):
        assert curve['native_binning']['interval_um']==pytest.approx(20/99)
        assert curve['native_binning']['enclosure_radius_um'][4]==0
        assert curve['native_x']==x
    else:assert 'native_binning' not in curve


def test_extended_source_unknown_sampling_does_not_infer_bin_mapping():
    q=RunAnalysis(request=dict(kind='extended_source_encircled_energy',image_name='square.IMA')).request.model_dump()
    curve=dict(x=[0,1],y=[[0],[1]],labels=['None'])
    describe_extended_source(dict(series=[curve]),q,dict(field_type='Angle'))
    assert 'native_binning' not in curve


@pytest.mark.parametrize('series',[[],[dict(x=[0],y=[[0,1]],labels=['a','b'])]])
def test_extended_source_empty_or_conflicting_output(series):
    q=RunAnalysis(request=dict(kind='extended_source_encircled_energy',image_name='square.IMA')).request.model_dump()
    with pytest.raises(ZemaxError) as caught:describe_extended_source(dict(series=series),q,{})
    assert caught.value.code==('NO_RESULT_DATA' if not series else 'INVALID_RESULT_DATA')


def test_paging_preserves_parallel_native_axes_and_bin_edges(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.models import TaskResult
    b=Backend(Config(tmp_path,tmp_path/'out'))
    curve=dict(x=[0,1,2,3],y=[[0],[.2],[.5],[1]],native_x=[0,1,2,3],
               field_coordinates=[{'x':i,'y':0} for i in range(4)],
               native_binning=dict(interval_um=1,enclosure_radius_um=[0,0,1,2]))
    result=b._page_task_result(dict(series=[curve]),TaskResult(task_id='x',series=0,start=1,count=2))
    page=result['series'][0]
    assert page['x']==page['native_x']==[1,2]
    assert page['field_coordinates']==[{'x':1,'y':0},{'x':2,'y':0}]
    assert page['native_binning']['enclosure_radius_um']==[0,1]
    assert len(curve['native_binning']['enclosure_radius_um'])==4
