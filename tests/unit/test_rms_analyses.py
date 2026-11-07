import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp.rms_analyses import map_rms_grid
from zemax_mcp.rms_analyses import rms_map_settings

@pytest.mark.parametrize('payload',[dict(kind='rms_vs_field',rings=3),dict(kind='rms_vs_focus',method='GaussQuad',sampling='S_64x64'),dict(kind='rms_vs_field',field_density=21),dict(kind='rms_vs_focus',maximum_focus=-1),dict(kind='rms_vs_field',wavelength=0,data_type='StrehlRatio'),dict(kind='through_focus_spot',delta_focus_um=0)])
def test_invalid_rms_requests(payload):
    with pytest.raises(ValidationError):RunAnalysis(request=payload)

@pytest.mark.parametrize('kind',['rms_vs_field','rms_vs_focus','through_focus_spot'])
def test_serialized_defaults_survive_worker_validation(kind):
    request=RunAnalysis(request=dict(kind=kind))
    assert RunAnalysis.model_validate(request.model_dump())==request


@pytest.mark.parametrize('payload', [
    dict(kind='rms_field_map',x_field_size=0),
    dict(kind='rms_field_map',y_field_sampling=102),
    dict(kind='rms_field_map',wavelength=0,data_type='StrehlRatio'),
    dict(kind='rms_field_map',method='GaussQuad',sampling='S_64x64'),
    dict(kind='rms_field_map',method='RectArray',rings=4),
])
def test_invalid_rms_field_map_requests(payload):
    with pytest.raises(ValidationError):
        RunAnalysis(request=payload)


def test_rms_field_map_request_defaults_and_worker_roundtrip():
    request=RunAnalysis(request=dict(kind='rms_field_map',x_field_sampling=7,y_field_sampling=5))
    assert request.request.field==1
    assert request.request.wavelength==1
    assert request.request.x_field_sampling==7
    assert request.request.y_field_sampling==5
    assert RunAnalysis.model_validate(request.model_dump())==request


def test_rms_field_map_grid_metadata_and_units():
    grid=dict(nx=7,ny=5,min_x=-4.,min_y=-2.,dx=8/6,dy=1.,values=[[1.0]*7 for _ in range(5)])
    request=dict(kind='rms_field_map',field=2,wavelength=1,data_type='Wavefront',
        x_field_sampling=7,y_field_sampling=5,x_field_size=4.,y_field_size=2.)
    result=map_rms_grid(grid,request,dict(field_type='Angle',fields=[dict(number=2,x=3.,y=10.)]),'Millimeters')
    assert result['array_order']=='values[y][x]'
    assert result['x_unit']==result['y_unit']=='degrees'
    assert result['value_unit']=='waves'
    assert result['x_field_size']==4. and result['y_field_size']==2.
    assert len(result['values'])==5 and len(result['values'][0])==7
    assert result['min_x']==-1 and result['min_y']==8
    assert result['field_center']==dict(x=3.,y=10.)
    assert result['native_axes']['min_x']==-4


def test_rms_field_map_rejects_grid_shape_mismatch():
    grid=dict(nx=5,ny=7,values=[[1.0]*5 for _ in range(7)])
    request=dict(data_type='SpotRadius',x_field_sampling=7,y_field_sampling=5)
    with pytest.raises(ZemaxError) as exc:
        map_rms_grid(grid,request,dict(field_type='Object'),'Millimeters')
    assert exc.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('corrupt_final_state',[False,True])
def test_rms_field_map_writes_and_reads_back_native_settings(monkeypatch,corrupt_final_state):
    import zemax_mcp.rms_analyses as module

    class NativeEnum:
        def __init__(self,value):self.value=value
        def Equals(self,other):return isinstance(other,NativeEnum) and self.value==other.value

    class TypeInfo:
        def __init__(self,owner):self.owner=owner
        def GetProperty(self,name):return self.owner.properties[name]

    class PropertyType:
        def __init__(self,kind):
            self.IsEnum=kind=='enum'
            self.FullName={'bool':'System.Boolean','int':'System.Int32','float':'System.Double'}.get(kind,'')

    class Property:
        CanWrite=True
        def __init__(self,kind):self.PropertyType=PropertyType(kind)

    class Settings:
        def __setattr__(self,name,value):
            object.__setattr__(self,name,value)
            if name=='PlotScale' and corrupt_final_state:
                object.__setattr__(self,'RayDensity',NativeEnum('RayDens_1'))
        def __init__(self):
            enums=('Data','MethodType','RayDensity','ReferTo','ShowAs')
            booleans=('UsePolarization','RemoveVignettingFactors')
            integers=('X_FieldSampling','Y_FieldSampling')
            floats=('X_FieldSize','Y_FieldSize','PlotScale')
            self.properties={name:Property('enum') for name in enums}
            self.properties.update({name:Property('bool') for name in booleans})
            self.properties.update({name:Property('int') for name in integers})
            self.properties.update({name:Property('float') for name in floats})
        def GetType(self):return TypeInfo(self)

    class Native:
        def enum(self,kind,value):return NativeEnum(value)
        def set_enum(self,obj,name,value):setattr(obj,name,NativeEnum(value))

    monkeypatch.setattr(module,'native_setting',lambda native,obj,name,value:setattr(obj,name,value) if name not in {'Data','MethodType','RayDensity','ReferTo','ShowAs'} else native.set_enum(obj,name,value))
    settings=Settings()
    request=RunAnalysis(request=dict(kind='rms_field_map',data_type='StrehlRatio',method='GaussQuad',rings=5,
        x_field_sampling=7,y_field_sampling=5,x_field_size=4,y_field_size=2)).request
    if corrupt_final_state:
        with pytest.raises(ZemaxError)as exc:rms_map_settings(Native(),settings,request)
        assert exc.value.code=='SETTING_REJECTED' and exc.value.details['setting']=='RayDensity'
        return
    rms_map_settings(Native(),settings,request)
    assert settings.Data.Equals(NativeEnum('StrehlRation'))
    assert settings.MethodType.Equals(NativeEnum('GaussQuad'))
    assert settings.RayDensity.Equals(NativeEnum('RayDens_5'))
    assert settings.X_FieldSampling==7 and settings.Y_FieldSampling==5
    assert settings.X_FieldSize==4 and settings.Y_FieldSize==2


def test_rms_map_rejects_unavailable_auxiliary_line():
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='rms_field_map',show_diffraction_limit=True))


@pytest.mark.parametrize('axis',['x_field_sampling','y_field_sampling'])
@pytest.mark.parametrize('count',[2,3,4])
def test_rms_map_rejects_native_minimum_grid_clamp(axis,count):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='rms_field_map',**{axis:count}))


def test_rms_map_missing_reference_metadata_preserves_result_error():
    grid=dict(nx=2,ny=2,values=[[0.,0.],[0.,0.]])
    request=dict(field=1,x_field_sampling=2,y_field_sampling=2,data_type='SpotRadius')
    with pytest.raises(ZemaxError)as exc:map_rms_grid(grid,request,dict(field_type='Angle'),'Millimeters')
    assert exc.value.code=='INVALID_RESULT_DATA' and exc.value.details['field']==1


@pytest.mark.parametrize('lens,scale',[('Millimeters',1000.),('Centimeters',10000.),('Meters',1e6),('Inches',25400.)])
def test_rms_map_spot_native_length_to_micrometers(lens,scale):
    grid=dict(nx=2,ny=2,min_x=-1.,min_y=-1.,dx=2.,dy=2.,values=[[.01,None],[.02,.03]])
    request=dict(kind='rms_field_map',field=1,wavelength=1,data_type='Spot_X',
        x_field_sampling=2,y_field_sampling=2,x_field_size=1.,y_field_size=1.)
    map_rms_grid(grid,request,dict(field_type='Angle',fields=[dict(number=1,x=0,y=0)]),lens)
    assert grid['values']==[[.01*scale,None],[.02*scale,.03*scale]]
    assert grid['native_value_unit']==lens and grid['native_to_value_scale']==scale
