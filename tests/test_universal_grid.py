import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from zemax_mcp.universal_grid import UniversalPlot2D,readback
from zemax_mcp.errors import ZemaxError


def request(**extra):
    base=dict(kind='universal_plot_2d',x=dict(surface=1,start=2,stop=6,samples=5),y=dict(surface=2,start=3,stop=5,samples=3),first_surface=1,last_surface=2)
    return UniversalPlot2D(**(base|extra))

@pytest.mark.parametrize('extra',[dict(last_surface=None),dict(operand='CURV'),dict(operand='CVVA'),dict(y=dict(surface=1,start=3,stop=5)),dict(x=dict(surface=1,start=2,stop=6,samples=1001),y=dict(surface=2,start=3,stop=5,samples=1001))])
def test_invalid_grid_requests(extra):
    with pytest.raises(ValidationError):request(**extra)


def test_native_non_square_grid_and_refused_header():
    r=json.loads((Path(__file__).parent/'reference_data/universal202-grid.json').read_text(encoding='utf-8'))
    actual=readback(r['text'],request(),r['grid']);assert actual['Y']['samples']==3
    with pytest.raises(ZemaxError):readback(r['text'].replace('3 - 5','3 - 9'),request(),r['grid'])
    with pytest.raises(ZemaxError):readback(r['text'],request(),r['grid']|dict(values=list(zip(*r['grid']['values']))))



def test_radius_curvature_alias_is_not_an_independent_pair():
    with pytest.raises(ValidationError):request(x=dict(surface=1,parameter='Radius',start=2,stop=6),y=dict(surface=1,parameter='Curvature',start=1,stop=3))


@pytest.mark.parametrize('axis',[
    dict(category='System',parameter='Pressure',start=-1,stop=1),
    dict(category='System',parameter='Wavelength',start=.4,stop=.6),
    dict(category='System',parameter='Temperature',surface=1,start=10,stop=20),
    dict(category='Surface',parameter='Pressure',surface=1,start=1,stop=2),
    dict(category='System',parameter='Temperature',selection=1,start=10,stop=20),
])
def test_system_axis_constraints(axis):
    with pytest.raises(ValidationError):request(x=axis)


def test_indexed_system_axes_use_distinct_physical_variables():
    axis=dict(category='System',parameter='XField',selection=1,start=-1,stop=1,samples=3)
    with pytest.raises(ValidationError):request(x=axis,y=axis)
    assert request(x=axis,y=axis|dict(selection=2)).y.selection==2
    assert request(x=axis,y=axis|dict(parameter='YField')).y.parameter=='YField'


def system_grid_fixture():
    q=request(x=dict(surface=1,parameter='Radius',start=20,stop=40,samples=5),
              y=dict(category='System',parameter='Wavelength',selection=2,start=.45,stop=.65,samples=3),
              operand='CVVA',last_surface=None)
    text=('Independent Variable X: Radius mm Surface 1\n'
          'Independent Variable Y: Wavelength 2\n'
          'Dependent Variable Z: CVVA, Surface=1\n'
          'X - Range: 20 - 40\nX - Sampling: 5\n'
          'Y - Range: 0.45 - 0.65\nY - Sampling: 3\n')
    grid=dict(nx=5,ny=3,min_x=20,min_y=.45,dx=5,dy=.1,values=[[1/x for x in [20,25,30,35,40]]for _ in range(3)])
    return q,text,grid


def test_mixed_system_grid_native_readback():
    q,text,grid=system_grid_fixture()
    actual=readback(text,q,grid)
    assert 'Wavelength 2'in actual['Y']['axis']and actual['X']['samples']==5


@pytest.mark.parametrize('old,new',[
    ('Wavelength 2','Wavelength 1'),('Wavelength 2','Y Field 2'),
    ('Surface 1','Surface 2'),('Y - Sampling: 3','Y - Sampling: 5'),
    ('Y - Range: 0.45 - 0.65','Y - Range: 0.45 - 0.75'),
])
def test_mixed_system_grid_rejects_unadopted_identity(old,new):
    q,text,grid=system_grid_fixture()
    with pytest.raises(ZemaxError)as error:readback(text.replace(old,new),q,grid)
    assert error.value.code=='SETTING_REJECTED'


def test_configuration_and_surface_axes_cannot_scan_the_same_property(monkeypatch):
    from types import SimpleNamespace as NS
    from zemax_mcp import universal_grid as module
    cell=NS(IsActive=True,IsReadOnly=False,Solve='Fixed',DataType='Double')
    row=NS(Type='THIC',Param1=1,Param1Enabled=True,Param2Enabled=False,Param3Enabled=False,GetOperandCell=lambda c:cell)
    source=NS(MCE=NS(CurrentConfiguration=2,NumberOfConfigurations=2,NumberOfOperands=3,GetOperandAt=lambda i:row),SystemData=NS(Units=NS(LensUnits='Millimeters')))
    backend=NS(system=source,_require_sequential=lambda:None,_row=lambda i:None)
    monkeypatch.setattr(module,'new_analysis',lambda *a:pytest.fail('duplicate physical axes opened native analysis'))
    q=request(y=dict(category='Configuration',configuration=2,operand_row=3,parameter='THIC',start=2,stop=4))
    with pytest.raises(ZemaxError)as error:module.run(backend,q)
    assert error.value.code=='INVALID_ARGUMENT'


def test_inactive_system_axis_is_rejected_before_opening_native(tmp_path,monkeypatch):
    from types import SimpleNamespace as NS
    from zemax_mcp import universal_grid as module
    source=NS(SystemData=NS(Units=NS(LensUnits='Millimeters'),Aperture=NS(ApodizationType='Uniform')))
    backend=NS(system=source,_require_sequential=lambda:None,_row=lambda i:None)
    monkeypatch.setattr(module,'new_analysis',lambda *args:pytest.fail('inactive axis opened native analysis'))
    with pytest.raises(ZemaxError)as error:module.run(backend,request(y=dict(category='System',parameter='ApodizationFactor',start=1,stop=3)))
    assert error.value.code=='INACTIVE_SETTING'



def test_native_universal_internal_isolation_uses_primary_owner(tmp_path,monkeypatch):
    from types import SimpleNamespace as NS
    from zemax_mcp import universal_grid as module
    def forbidden():pytest.fail('Universal2D opened extra native system')
    native_settings=NS(SaveTo=lambda p:True,ModifySettings=lambda *a:True,LoadFrom=lambda p:True)
    tool=NS(GetSettings=lambda:native_settings)
    source=NS(CopySystem=forbidden,SystemID=17,SystemData=NS(Units=NS(LensUnits='Millimeters')),MCE=NS(CurrentConfiguration=1))
    backend=NS(system=source,native=None,directory=tmp_path,_require_sequential=lambda:None,_row=lambda i:None,_start_task=lambda kind,tool,settings,**kw:settings)
    monkeypatch.setattr(module,'new_analysis',lambda owner,kind:tool)
    result=module.run(backend,request())
    assert result['source_system_id']==result['analysis_system_id']==17
    assert 'native UniversalPlot internal'in result['isolation']
