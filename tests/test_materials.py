"""Material identity, native selector/readback, table extraction and ownership."""
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp import materials as ma
from zemax_mcp.material_models import MaterialProperties
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('values,catalog_name,expected',[
    (['SCHOTT.AGF'],'schott','SCHOTT.AGF'),
    (['SCHOTT'],'SCHOTT.AGF','SCHOTT'),
    (['SCHOTT.AGF'],'SCHOTT.AGF','SCHOTT.AGF'),
])
def test_native_catalog_filename_and_stem_identity(values,catalog_name,expected):
    assert ma.choose_catalog(values,catalog_name)==expected

@pytest.mark.parametrize('values,catalog_name',[
    (['SCHOTT','SCHOTT.AGF'],'SCHOTT'),
    (['SCHOTT.AGF'],'../SCHOTT'),
    (['SCHOTT.AGF'],'SCHOTT.AGF.AGF'),
])
def test_catalog_alias_ambiguity_and_invalid_names(values,catalog_name):
    with pytest.raises(ZemaxError) as caught:ma.choose_catalog(values,catalog_name)
    assert caught.value.code=='INVALID_RESOURCE'

@pytest.mark.parametrize('change',[
    dict(glasses=[]),dict(glasses=['A']*5),dict(glasses=['A','a']),dict(thickness_mm=0),
    dict(minimum_wavelength_um=0,maximum_wavelength_um=.7),dict(minimum_wavelength_um=.7,maximum_wavelength_um=.4),
    dict(minimum_transmission=1,maximum_transmission=1),dict(minimum_transmission=-1),dict(thickness_mm=float('nan')),
    dict(catalog=''),dict(surface=1),
])
def test_invalid_transmission_request(change):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',**{**dict(catalog='C',glasses=['A']),**change}))

@pytest.mark.parametrize('bounds',[(0,0),(.4,.7)])
def test_transmission_request_roundtrip(bounds):
    q=RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',catalog='C',glasses=['A'],minimum_wavelength_um=bounds[0],maximum_wavelength_um=bounds[1]))
    assert RunAnalysis.model_validate(q.model_dump())==q

class Catalog:
    SelectedCatalog='';SelectedMaterial='';NumberOfFitCoefficients=2
    def GetAllCatalogs(self):return ['C']
    def GetAllMaterials(self):return ['A','B']
    def GetCoefficientName(self,i):return ['K1','L1'][i]
    def GetFitCoefficient(self,i):return [1.2,.03][i]
    def GetInternalTransmissionData(self):return NS(NumberOfPoints=1,GetDataPoint=lambda i:NS(Wavelength=.55,Transmission=.98,Thickness=25))
    def GetInternalBirefringenceData(self):return NS(NumberOfPoints=0)
class Backend(ma.MaterialsMixin):
    def __init__(self,tool=None):
        self.tool=tool or Catalog();self.closed=[];self.close_ok=True
        catalogs=NS(GetCatalogsInUse=lambda:['C'],GetMaterialsInCatalog=lambda c:['A','B'])
        self.system=NS(Tools=NS(OpenMaterialsCatalog=lambda:self.tool),SystemData=NS(MaterialCatalogs=catalogs))
    def _require_work(self):pass
    def _require_sequential(self):pass
    def _close_task_native(self,holder):self.closed.append(holder['native']);holder['cleanup_warnings']=['close failed'];return self.close_ok

@pytest.fixture
def readback(monkeypatch):
    monkeypatch.setattr(ma,'scalar_settings',lambda obj:dict(SelectedCatalog=obj.SelectedCatalog,SelectedMaterial=obj.SelectedMaterial))


def test_material_data_and_close_without_save(readback):
    b=Backend();result=b.get_material_properties(MaterialProperties(catalog='c',material='a'))
    assert result['catalog']=='C' and result['material']=='A' and result['coefficients'][0]['value']==1.2
    assert result['internal_transmission']==[dict(native_index=0,wavelength_um=.55,transmission=.98,thickness_mm=25)]
    assert b.closed==[b.tool] and result['birefringence']==[]


def test_catalog_scalar_metadata_uses_native_implementation(monkeypatch):
    b=Backend();implementation=NS(SelectedCatalog='C',SelectedMaterial='A')
    b.tool.__implementation__=implementation
    seen=[]
    monkeypatch.setattr(ma,'scalar_settings',lambda obj:seen.append(obj) or {})
    b.get_material_properties(MaterialProperties(catalog='C',material='A'))
    assert seen==[implementation] and b.closed==[b.tool]

def test_optional_tables_are_not_opened(readback):
    b=Backend();b.tool.GetInternalTransmissionData=lambda:(_ for _ in ()).throw(AssertionError('table requested'))
    result=b.get_material_properties(MaterialProperties(catalog='C',material='A',include_internal_transmission=False,include_birefringence=False))
    assert 'internal_transmission'not in result and 'birefringence'not in result and b.closed==[b.tool]

@pytest.mark.parametrize('q',[dict(catalog='missing',material='A'),dict(catalog='C',material='missing')])
def test_missing_identity_closes_tool(q):
    b=Backend()
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(**q))
    assert exc.value.code=='INVALID_RESOURCE' and b.closed==[b.tool]

def test_read_failure_and_close_failure_preserve_original():
    b=Backend();b.close_ok=False
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(catalog='missing',material='A'))
    assert exc.value.code=='INVALID_RESOURCE' and exc.value.details['cleanup_warnings']==['close failed']

def test_successful_read_with_close_failure_is_error(readback):
    b=Backend();b.close_ok=False
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(catalog='C',material='A'))
    assert exc.value.code=='CLEANUP_FAILED'

def test_duplicate_native_material_identity_rejected(readback):
    b=Backend();b.tool.GetAllMaterials=lambda:['A','a']
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(catalog='C',material='a'))
    assert exc.value.code=='INVALID_RESOURCE' and len(b.closed)==1

def test_invalid_coefficient_closes(readback):
    b=Backend();b.tool.GetFitCoefficient=lambda i:float('nan')
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(catalog='C',material='A'))
    assert exc.value.code=='INVALID_RESULT_DATA' and len(b.closed)==1

@pytest.mark.parametrize('table',[
    NS(NumberOfPoints=-1),NS(NumberOfPoints=100001),
    NS(NumberOfPoints=1,GetDataPoint=lambda i:NS(Wavelength=float('nan'))),
])
def test_invalid_tables(table):
    with pytest.raises(ZemaxError):ma.material_table(table,dict(wave='Wavelength'))

def test_resolve_in_use_catalog_and_ambiguity():
    b=Backend();q=RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',catalog='c',glasses=['a'])).request
    assert ma.resolve_glasses(b,q)==('C',['A'])
    b.system.SystemData.MaterialCatalogs.GetCatalogsInUse=lambda:['C','D']
    with pytest.raises(ZemaxError)as exc:ma.resolve_glasses(b,q)
    assert exc.value.code=='AMBIGUOUS_MATERIAL'

def test_material_transmission_settings_clear_unused_slots(monkeypatch):
    b=Backend();b.native=None;s=NS(Glass2='old',Glass3='old',Glass4='old')
    monkeypatch.setattr(ma,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(ma,'check',lambda n,s,k,v:ma.check_setting_value(k,v,getattr(s,k)))
    monkeypatch.setattr(ma,'scalar_settings',lambda s:dict(vars(s)))
    q=RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',catalog='C',glasses=['A'],thickness_mm=5)).request
    actual=ma.configure_transmission(b,s,q)
    assert s.Glass1=='A' and s.Glass2==s.Glass3==s.Glass4=='' and s.Thickness==5
    assert actual['units']['thickness']=='millimeters'

def test_transmission_configuration_failure_closes_analysis(monkeypatch):
    b=Backend();tool=NS(GetSettings=lambda:None)
    monkeypatch.setattr(ma,'new_analysis',lambda b,k:tool)
    monkeypatch.setattr(ma,'configure_transmission',lambda *args:(_ for _ in ()).throw(RuntimeError('settings failed')))
    q=RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',catalog='C',glasses=['A'])).request
    with pytest.raises(RuntimeError,match='settings failed'):ma.run_internal_transmission(b,q)
    assert b.closed==[tool]

def test_material_analysis_dispatch(monkeypatch):
    from zemax_mcp.analyses import AnalysesMixin
    monkeypatch.setattr(ma,'run_internal_transmission',lambda b,q:q.kind)
    assert AnalysesMixin().run_analysis(RunAnalysis(request=dict(kind='internal_transmission_vs_wavelength',catalog='C',glasses=['A'])))=='internal_transmission_vs_wavelength'

def test_native_table_page_keeps_native_indices():
    table=NS(NumberOfPoints=4,GetDataPoint=lambda i:NS(Wavelength=i+.5))
    assert ma.material_table(table,dict(wave='Wavelength'),start=1,count=2)==[dict(native_index=1,wave=1.5),dict(native_index=2,wave=2.5)]
    assert ma.table_page(table,MaterialProperties(catalog='C',material='A',table_start=1,table_count=2))['next_start']==3

@pytest.mark.parametrize('changes',[dict(table_count=0),dict(table_start=-1),dict(table_count=1001)])
def test_invalid_native_table_page(changes):
    with pytest.raises(ValidationError):MaterialProperties(catalog='C',material='A',**changes)

def test_raw_native_error_retains_cleanup_failure():
    b=Backend();b.close_ok=False
    b.tool.GetAllCatalogs=lambda:(_ for _ in ()).throw(RuntimeError('original catalog error'))
    with pytest.raises(ZemaxError)as exc:b.get_material_properties(MaterialProperties(catalog='C',material='A'))
    assert exc.value.code=='NATIVE_ERROR' and str(exc.value)=='original catalog error'
    assert exc.value.details['type']=='RuntimeError' and exc.value.details['cleanup_warnings']==['close failed']
