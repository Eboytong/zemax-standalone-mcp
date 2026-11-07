"""Bounded scalar detector regions preserve global indices and partial-sum scope."""
from types import SimpleNamespace as NS
import json
import pytest
from pydantic import ValidationError
from zemax_mcp.nsc_models import DetectorRead
from zemax_mcp.detector_regions import read_region,axis_region
from zemax_mcp.errors import ZemaxError

@pytest.fixture
def backend(tmp_path):
    calls=[]
    def read(detector,pixel,kind,value):calls.append((detector,pixel,kind));return True,float(pixel)
    units=NS(LensUnits='Millimeters',SourceUnits='Watts',SourceUnitPrefix='None',AnalysisUnits='WattsPerSquareCentimeter',AnalysisUnitPrefix='None')
    return NS(directory=tmp_path,system=NS(NCE=NS(GetDetectorData=read),SystemData=NS(Units=units)),calls=calls,context=lambda:dict(model_revision=3),_detector_provenance=lambda n:dict(history_known=False,complete=False))

def row(volume=False):
    return NS(Type='DetectorVolume'if volume else'DetectorRectangle',ObjectData=NS(DataType=0,NumberXPixels=200,NumberYPixels=300,NumberZPixels=400,XHalfWidth=2,YHalfWidth=3,ZHalfWidth=4))

def request(**kw):return DetectorRead(detector=1,read_mode='region',**kw)

@pytest.mark.parametrize('volume',[False,True])
def test_only_requested_cells_native_x_fast(backend,volume):
    q=request(x_start=17,y_start=23,z_start=31 if volume else 0,width=2,height=3,depth=2 if volume else 1)
    result=read_region(backend,q,row(volume))
    z=31 if volume else 0
    expected=1+17+200*(23+300*z)
    assert backend.calls[0]==(1,expected,0) and len(backend.calls)==(12 if volume else 6)
    assert result['values'][0][0][0]==expected if volume else result['values'][0][0]==expected
    assert result['nx']==200 and result['total_flux']is None and result['scope']=='requested region only'
    assert result['region_sum']>0 and result['context']['model_revision']==3
    saved=json.loads(__import__('pathlib').Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
    assert saved['artifact_scope'].startswith('requested region only')

@pytest.mark.parametrize('kind,code',[('flux',0),('absorbed_flux',1),('absorbed_density',2)])
def test_volume_quantity_codes(backend,kind,code):
    result=read_region(backend,request(kind=kind,width=1,height=1),row(True))
    assert backend.calls[0][2]==code
    assert result['region_sum']is None if kind=='absorbed_density'else result['region_sum']==1
    if kind=='absorbed_density':assert result['value_unit']=='Watts/Millimeters^3'

@pytest.mark.parametrize('kind,code',[('flux',0),('irradiance',1),('intensity',2)])
def test_rectangle_quantity_codes(backend,kind,code):
    result=read_region(backend,request(kind=kind,width=1,height=1),row())
    assert backend.calls[0][2]==code
    assert result['value_unit_prefix']=='None'

@pytest.mark.parametrize('kw',[dict(x_start=200),dict(y_start=300),dict(z_start=400)])
def test_region_out_of_bounds_before_native_read(backend,kw):
    with pytest.raises(ZemaxError)as caught:read_region(backend,request(**kw),row(True))
    assert caught.value.code=='INDEX_OUT_OF_RANGE' and backend.calls==[]

@pytest.mark.parametrize('kw',[dict(kind='coherent',coherent_type='Power'),dict(angle_space=True),dict(include_geometry=True),dict(color_channel='radiometric_flux'),dict(z_start=1)])
def test_rectangle_incompatible_options(backend,kw):
    with pytest.raises(ZemaxError):read_region(backend,request(**kw),row())
    assert not backend.calls

def test_unsupported_detector_type(backend):
    r=row();r.Type='DetectorColor'
    with pytest.raises(ZemaxError)as caught:read_region(backend,request(),r)
    assert caught.value.code=='UNSUPPORTED_DETECTOR_DATA'

def test_native_scalar_failure_is_preserved(backend):
    backend.system.NCE.GetDetectorData=lambda *args:(False,99)
    with pytest.raises(ZemaxError)as caught:read_region(backend,request(width=1,height=1),row())
    assert caught.value.code=='DETECTOR_READ_FAILED' and caught.value.details['pixel']==1

def test_nonfinite_data_becomes_null(backend):
    backend.system.NCE.GetDetectorData=lambda *args:(True,float('nan'))
    result=read_region(backend,request(width=1,height=1),row())
    assert result['invalid_count']==1 and result['values']==[[None]]

def test_tail_clipping_and_partial_axes(backend):
    result=read_region(backend,request(x_start=199,y_start=299,width=2,height=3),row())
    assert result['values']==[[60000.]] and result['next_x']is None and result['next_y']is None
    assert result['x_axis']['native_start']==199 and len(result['x_axis']['centers'])==1
    assert result['x_axis']['centers'][0]==pytest.approx(1.99)

def test_native_index_capacity(backend):
    r=row(True);r.ObjectData.NumberXPixels=2147483647
    with pytest.raises(ZemaxError)as caught:read_region(backend,request(),r)
    assert caught.value.code=='UNSUPPORTED_DETECTOR_SIZE' and not backend.calls

def test_keep_existing_full_and_region_limits():
    with pytest.raises(ValidationError):DetectorRead(detector=1,width=101,height=1)
    with pytest.raises(ValidationError):request(width=100,height=100,depth=11)
    assert request(width=1000,height=1).width==1000

def test_invalid_half_width():
    with pytest.raises(ZemaxError)as caught:axis_region('x',0,5,0,1,'Millimeters')
    assert caught.value.code=='INVALID_DETECTOR_DATA'
