import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.material_index import uses_index
from zemax_mcp.errors import ZemaxError

BASE=dict(kind='dispersion_diagram',catalog='SCHOTT',glasses=['N-BK7'])


def test_default_report_and_selected_formal_index_dispatch():
    assert not uses_index(RunAnalysis(request=dict(kind='dispersion_diagram')).request)
    assert uses_index(RunAnalysis(request=BASE).request)
    assert uses_index(RunAnalysis(request=dict(BASE,method='index')).request)
    with pytest.raises(ZemaxError) as error:
        uses_index(RunAnalysis(request=dict(BASE,method='native')).request)
    assert error.value.code=='UNSUPPORTED_SETTING'


@pytest.mark.parametrize('patch',[
    dict(glasses=[]),dict(glasses=['N-BK7']*5),dict(glasses=['N-BK7','n-bk7']),
    dict(maximum_wavelength_um=.3),dict(minimum_wavelength_um=0),dict(samples=1),dict(samples=2002),
    dict(samples=10.5),dict(temperature_c=30),dict(pressure_atm=0),dict(use_temperature_pressure=True,temperature_c=-273.15),
    dict(use_temperature_pressure=True,pressure_atm=-1),dict(minimum_index=2,maximum_index=1),dict(maximum_index=float('nan'))])
def test_selected_material_boundaries(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=BASE|patch)


@pytest.mark.parametrize('payload',[dict(kind='dispersion_diagram',method='index'),
    dict(kind='dispersion_diagram',samples=10),dict(kind='dispersion_diagram',catalog='SCHOTT')])
def test_selected_contract_requires_unambiguous_material_input(payload):
    with pytest.raises(ValidationError):RunAnalysis(request=payload)


def test_selected_material_contract_round_trip():
    q=RunAnalysis(request=BASE|dict(glasses=['N-BK7','N-F2','N-SF6','N-SF10'],use_temperature_pressure=True,
        temperature_c=30,pressure_atm=.8,samples=2))
    assert RunAnalysis.model_validate(q.model_dump())==q
    default=RunAnalysis(request=dict(kind='dispersion_diagram'))
    assert not uses_index(RunAnalysis.model_validate(default.model_dump()).request)


@pytest.mark.parametrize('failure',['cancel','native','close'])
@pytest.mark.parametrize('kind',['dispersion_diagram','dispersion_vs_wavelength'])
def test_owned_copy_closes_on_cancel_native_failure_and_close_rejection(monkeypatch,failure,kind):
    from types import SimpleNamespace as NS
    from zemax_mcp import material_index as module
    from zemax_mcp.evaluation import Cancelled
    monkeypatch.setattr('zemax_mcp.materials.resolve_glasses',lambda *args:('SCHOTT',['N-BK7']))
    monkeypatch.setattr(module,'set_wavelengths',lambda table,values:values)
    def indices(system,count):
        if failure=='native':raise RuntimeError('controlled GetIndex failure')
        return count,[1.5]*count
    monkeypatch.setattr(module,'read_indices',indices)
    closed=[]
    def close(save):closed.append(save);return failure!='close'
    surface=NS(Material='N-BK7')
    copy=NS(SystemID=2,New=lambda save:None,Close=close,
        SystemData=NS(MaterialCatalogs=NS(GetCatalogsInUse=lambda:['SCHOTT']),
            Environment=NS(AdjustIndexToEnvironment=False,Temperature=20.,Pressure=1.),Wavelengths=object()),
        LDE=NS(GetSurfaceAt=lambda index:surface))
    task=dict(rows=[],context=dict(configuration=1))
    backend=NS(_require_sequential=lambda:None,_require_work=lambda:None,
        get_material_properties=lambda q:dict(properties=dict(MinimumWavelength=.3,MaximumWavelength=2.)),
        system=NS(SystemID=1,CopySystem=lambda:copy),requires_reconnect=False,
        _composite=lambda kind,settings,factory:factory(task),_cancel_boundary=lambda task:None)
    iterator=module.run_material_index(backend,RunAnalysis(request=BASE|dict(kind=kind)).request)
    if failure=='cancel':
        next(iterator)
        with pytest.raises(Cancelled):iterator.throw(Cancelled())
    elif failure=='native':
        with pytest.raises(RuntimeError,match='controlled GetIndex failure'):list(iterator)
    else:
        with pytest.raises(ZemaxError) as caught:list(iterator)
        assert caught.value.code=='RESOURCE_CLOSE_FAILED'
    assert closed==[False]
    assert task['restoration']['analysis_copy_closed']==(failure!='close')
    assert backend.requires_reconnect==(failure=='close')


def test_automatic_catalog_range_and_independent_display_bounds():
    q=RunAnalysis(request=BASE|dict(minimum_wavelength_um=0,maximum_wavelength_um=0,minimum_index=1.4)).request
    assert q.minimum_wavelength_um==q.maximum_wavelength_um==0
    assert q.minimum_index==1.4 and q.maximum_index is None


@pytest.mark.parametrize('contents,code',[(None,'INVALID_RESOURCE'),('0.5 1.5\n0.4 1.6','INVALID_RESOURCE'),('0.4 nan\n0.8 1.5','INVALID_RESOURCE'),('0.4 1.6\n0.8 1.5',None)])
def test_table_glass_resource_preflight(tmp_path,contents,code):
    from types import SimpleNamespace as NS
    from zemax_mcp.material_index import run_material_index
    folder=tmp_path/'Glasscat';folder.mkdir()
    if contents is not None:(folder/'TEST.ZTG').write_text(contents)
    backend=NS(_require_sequential=lambda:None,_require_work=lambda:None,
        native=NS(application=NS(ZemaxDataDir=str(tmp_path))),
        system=NS(SystemData=NS(MaterialCatalogs=NS(GetCatalogsInUse=lambda:['SCHOTT']))),
        _composite=lambda *args:'prepared')
    q=RunAnalysis(request=BASE|dict(glasses=['test.ztg'])).request
    if code:
        with pytest.raises(ZemaxError) as error:run_material_index(backend,q)
        assert error.value.code==code
    else:assert run_material_index(backend,q)=='prepared'
