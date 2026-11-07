from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.universal import UniversalPlot1D,resolve_axis,parse_curve
from zemax_mcp.errors import ZemaxError


def request(**patch):
    return UniversalPlot1D(**(dict(kind='universal_plot_1d',category='Configuration',parameter='ConfigurationValue',mce_operand='TEMP',configuration=1,operand_row=2,start=10,stop=30,samples=3,target=dict(mode='merit'))|patch))


@pytest.mark.parametrize('patch',[dict(mce_operand=None),dict(mce_operand='bad'),dict(parameter='THIC'),dict(configuration=None),dict(operand_row=0)])
def test_configuration_value_constraints(patch):
    with pytest.raises(ValidationError):request(**patch)


def source(kind='TEMP',dtype='Double',parameters=()):
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',DataType=dtype)
    row=NS(Type=kind,GetOperandCell=lambda c:cell)
    for i in range(1,4):setattr(row,'Param'+str(i)+'Enabled',i<=len(parameters));setattr(row,'Param'+str(i),parameters[i-1]if i<=len(parameters)else 0)
    return NS(MCE=NS(NumberOfConfigurations=2,NumberOfOperands=2,GetOperandAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters'),Wavelengths=NS(NumberOfWavelengths=2),Fields=NS(NumberOfFields=2,GetFieldType=lambda:'Angle'))),cell


def test_native_mce_type_parameter_readback_and_non_numeric_rejection():
    s,cell=source();q=request();axis=resolve_axis(s,q)
    assert axis['unit']=='Celsius'and axis['operand_parameters']==[]
    text='自变量X : 2: TEMP -\n因变量Y : 评价函数\nX Y\n10 2\n20 2\n30 2\n'
    assert len(parse_curve(text,q,resolved_axis=axis)[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace('TEMP','PRES'),q,resolved_axis=axis)
    cell.DataType='String'
    with pytest.raises(ZemaxError)as error:resolve_axis(s,q)
    assert error.value.code=='UNSUPPORTED_SETTING'


@pytest.mark.parametrize('kind,low,high',[('TEMP',-274,0),('PRES',-1,1),('WAVE',0,1)])
def test_known_mce_physical_ranges(kind,low,high):
    s,cell=source(kind)
    with pytest.raises(ZemaxError)as error:resolve_axis(s,request(mce_operand=kind,start=low,stop=high))
    assert error.value.code=='INVALID_ARGUMENT'


def test_mce_integer_sampling_and_row_parameter_identity():
    s,cell=source('THIC','Integer',(1,));q=request(mce_operand='THIC',start=2,stop=4)
    axis=resolve_axis(s,q)
    text='自变量X : 2: THIC 1\n因变量Y : 评价函数\nX Y\n2 2\n3 3\n4 4\n'
    with pytest.raises(ZemaxError)as error:parse_curve(text.replace('THIC 1','THIC 2'),q,resolved_axis=axis)
    assert error.value.code=='SETTING_REJECTED'
    with pytest.raises(ZemaxError)as error:resolve_axis(s,request(mce_operand='THIC',start=2,stop=4,samples=4))
    assert error.value.code=='INVALID_ARGUMENT'


@pytest.mark.parametrize('kind',['WAVE','XFIE','YFIE'])
def test_mce_zero_based_selector_display_mapping(kind):
    s,cell=source(kind,parameters=(1,));q=request(mce_operand=kind)
    axis=resolve_axis(s,q)
    assert axis['native_operand_parameters']==[1]and axis['operand_parameters']==[2]
    text='自变量X : 2: '+kind+' 2\n因变量Y : 评价函数\nX Y\n10 2\n20 2\n30 2\n'
    assert len(parse_curve(text,q,resolved_axis=axis)[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace(kind+' 2',kind+' 1'),q,resolved_axis=axis)
