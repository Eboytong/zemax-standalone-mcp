import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import configure_contrast_loss


def test_contrast_loss_defaults_and_roundtrip():
    request=RunAnalysis(request={'kind':'contrast_loss'})
    assert request.request.sampling=='S_41x41'
    assert request.request.frequency==50
    assert RunAnalysis.model_validate(request.model_dump())==request


@pytest.mark.parametrize('payload', [
    {'frequency':-1},
    {'sampling':'S_4x4'},
    {'field':0},
    {'wavelength':0},
])
def test_contrast_loss_rejects_invalid_options(payload):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind':'contrast_loss',**payload})


def test_contrast_loss_configures_all_native_fields():
    request=RunAnalysis(request={'kind':'contrast_loss','sampling':'S_63x63','frequency':72.5,'normalize':False,'show_opd':True}).request
    settings={}
    configure_contrast_loss(request,lambda name,value:settings.__setitem__(name,value))
    assert settings=={'SampleSize':'S_63x63','Frequency':72.5,'Normalize':False,'ShowOPD':True}


def grids():
    return [dict(description=d+' '+q,nx=2,ny=1,values=[[None,.2]],x_label='None',
                 y_label='None',value_label='None',min_x=-1,min_y=0,dx=2,dy=1)
            for d in ['子午的','弧矢的'] for q in ['相位','对比度损失图']]


def test_contrast_loss_grid_identities_and_units():
    from zemax_mcp.contrast_loss import describe_contrast_loss
    q=RunAnalysis(request=dict(kind='contrast_loss')).request.model_dump()
    original=grids();data=describe_contrast_loss(dict(grids=original),q,'CyclesPerMillimeter')
    assert [g['value_unit'] for g in original]==['degrees','dimensionless','degrees','dimensionless']
    assert original[2]['direction']=='Sagittal' and original[0]['native_axes']['x_label']=='None'
    assert original[1]['values']==[[None,.2]] and data['display_normalize'] is True


@pytest.mark.parametrize('issue',['empty','unknown','duplicate','missing','shape'])
def test_contrast_loss_invalid_native_grids(issue):
    from zemax_mcp.contrast_loss import describe_contrast_loss
    from zemax_mcp.errors import ZemaxError
    selected=grids()
    if issue=='empty':selected=[]
    elif issue=='unknown':selected[0]['description']='unknown'
    elif issue=='duplicate':selected[1]['description']=selected[0]['description']
    elif issue=='missing':selected.pop()
    else:selected[0]['ny']=2
    with pytest.raises(ZemaxError) as error:
        describe_contrast_loss(dict(grids=selected),RunAnalysis(request=dict(kind='contrast_loss')).request.model_dump(),'CyclesPerMillimeter')
    assert error.value.code==('NO_RESULT_DATA' if issue=='empty' else 'INVALID_RESULT_DATA')
