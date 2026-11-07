from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.universal import UniversalPlot1D,parse_curve
from zemax_mcp.universal_targets import resolve,verify
from zemax_mcp.errors import ZemaxError


def request(**patch):
    return UniversalPlot1D(**(dict(kind='universal_plot_1d',surface=1,start=2,stop=4,samples=3,target=dict(mode='merit',line=0))|patch))


@pytest.mark.parametrize('patch',[
    dict(target=dict(mode='merit',line=-1)),dict(target=dict(mode='merit',line=True)),
    dict(target=dict(mode='operand',operand='unknown')),dict(target=dict(mode='operand',operand='REAY',parameters=[float('nan')])),
    dict(target=dict(mode='operand',operand='REAY',parameters=[0]*9)),
    dict(first_surface=1),dict(operand='CVVA'),
])
def test_invalid_target_requests(patch):
    with pytest.raises(ValidationError):request(**patch)


def test_target_survives_request_serialization():
    q=request()
    assert UniversalPlot1D.model_validate(q.model_dump())==q


def test_merit_native_identity_and_line_type():
    q=request(target=dict(mode='merit',line=2))
    text='Independent Variable X: Thickness mm Surface 1\nDependent Variable Y: Merit Function Operand 2, TTHI\nX Y\n2 2\n3 3\n4 4\n'
    assert len(parse_curve(text,q,dict(line_operand='TTHI'))[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace('Operand 2','Operand 1'),q)
    with pytest.raises(ZemaxError):parse_curve(text,q,dict(line_operand='CVVA'))
    with pytest.raises(ZemaxError):parse_curve(text,request())


def test_generic_activity_integer_and_cleanup():
    closed=[]
    cells=[NS(IsActive=True,DataType='Integer',Header='Surf'),NS(IsActive=True,DataType='Integer',Header='Wave')]+[NS(IsActive=True,DataType='Double',Header='Data')for _ in range(4)]+[NS(IsActive=False)for _ in range(2)]
    row=NS(Type='REAY',ChangeType=lambda k:True,GetCellAt=lambda i:cells[i-2])
    copy=NS(MFE=NS(AddOperand=lambda:row),Close=lambda save:closed.append(save))
    b=NS(system=NS(LDE=NS(NumberOfSurfaces=3),SystemData=NS(Units=NS(LensUnits='Millimeters'),Wavelengths=NS(NumberOfWavelengths=1)),CopySystem=lambda:copy),native=NS(api=NS(Editors=NS(MFE=NS(MeritOperandType=None))),enum=lambda enum,name:name))
    q=request(target=dict(mode='operand',operand='REAY',parameters=[1,1,0,0,0,.5]))
    result=resolve(b,q);assert len(result['active_parameters'])==6 and closed==[False]
    verify('Dependent Variable Y: REAY, Surf=1, Wave=1, Hx=0, Hy=0, Px=0, Py=0.5',q.target,result)
    with pytest.raises(ZemaxError):verify('REAY, Surf=1, Wave=1, Hx=0, Hy=0, Px=0, Py=0.25',q.target,result)
    with pytest.raises(ZemaxError):resolve(b,request(target=dict(mode='operand',operand='REAY',parameters=[1.5,1])))
    with pytest.raises(ZemaxError):resolve(b,request(target=dict(mode='operand',operand='REAY',parameters=[1,1,0,0,0,0,1])))
    assert len(closed)==3
    with pytest.raises(ZemaxError)as error:resolve(b,request(target=dict(mode='operand',operand='REAY',parameters=[1,99])))
    assert error.value.code=='INDEX_OUT_OF_RANGE'and len(closed)==4


@pytest.mark.parametrize('report',['某些操作数不能计算!','Some operands cannot be computed!'])
def test_native_calculation_error_preserves_report(report):
    with pytest.raises(ZemaxError)as error:parse_curve(report,request())
    assert error.value.code=='ANALYSIS_FAILED'
    assert error.value.details['native_report']==report


def test_metadata_cleanup_retains_original_error_and_reconnect():
    def close(save):raise RuntimeError('metadata close failure')
    def change(kind):raise RuntimeError('metadata type failure')
    copy=NS(MFE=NS(AddOperand=lambda:NS(ChangeType=change)),Close=close)
    b=NS(system=NS(SystemData=NS(Units=NS(LensUnits='Millimeters')),CopySystem=lambda:copy),native=NS(api=NS(Editors=NS(MFE=NS(MeritOperandType=None))),enum=lambda enum,name:name),requires_reconnect=False)
    with pytest.raises(RuntimeError,match='metadata type failure')as error:resolve(b,request(target=dict(mode='operand',operand='REAY')))
    assert b.requires_reconnect and 'metadata close failure'in error.value.__notes__[0]


def test_merit_configuration_directives_are_explicit():
    rows=[NS(Type='CONF',GetCellAt=lambda i:NS(IntegerValue=2)),NS(Type='TTHI')]
    b=NS(system=NS(SystemData=NS(Units=NS(LensUnits='Millimeters')),MFE=NS(NumberOfOperands=2,GetOperandAt=lambda i:rows[i-1])))
    target=resolve(b,request())
    assert target['configuration_scope']=='merit CONF directives'
    assert target['merit_configurations']==[dict(line=1,configuration=2)]
