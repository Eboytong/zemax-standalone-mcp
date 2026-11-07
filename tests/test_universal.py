import pytest
from pydantic import ValidationError
from zemax_mcp.universal import UniversalPlot1D,parse_curve
from zemax_mcp.errors import ZemaxError


def request(**patch):return UniversalPlot1D(**(dict(kind='universal_plot_1d',surface=1,start=2,stop=6,samples=5,first_surface=1,last_surface=1)|patch))

@pytest.mark.parametrize('patch',[dict(samples=True),dict(samples=1),dict(start=6),dict(stop=float('inf')),dict(last_surface=0),dict(parameter='missing')])
def test_ranges(patch):
    with pytest.raises(ValidationError):request(**patch)


def test_text_readback_and_refused_selection():
    text='自变量X : 厚度mm表面1\n因变量Y : TTHI, 面1=1, 面2=1\n X Y\n2 2\n3 3\n4 4\n5 5\n6 6\n'
    rows,actual=parse_curve(text,request());assert len(rows)==5 and actual['stop']==6
    with pytest.raises(ZemaxError):parse_curve(text.replace('表面1','表面2'),request())
    with pytest.raises(ZemaxError):parse_curve(text.replace('6 6','7 6'),request())


@pytest.mark.parametrize('parameter,caption',[('Radius','半径mm'),('Curvature','曲率倒数mm')])
def test_native_parameter_identity(parameter,caption):
    text='自变量X : '+caption+'表面1\n因变量Y : TTHI, 面1=1, 面2=1\n X Y\n2 0\n3 0\n4 0\n5 0\n6 0\n'
    assert len(parse_curve(text,request(parameter=parameter))[0])==5
    with pytest.raises(ZemaxError):parse_curve(text,request(parameter='Thickness'))



def test_operand_specific_parameters_and_readback():
    q=request(operand='CVVA',last_surface=None)
    text='自变量X : 厚度mm表面1\n因变量Y : CVVA, 面=1\n X Y\n2 0\n3 0\n4 0\n5 0\n6 0\n'
    assert len(parse_curve(text,q)[0])==5
    with pytest.raises(ZemaxError):parse_curve(text.replace('面=1','面=2'),q)
    with pytest.raises(ValidationError):request(operand='CVVA')
    with pytest.raises(ValidationError):request(last_surface=None)
    with pytest.raises(ValidationError):request(operand='CURV')



def test_setup_failure_retains_original_when_copy_close_fails(monkeypatch):
    from types import SimpleNamespace as NS
    from zemax_mcp import universal
    def close(save):raise RuntimeError('copy close failure')
    backend=NS(_require_sequential=lambda:None,_row=lambda i:None,system=NS(SystemData=NS(Units=NS(LensUnits='Millimeters')),CopySystem=lambda:NS(Close=close)),native=None,requires_reconnect=False)
    def fail(*args):raise RuntimeError('original analysis factory failure')
    monkeypatch.setattr(universal,'new_analysis',fail)
    with pytest.raises(RuntimeError,match='original analysis factory failure')as error:universal.run(backend,request())
    assert backend.requires_reconnect and 'copy close failure'in error.value.__notes__[0]


@pytest.mark.parametrize('parameter,label',[('Temperature','温度'),('Pressure','压力'),('Aperture','系统孔径'),('ApodizationFactor','切趾因子')])
def test_system_identity_and_category_conditions(parameter,label):
    q=request(category='System',parameter=parameter,surface=None)
    text='自变量X : '+label+'\n因变量Y : TTHI, 面1=1, 面2=1\n X Y\n2 0\n3 0\n4 0\n5 0\n6 0\n'
    assert len(parse_curve(text,q)[0])==5
    with pytest.raises(ValidationError):request(category='Surface',parameter=parameter)
    with pytest.raises(ValidationError):request(category='System',parameter=parameter)



def test_uniform_apodization_scan_is_inactive_before_copy():
    from types import SimpleNamespace as NS
    from zemax_mcp import universal
    b=NS(_require_sequential=lambda:None,_row=lambda i:None,system=NS(SystemData=NS(Aperture=NS(ApodizationType='Uniform')),CopySystem=lambda:pytest.fail('inactive scan copied system')))
    with pytest.raises(ZemaxError)as error:universal.run(b,request(category='System',parameter='ApodizationFactor',surface=None))
    assert error.value.code=='INACTIVE_SETTING'


@pytest.mark.parametrize('parameter,expected',[('XField',2),('YField',4),('Wavelength',6),('ApodizationFactor',7),('Temperature',8),('Pressure',9)])
def test_dynamic_system_indices(parameter,expected):
    from types import SimpleNamespace as NS
    from zemax_mcp.universal import system_parameter_index
    q=request(category='System',surface=None,parameter=parameter,selection=2 if parameter in {'XField','YField','Wavelength'}else None)
    system=NS(SystemData=NS(Fields=NS(NumberOfFields=2),Wavelengths=NS(NumberOfWavelengths=2)))
    assert system_parameter_index(system,q)==expected


def test_explicit_index_and_native_identity():
    from types import SimpleNamespace as NS
    from zemax_mcp.universal import system_parameter_index
    q=request(category='System',surface=None,parameter='Wavelength',selection=2)
    text='自变量X : 波长2\n因变量Y : TTHI, 面1=1, 面2=1\n X Y\n2 0\n3 0\n4 0\n5 0\n6 0\n'
    assert len(parse_curve(text,q)[0])==5
    with pytest.raises(ZemaxError):parse_curve(text.replace('波长2','波长1'),q)
    with pytest.raises(ValidationError):request(category='System',surface=None,parameter='Wavelength')
    with pytest.raises(ValidationError):request(selection=1)
    with pytest.raises(ZemaxError):system_parameter_index(NS(SystemData=NS(Fields=NS(NumberOfFields=1),Wavelengths=NS(NumberOfWavelengths=1))),q)



def test_object_height_requires_finite_object_distance():
    from types import SimpleNamespace as NS
    from zemax_mcp import universal
    source=NS(SystemData=NS(Fields=NS(NumberOfFields=2,GetFieldType=lambda:'ObjectHeight'),Wavelengths=NS(NumberOfWavelengths=2)),LDE=NS(GetSurfaceAt=lambda i:NS(Thickness=float('inf'))),CopySystem=lambda:pytest.fail('invalid object-height model copied'))
    b=NS(_require_sequential=lambda:None,_row=lambda i:None,system=source)
    with pytest.raises(ZemaxError)as error:universal.run(b,request(category='System',surface=None,parameter='XField',selection=2))
    assert error.value.code=='INVALID_MODEL'


@pytest.mark.parametrize('patch',[
    dict(configuration=None),dict(operand_row=None),dict(surface=1),
    dict(parameter='Thickness'),dict(selection=1),dict(configuration=0),
])
def test_configuration_axis_constraints(patch):
    q=dict(category='Configuration',surface=None,parameter='THIC',configuration=2,operand_row=3)
    with pytest.raises(ValidationError):request(**(q|patch))


def test_configuration_readback_and_cell_conditions():
    from types import SimpleNamespace as NS
    from zemax_mcp.universal import resolve_axis
    q=request(category='Configuration',surface=None,parameter='THIC',configuration=2,operand_row=3)
    text='自变量X : 3: THIC 1\n因变量Y : TTHI, 面1=1, 面2=1\n X Y\n2 2\n3 3\n4 4\n5 5\n6 6\n'
    assert len(parse_curve(text,q)[0])==5
    with pytest.raises(ZemaxError):parse_curve(text.replace('3: THIC','2: THIC'),q)
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',DataType='Double')
    row=NS(Type='THIC',Param1=1,Param1Enabled=True,Param2Enabled=False,Param3Enabled=False,GetOperandCell=lambda c:cell)
    source=NS(MCE=NS(NumberOfConfigurations=2,NumberOfOperands=3,GetOperandAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    assert resolve_axis(source,q)['native_parameter_index']==3
    assert resolve_axis(source,q)['native_surface']==2
    cell.Solve='ConfigPickup'
    with pytest.raises(ZemaxError)as error:resolve_axis(source,q)
    assert error.value.code=='INACTIVE_SETTING'
    cell.Solve='Fixed';row.Type='CRVT'
    with pytest.raises(ZemaxError)as error:resolve_axis(source,q)
    assert error.value.code=='INVALID_ARGUMENT'
