from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.errors import ZemaxError
from zemax_mcp.material_models import MaterialProperties
from tests.unit.test_materials import Backend, readback


@pytest.mark.parametrize('sample',[
    {'wavelength_um':0},{'wavelength_um':.55,'environment_pressure_atm':-1},
    {'wavelength_um':.55,'material_temperature_c':-273.15},
    {'wavelength_um':.55,'environment_temperature_c':float('inf')},
    {'wavelength_um':.55,'delta_temperature_c':0},
])
def test_star_material_sample_units_and_limits(sample):
    with pytest.raises(ValidationError):
        MaterialProperties(catalog='C',material='A',star_samples=[sample])


def setup_backend():
    b=Backend();b._require_star=lambda:None;b.calls=[]
    def refractive(*args): b.calls.append(('index',args));return 1.5
    def dndt(*args): b.calls.append(('dndt',args));return -1e-6
    b.system.STARSubsystem=N(Materials=N(GetRefractiveIndex=refractive,GetDNDT=dndt))
    return b


def test_star_material_parameter_order_and_canonical_identity(readback):
    b=setup_backend()
    sample=dict(wavelength_um=.6328,environment_pressure_atm=.9,environment_temperature_c=18,
                material_pressure_atm=1.2,material_temperature_c=35,delta_temperature_c=.1)
    q=MaterialProperties(catalog='c',material='a',star_samples=[sample])
    assert MaterialProperties.model_validate(q.model_dump())==q
    result=b.get_material_properties(q)['star_samples']
    assert b.calls==[('index',('C','A',.6328,.9,18.,1.2,35.)),
                     ('dndt',('C','A',.6328,.9,18.,1.2,35.,.1))]
    assert result['rows'][0]['dn_dt']==-1e-6
    assert result['rows'][0]['material_temperature_c']==35
    assert b.closed==[b.tool]


def test_material_utility_availability_is_decided_by_native_getter(readback):
    b=setup_backend()
    b.system.STARSubsystem.Materials.GetRefractiveIndex=lambda *args:(_ for _ in ()).throw(RuntimeError('native feature unavailable'))
    with pytest.raises(ZemaxError) as exc:
        b.get_material_properties(MaterialProperties(catalog='C',material='A',star_samples=[dict(wavelength_um=.55)]))
    assert exc.value.code=='STAR_MATERIAL_ERROR'
    assert 'native feature unavailable' in str(exc.value)
    assert b.closed==[b.tool] and b.calls==[]


@pytest.mark.parametrize('value',[0.,float('nan'),float('inf')])
def test_invalid_native_index_closes_catalog(readback,value):
    b=setup_backend();b.system.STARSubsystem.Materials.GetRefractiveIndex=lambda *args:value
    with pytest.raises(ZemaxError) as exc:
        b.get_material_properties(MaterialProperties(catalog='C',material='A',star_samples=[dict(wavelength_um=.55)]))
    assert exc.value.code=='INVALID_RESULT_DATA' and b.closed==[b.tool]


def test_dndt_error_preserves_method_conditions_and_close_warning(readback):
    b=setup_backend();b.close_ok=False
    b.system.STARSubsystem.Materials.GetDNDT=lambda *args:(_ for _ in ()).throw(RuntimeError('native thermal error'))
    with pytest.raises(ZemaxError) as exc:
        b.get_material_properties(MaterialProperties(catalog='C',material='A',star_samples=[dict(wavelength_um=.55)]))
    assert exc.value.code=='STAR_MATERIAL_ERROR'
    assert exc.value.details['native_method']=='GetDNDT'
    assert exc.value.details['conditions']['wavelength_um']==.55
    assert exc.value.details['cleanup_warnings']==['close failed'] and b.closed==[b.tool]
