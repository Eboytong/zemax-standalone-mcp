import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.gaussian_beams import native_arguments


@pytest.mark.parametrize('kind',['paraxial_gaussian_beam','skew_gaussian_beam'])
def test_gaussian_defaults_and_typed_roundtrip(kind):
    q=RunAnalysis(request=dict(kind=kind))
    assert q.request.orientation=='Both' and q.request.wavelength==1
    assert RunAnalysis.model_validate(q.model_dump())==q


@pytest.mark.parametrize('patch',[
    dict(kind='paraxial_gaussian_beam',m2=.5),dict(kind='paraxial_gaussian_beam',waist_radius=0),
    dict(kind='paraxial_gaussian_beam',surface_start=3,surface_end=2),
    dict(kind='skew_gaussian_beam',start_surface=3,end_surface=2),
    dict(kind='skew_gaussian_beam',m2=2),dict(kind='skew_gaussian_beam',field=0),
    dict(kind='skew_gaussian_beam',waist_radius_y=float('nan'))])
def test_gaussian_rejects_invalid_and_type_specific_arguments(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=patch)


def test_gaussian_native_parameter_identity_and_signed_skew_direction():
    p=RunAnalysis(request=dict(kind='paraxial_gaussian_beam',waist_radius=.1,surface_1_to_waist=-5,m2=4)).request
    assert native_arguments(p,3,'X')==[3,1,1,.1,-5,4,0,0]
    q=RunAnalysis(request=dict(kind='skew_gaussian_beam',start_surface=2,field=3,
                              waist_radius_x=.1,waist_radius_y=.2,start_surface_to_waist=5)).request
    assert native_arguments(q,4,'X')==[2,4,1,3,5,-.1,0,0]
    assert native_arguments(q,4,'Y')==[2,4,1,3,5,.2,0,0]


from types import SimpleNamespace as NS
from zemax_mcp.gaussian_beams import run_gaussian
from zemax_mcp.errors import ZemaxError


def gaussian_fake(value):
    task=dict(context=dict(lens_units='Millimeters',configuration=1),rows=[])
    def query(code,*args):
        if isinstance(value,Exception):raise value
        return value if code=='GBPS' else 1.
    def composite(kind,settings,factory):
        for _ in factory(task):pass
        return task
    b=NS(system=NS(LDE=NS(NumberOfSurfaces=3),MFE=NS(GetOperandValue=query),
                   SystemData=NS(Wavelengths=NS(NumberOfWavelengths=2),Fields=NS(NumberOfFields=3))),
         native=NS(enum=lambda owner,code:code,api=NS(Editors=NS(MFE=NS(MeritOperandType=object())))),
         _require_sequential=lambda:None,_require_work=lambda:None,_cancel_boundary=lambda task:None,
         _composite=composite)
    return b,task


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0.,-1.])
def test_gaussian_invalid_native_value_has_source_and_no_partial_row(value):
    b,t=gaussian_fake(value)
    with pytest.raises(ZemaxError) as exc:
        run_gaussian(b,RunAnalysis(request=dict(kind='paraxial_gaussian_beam')).request)
    assert exc.value.code=='INVALID_RESULT_DATA' and not t['rows']
    assert exc.value.details


def test_gaussian_preserves_native_query_failure_identity():
    b,t=gaussian_fake(RuntimeError('native-license-test'))
    with pytest.raises(ZemaxError) as exc:
        run_gaussian(b,RunAnalysis(request=dict(kind='paraxial_gaussian_beam')).request)
    assert exc.value.code=='NATIVE_ERROR'
    assert exc.value.details['operand']=='GBPD'
    assert exc.value.details['native_exception']=='native-license-test'
    assert exc.value.details['native_exception_type']=='RuntimeError'
    assert exc.value.details['arguments']==[1,1,1.,.05,0,1,0.,0.]
    assert not t['rows']


def test_gaussian_rejects_output_surface_out_of_model_before_query():
    b,t=gaussian_fake(1.)
    with pytest.raises(ZemaxError) as exc:
        run_gaussian(b,RunAnalysis(request=dict(kind='paraxial_gaussian_beam',surface_end=3)).request)
    assert exc.value.code=='INDEX_OUT_OF_RANGE' and not t['rows']
