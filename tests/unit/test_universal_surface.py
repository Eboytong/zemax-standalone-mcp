from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.universal import UniversalPlot1D,resolve_axis,parse_curve
from zemax_mcp.errors import ZemaxError


def request(**patch):
    return UniversalPlot1D(**(dict(kind='universal_plot_1d',surface=1,parameter='Conic',start=0,stop=2,samples=3,first_surface=1,last_surface=1)|patch))


@pytest.mark.parametrize('patch',[dict(parameter='SurfaceParameter'),dict(parameter_number=1),dict(parameter='SurfaceParameter',parameter_number=0),dict(parameter='SurfaceParameter',parameter_number=255),dict(category='System',surface=None)])
def test_surface_parameter_request_constraints(patch):
    with pytest.raises(ValidationError):request(**patch)


def fixture():
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',Header='Parameter',DataType='Double')
    row=NS(Type='CoordinateBreak',ConicCell=cell,TCECell=cell,GetSurfaceCell=lambda kind:cell)
    source=NS(LDE=NS(GetSurfaceAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    native=NS(api=NS(Editors=NS(LDE=NS(SurfaceColumn=None))),enum=lambda owner,name:name)
    return source,native,cell


@pytest.mark.parametrize('parameter,number,index,unit,caption',[
    ('Conic',None,4,'dimensionless','圆锥系数'),
    ('TCE',None,5,'ppm/Celsius','TCE'),
    ('SurfaceParameter',1,7,'Millimeters','参数1'),
    ('SurfaceParameter',3,9,'degrees','参数3'),
])
def test_surface_native_mapping_and_identity(parameter,number,index,unit,caption):
    source,native,cell=fixture();q=request(parameter=parameter,parameter_number=number)
    axis=resolve_axis(source,q,native)
    assert axis['native_parameter_index']==index and axis['unit']==unit
    text='自变量X : '+caption+'表面1\n因变量Y : TTHI, 面1=1, 面2=1\nX Y\n0 2\n1 2\n2 2\n'
    assert len(parse_curve(text,q)[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace('表面1','表面2'),q)
    cell.Solve='SurfacePickup'
    with pytest.raises(ZemaxError)as error:resolve_axis(source,q,native)
    assert error.value.code=='INACTIVE_SETTING'


def test_surface_integer_parameter_samples():
    source,native,cell=fixture();cell.DataType='Integer'
    with pytest.raises(ZemaxError)as error:resolve_axis(source,request(parameter='SurfaceParameter',parameter_number=6,samples=4),native)
    assert error.value.code=='INVALID_ARGUMENT'
