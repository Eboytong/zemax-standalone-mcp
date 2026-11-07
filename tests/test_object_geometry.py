"""Paged borrowed IFaceData settings, geometry and restoration errors."""
from types import SimpleNamespace as NS
import pytest
from pydantic import ValidationError
from zemax_mcp.nsc_models import ObjectGeometry
from zemax_mcp import object_geometry as og
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('payload',[dict(object=0),dict(start=-1),dict(count=0),dict(count=1001),dict(frame='world'),dict(nsc_surface=0)])
def test_invalid_request(payload):
    with pytest.raises(ValidationError):ObjectGeometry.model_validate(dict(object=1)|payload)

class Faces:
    CurrentFace=1
    ConvertToGlobal=True
    NumberOfFaces=4
    NumberOfVertices=3
    Flux=1.
    Irradiance=2.
    AbsorbedFlux=.1
    AbsorbedIrradiance=.2
    def GetVertex(self,i,*args):
        point=[(0,0,0),(1,0,0),(0,1,0)][i]
        shift=10 if self.ConvertToGlobal else 0
        return True,point[0]+shift,point[1],point[2]+self.CurrentFace
    def GetVertexNormal(self,i,*args):return True,0.,0.,1.

@pytest.fixture
def row():
    data=Faces();return NS(Type='StandardLens',GetFacetedObjectData=lambda:data,data=data)

def test_only_requested_faces_and_state_restoration(row):
    q=ObjectGeometry(object=1,start=2,count=1)
    result=og.read_page(row,q)
    assert result['total']==4 and result['next_start']==3 and len(result['rows'])==1
    assert result['rows'][0]['face']==2 and result['rows'][0]['triangle_area']==.5
    assert result['rows'][0]['vertices']==[[0.,0.,2.],[1.,0.,2.],[0.,1.,2.]]
    assert result['vertices_read']==3 and 'radiometry'not in result['rows'][0]
    assert row.data.CurrentFace==1 and row.data.ConvertToGlobal is True

def test_global_and_raw_radiometry(row):
    result=og.read_page(row,ObjectGeometry(object=1,count=1,frame='global',include_radiometry=True),[[1,0,0],[0,1,0],[0,0,1]])
    assert result['rows'][0]['vertices'][0]==[10.,0.,0.]
    assert result['rows'][0]['radiometry']['AbsorbedFlux']==.1

def test_global_normals_rotate_local_vectors_excluding_native_translation(row):
    def normal(i,*args):return (True,10.,0.,11.)if row.data.ConvertToGlobal else(True,0.,0.,1.)
    row.data.GetVertexNormal=normal
    result=og.read_page(row,ObjectGeometry(object=1,count=1,frame='global'),[[0,0,1],[0,1,0],[-1,0,0]])
    assert result['rows'][0]['vertex_normals']==[[1.,0.,0.]]*3
    assert result['rows'][0]['native_vertex_normals']==[[10.,0.,11.]]*3
    assert row.data.ConvertToGlobal is True and row.data.CurrentFace==1

@pytest.mark.parametrize('start',[0,4])
def test_empty_tail_and_zero_geometry(row,start):
    if start==0:row.data.NumberOfFaces=0
    result=og.read_page(row,ObjectGeometry(object=1,start=start))
    assert result['rows']==[] and result['next_start']is None

def test_out_of_bounds_before_state_change(row):
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1,start=5))
    assert caught.value.code=='INDEX_OUT_OF_RANGE' and row.data.CurrentFace==1

@pytest.mark.parametrize('method',['GetVertex','GetVertexNormal'])
def test_native_read_failure_preserves_face_and_restores(row,method):
    setattr(row.data,method,lambda *args:(False,0,0,0))
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1,start=2))
    assert caught.value.code=='OBJECT_GEOMETRY_READ_FAILED' and caught.value.details['face']==2
    assert row.data.CurrentFace==1 and row.data.ConvertToGlobal is True

def test_nonfinite_geometry_rejected(row):
    row.data.GetVertex=lambda *args:(True,float('nan'),0,0)
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1))
    assert caught.value.code=='INVALID_RESULT_DATA' and row.data.CurrentFace==1

@pytest.mark.parametrize('count',[2,10001])
def test_face_budget(row,count):
    row.data.NumberOfVertices=count
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1))
    assert caught.value.code=='RESULT_TOO_LARGE'

def test_degenerate_triangle(row):
    row.data.GetVertex=lambda *args:(True,0,0,0)
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1))
    assert caught.value.code=='INVALID_RESULT_DATA'

def test_restore_failure_retains_original_and_requires_reconnect(row):
    class Broken(Faces):
        _face=1
        @property
        def CurrentFace(self):return self._face
        @CurrentFace.setter
        def CurrentFace(self,v):
            if v==1:raise RuntimeError('original restore error')
            self._face=v
        def GetVertex(self,*args):raise RuntimeError('original read error')
    row.data=Broken();row.GetFacetedObjectData=lambda:row.data
    backend=NS(_object=lambda n:row,requires_reconnect=False)
    with pytest.raises(ZemaxError)as caught:og.get_object_geometry(backend,ObjectGeometry(object=1,start=2))
    assert caught.value.code=='OBJECT_GEOMETRY_RESTORE_FAILED' and backend.requires_reconnect
    assert caught.value.details['operation_error']['message']=='original read error'
    assert caught.value.details['restore_error']['message']=='original restore error'

def test_missing_face_interface(row):
    row.GetFacetedObjectData=lambda:None
    with pytest.raises(ZemaxError)as caught:og.read_page(row,ObjectGeometry(object=1))
    assert caught.value.code=='OBJECT_GEOMETRY_UNAVAILABLE'

def test_context_units_and_source_conditions(row):
    units=NS(LensUnits='Millimeters',SourceUnits='Watts',SourceUnitPrefix='None',AnalysisUnits='WattsPerSquareCentimeter',AnalysisUnitPrefix='None')
    b=NS(_object=lambda n:row,system=NS(SystemData=NS(Units=units)),context=lambda:dict(model_revision=7))
    result=og.get_object_geometry(b,ObjectGeometry(object=1,count=1,include_radiometry=True))
    assert result['context']['model_revision']==7 and result['area_unit']=='Millimeters^2'
    assert result['radiometry_units']['source_units']=='Watts'
