from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.universal import UniversalPlot1D,resolve_axis,parse_curve
from zemax_mcp.errors import ZemaxError


def request(**patch):
    return UniversalPlot1D(**(dict(kind='universal_plot_1d',category='NSC',object=1,parameter='XPosition',start=2,stop=4,samples=3,target=dict(mode='merit'))|patch))


@pytest.mark.parametrize('patch',[dict(object=None),dict(object=0),dict(surface=1),dict(selection=1),dict(parameter='Thickness'),dict(configuration=1),dict(category='System')])
def test_nsc_request_constraints(patch):
    with pytest.raises(ValidationError):request(**patch)


@pytest.mark.parametrize('parameter,caption,index',[('XPosition','X位置：mm',0),('YPosition','Y位置：mm',1),('ZPosition','Z位置：mm',2),('TiltX','X倾斜：角度',3),('TiltY','Y倾斜：角度',4),('TiltZ','Z倾斜：角度',5)])
def test_nsc_identity_and_native_mapping(parameter,caption,index):
    q=request(parameter=parameter)
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',Header='Position')
    row=NS(Type='NullObject',**{name+'Cell':cell for name in ['XPosition','YPosition','ZPosition','TiltAboutX','TiltAboutY','TiltAboutZ']})
    s=NS(Mode='NonSequential',NCE=NS(NumberOfObjects=1,GetObjectAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    assert resolve_axis(s,q)['native_parameter_index']==index
    text='自变量X : '+caption+'物体1\n因变量Y : 评价函数\nX Y\n2 2\n3 3\n4 4\n'
    assert len(parse_curve(text,q)[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace('物体1','物体2'),q)
    cell.Solve='Pickup'
    with pytest.raises(ZemaxError)as error:resolve_axis(s,q)
    assert error.value.code=='INACTIVE_SETTING'


def test_nsc_mixed_group_requires_explicit_selection():
    with pytest.raises(ZemaxError)as error:resolve_axis(NS(Mode='Sequential'),request())
    assert error.value.code=='INVALID_ARGUMENT'


def test_mixed_nsc_category_mapping_and_restore():
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',Header='Position')
    row=NS(Type='NullObject',XPositionCell=cell)
    class Editor:
        ActiveSurface=4;NumberOfObjects=1
        def SetActiveSurface(self,index):self.ActiveSurface=index;return True
        def GetObjectAt(self,index):return row
    source=NS(Mode='Sequential',NCE=Editor(),LDE=NS(NumberOfSurfaces=6,GetSurfaceAt=lambda i:NS(Type='NonSequential'if i in {2,4}else'Standard')),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    assert resolve_axis(source,request(nsc_surface=2))['category_index']==3
    assert source.NCE.ActiveSurface==4
    assert resolve_axis(source,request(nsc_surface=4))['category_index']==4
    assert source.NCE.ActiveSurface==4
    with pytest.raises(ZemaxError)as error:resolve_axis(source,request(nsc_surface=3))
    assert error.value.code=='INVALID_NSC_GROUP'
    cell.IsActive=False
    with pytest.raises(ZemaxError)as error:resolve_axis(source,request(nsc_surface=2))
    assert error.value.code=='INACTIVE_SETTING'and source.NCE.ActiveSurface==4
    source.NCE.SetActiveSurface=lambda index:False if index==4 else setattr(source.NCE,'ActiveSurface',index)or True
    from zemax_mcp.universal import checked_axis
    backend=NS(system=source,native=None,requires_reconnect=False)
    with pytest.raises(ZemaxError)as error:checked_axis(backend,request(nsc_surface=2))
    assert error.value.code=='RESTORE_FAILED'and backend.requires_reconnect
    assert error.value.details['operation_error']['code']=='INACTIVE_SETTING'


def test_nsc_axes_require_an_explicit_target_and_distinct_parameter_numbers():
    from zemax_mcp.universal_grid import UniversalPlot2D
    with pytest.raises(ValidationError):request(target=None,first_surface=1,last_surface=1)
    axis=dict(category='NSC',object=1,parameter='ObjectParameter',parameter_number=1,start=2,stop=4,samples=3)
    assert UniversalPlot2D(kind='universal_plot_2d',x=axis,y=axis|dict(parameter_number=2),target=dict(mode='merit')).y.parameter_number==2
    with pytest.raises(ValidationError):UniversalPlot2D(kind='universal_plot_2d',x=axis,y=axis,target=dict(mode='merit'))


@pytest.mark.parametrize('patch',[dict(parameter_number=None),dict(parameter_number=0),dict(parameter_number=251),dict(parameter='XPosition')])
def test_object_parameter_number_constraints(patch):
    with pytest.raises(ValidationError):request(**(dict(parameter='ObjectParameter',parameter_number=1)|patch))


def test_object_parameter_readback_and_integer_sampling():
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',DataType='Integer',Header='Test integer')
    row=NS(Type='Rectangle',GetObjectCell=lambda c:cell)
    source=NS(Mode='NonSequential',NCE=NS(NumberOfObjects=1,GetObjectAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    native=NS(api=NS(Editors=NS(NCE=NS(ObjectColumn=None))),enum=lambda owner,name:name)
    q=request(parameter='ObjectParameter',parameter_number=1)
    assert resolve_axis(source,q,native)['native_parameter_index']==6
    text='自变量X : 参数1物体1\n因变量Y : 评价函数\nX Y\n2 2\n3 3\n4 4\n'
    assert len(parse_curve(text,q)[0])==3
    with pytest.raises(ZemaxError):parse_curve(text.replace('参数1','参数2'),q)
    with pytest.raises(ZemaxError)as error:resolve_axis(source,request(parameter='ObjectParameter',parameter_number=1,samples=4),native)
    assert error.value.code=='INVALID_ARGUMENT'
