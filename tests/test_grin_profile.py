import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import configure_grin_profile


@pytest.mark.parametrize("axis",["X","Y","Z"])
def test_grin_profile_request_round_trip(axis):
    request=RunAnalysis(request={"kind":"grin_profile","surface":3,"show_index_vs":axis})
    assert RunAnalysis.model_validate(request.model_dump())==request


@pytest.mark.parametrize("changes",[
    {"surface":0},{"show_index_vs":"R"},{"minimum_x":-1},{"minimum_z":2,"maximum_z":1},
    {"minimum_index":1.4},{"minimum_index":1.6,"maximum_index":1.5},{"x_value":float("inf")},
    {"minimum_y":-1,"maximum_y":1},{"x_value":0},
])
def test_grin_profile_rejects_invalid_settings(changes):
    with pytest.raises(ValidationError):
        RunAnalysis(request={"kind":"grin_profile","surface":3,"show_index_vs":"X",**changes})


def test_grin_profile_applies_axis_and_only_requested_ranges():
    request=RunAnalysis(request={"kind":"grin_profile","surface":3,"show_index_vs":"Y","minimum_y":-1,"maximum_y":1,"z_value":0}).request
    actual={"MaximumX":3.0}
    configure_grin_profile(request,lambda name,value:actual.__setitem__(name,value))
    assert actual=={"MaximumX":3.0,"ShowIndexVs":"Y","MinimumY":-1,"MaximumY":1,"Z_Value":0}


def test_grin_profile_result_units_and_native_axes():
    from zemax_mcp.analyses import label_grin_profile
    data=dict(series=[dict(series=0,x_label='native coordinate',labels=['None'],x=[0],y=[[1.5]])])
    label_grin_profile(data,dict(show_index_vs='Y'),'Millimeters')
    curve=data['series'][0]
    assert curve['native_axes']==dict(x_label='native coordinate',labels=['None'])
    assert curve['x_label']=='Y' and curve['x_unit']=='Millimeters' and curve['y_unit']=='dimensionless'


@pytest.mark.parametrize('curves',[[],[dict(series=0,x=[],y=[],x_label='',labels=[])],[dict(series=0,x=[0],y=[[1,2]],x_label='',labels=[])]])
def test_grin_profile_requires_index_curve(curves):
    from zemax_mcp.analyses import label_grin_profile
    from zemax_mcp.errors import ZemaxError
    with pytest.raises(ZemaxError):label_grin_profile(dict(series=curves),dict(show_index_vs='X'),'Millimeters')


@pytest.mark.parametrize('kind',['Gradient1','Gradium'])
def test_grin_source_context_retains_profile_and_reference_wavelength_identity(kind):
    from types import SimpleNamespace as NS
    from zemax_mcp.analyses import grin_source_context
    row=NS(Type=kind,Material='G14SFN',Thickness=1.,SemiDiameter=2.)
    b=NS(_row=lambda surface:row,_cell=lambda row,name:NS(DoubleValue=float(name.split('_')[1])),
        system=NS(MCE=NS(CurrentConfiguration=2),SystemData=NS(Files=NS(GradiumProfile='PROFILE.GRD'))))
    result=grin_source_context(b,3)
    assert result['surface']==3 and result['configuration']==2 and result['material']=='G14SFN'
    if kind=='Gradium':
        assert result['gradium']['profile_file']=='PROFILE.GRD'
        assert result['gradium']['reference_vertex_index']==3.
        assert result['gradium']['capping']==8.
        assert 'separate'in result['gradium']['reference_index_definition']
    else:assert 'gradium'not in result
