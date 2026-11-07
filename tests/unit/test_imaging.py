"""Typed imaging settings and complete native result shapes without a license."""
from types import SimpleNamespace as NS
import math
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp import imaging as im
from zemax_mcp.errors import ZemaxError

KINDS=['image_simulation','geometric_image','geometric_bitmap_image','fft_line_edge_spread','geometric_line_edge_spread','extended_source_encircled_energy']

def test_geometric_bitmap_default_settings_preserve_interface_limit():
    q=RunAnalysis(request=dict(kind='geometric_bitmap_image',input_file='point.IMA')).request
    settings=NS(GetType=lambda:NS(FullName='ZOSAPI.Analysis.Settings.AS_Default'))
    with pytest.raises(ZemaxError) as caught:im.configure(None,settings,q)
    assert caught.value.code=='UNSUPPORTED_INTERFACE'
    assert caught.value.details['runtime_settings_type']=='ZOSAPI.Analysis.Settings.AS_Default'
    assert caught.value.details['missing_method']=='GetFileNames'
def payload(kind):
    return dict(kind=kind, **({'input_file':'point.IMA'} if kind in {'image_simulation','geometric_image','geometric_bitmap_image'} else {'image_name':'point.IMA'} if kind=='extended_source_encircled_energy' else {}))

@pytest.mark.parametrize('kind',KINDS)
def test_requests_round_trip(kind):
    q=RunAnalysis(request=payload(kind))
    assert RunAnalysis.model_validate(q.model_dump())==q

@pytest.mark.parametrize('kind,changes',[
    ('image_simulation',dict(field=0)),('image_simulation',dict(wavelength=0)),
    ('image_simulation',dict(psf_x_points=0)),('image_simulation',dict(pixel_size=float('nan'))),
    ('image_simulation',dict(x_pixels=16001)),('image_simulation',dict(rotation_source='90')),
    ('geometric_image',dict(field=0)),('geometric_image',dict(na=1.1)),
    ('geometric_image',dict(rays_x1000=True)),('geometric_image',dict(field_size=-1)),
    ('fft_line_edge_spread',dict(spread='Square')),('fft_line_edge_spread',dict(surface=3)),
    ('geometric_line_edge_spread',dict(use_coherent_psf=True)),
    ('extended_source_encircled_energy',dict(rays_x1000=0)),
])
def test_invalid_typed_requests(kind,changes):
    with pytest.raises(ValidationError):RunAnalysis(request={**payload(kind),**changes})

class Selector:
    def __init__(self,kind):self.kind=kind;self.value=1
    def __getattr__(self,name):
        if name=='Set'+self.kind+'Number':return lambda v:setattr(self,'value',v)
        if name=='Get'+self.kind+'Number':return lambda:self.value
        raise AttributeError(name)

class Settings:
    def __init__(self,kind):
        self.kind=kind;self.Field=Selector('Field');self.Wavelength=Selector('Wavelength');self.Surface=Selector('Surface')
        self.mode=1;self.rejected=None
    def UseColumnRowCenter(self):self.RowColumnNumber=self.NumberOfPixels//2
    def GetInputFileNames(self):return ['point.IMA','color.png']
    def GetFileNames(self):return ['point.IMA']
    def SetWavelengthRGB(self):self.mode='RGB'
    def SetWavelength123(self):self.mode='1+2+3'
    def SetWavelengthNumber(self,n):self.mode=n
    def GetWavelengthRGB(self):return self.mode=='RGB'
    def GetWavelength123(self):return self.mode=='1+2+3'
    def GetWavelengthNumber(self):return self.mode

@pytest.fixture
def adapted(monkeypatch):
    monkeypatch.setattr(im,'scalar_settings',lambda s:dict(Field=s.Field.value))
    def setting(native,s,name,value):
        if name!=s.rejected:setattr(s,name,value)
    monkeypatch.setattr(im,'native_setting',setting)
    monkeypatch.setattr(im,'check',lambda native,s,name,value:im.check_setting_value(name,value,getattr(s,name)))
    monkeypatch.setattr(im,'resource_names',lambda b,kind:['point.IMA'])
    return NS(native=None,system=NS(LDE=NS(NumberOfSurfaces=5)))

@pytest.mark.parametrize('kind',KINDS)
def test_configure_explicit_settings_and_selectors(adapted,kind):
    q=RunAnalysis(request=payload(kind)).request;s=Settings(kind)
    actual=im.configure(adapted,s,q)
    assert actual['requested']['kind']==kind and s.Field.value==q.field
    if kind=='image_simulation':assert s.mode=='RGB' and s.OutputFile==''
    elif kind in {'geometric_image','geometric_bitmap_image'}:assert s.SaveAsBIMFile=='' and s.Surface.value==4
    if kind in im.EXTRA:
        for key,name in im.EXTRA[kind].items():assert getattr(s,name)==getattr(q,key)

@pytest.mark.parametrize('kind',['image_simulation','geometric_image','geometric_bitmap_image'])
def test_resource_case_matching_and_rejection(adapted,kind):
    s=Settings(kind);q=RunAnalysis(request={**payload(kind),'input_file':'POINT.ima'}).request
    assert im.configure(adapted,s,q)['input_resource']=='point.IMA'
    q=RunAnalysis(request={**payload(kind),'input_file':'../point.IMA'}).request
    with pytest.raises(ZemaxError,match='Images'):im.configure(adapted,s,q)

@pytest.mark.parametrize('mode',['RGB','1+2+3',1])
def test_wavelength_selection(adapted,mode):
    q=RunAnalysis(request={**payload('image_simulation'),'wavelength':mode}).request
    s=Settings(q.kind);im.configure(adapted,s,q);assert s.mode==mode

def test_setting_rejected(adapted):
    q=RunAnalysis(request=payload('geometric_image')).request;s=Settings(q.kind);s.rejected='FieldSize';s.FieldSize=9
    with pytest.raises(ZemaxError):im.configure(adapted,s,q)

class Array:
    def __init__(self,rows):self.rows=rows;self.Rank=2
    def GetLength(self,i):return len(self.rows) if i==0 else len(self.rows[0])
    def __getitem__(self,key):return self.rows[key[0]][key[1]]
class Vector:
    Rank=1
    def __init__(self,values):self.values=values
    def __iter__(self):return iter(self.values)
def grid(rows,nx=3,ny=2):
    return NS(Values=Array(rows),Nx=nx,Ny=ny,Dx=.1,Dy=.2,MinX=-1,MinY=-2,Description='test',XLabel='x',YLabel='y',ValueLabel='irradiance')

def test_nonsquare_grid_and_transpose():
    a,meta=im.grid_values(grid([[1,2,3],[4,5,6]]));assert a==[[1,2,3],[4,5,6]] and not meta['transposed']
    a,meta=im.grid_values(grid([[1,4],[2,5],[3,6]]));assert a==[[1,2,3],[4,5,6]] and meta['transposed']

@pytest.mark.parametrize('g',[grid([[1,2],[3,4]]),grid([[1]],0,0),grid([[1]],3000,3000)])
def test_grid_shape_failure(g):
    with pytest.raises(ZemaxError):im.grid_values(g)

def results(**changes):
    base=dict(IsValid=True,HeaderData=NS(Lines=['unit definition']),NumberOfMessages=0,
        GetTextFile=lambda path:False,NumberOfDataGrids=0,NumberOfDataGridsRgb=0,
        NumberOfDataSeries=0,NumberOfDataSeriesRgb=0,NumberOfDataScatterPoints=0,NumberOfDataScatterPointsRgb=0,
        GetDataGrid=lambda i:None,GetDataGridRgb=lambda i:None,GetDataSeries=lambda i:None,
        GetDataSeriesRgb=lambda i:None,GetDataScatterPoint=lambda i:None,GetDataScatterPointRgb=lambda i:None)
    return NS(**{**base,**changes})
def collect(tmp_path,r,kind='geometric_image'):
    return im.collect_imaging(NS(directory=tmp_path,context=lambda:dict(lens_units="Millimeters")),dict(native=NS(GetResults=lambda:r),task_id='test',settings=dict(kind=kind,requested=dict(wavelength='RGB'))))

def test_rgb_grid_channels_and_nonfinite(tmp_path):
    pixel=lambda v:NS(R=v,G=v+1,B=float('nan'))
    r=results(NumberOfDataGridsRgb=1,GetDataGridRgb=lambda i:grid([[pixel(1),pixel(2),pixel(3)],[pixel(4),pixel(5),pixel(6)]]))
    data=collect(tmp_path,r,'image_simulation')
    assert [g['channel'] for g in data['grids']]==list('RGB')
    assert data['grids'][0]['values']==[[1,2,3],[4,5,6]]
    assert data['grids'][2]['invalid_count']==6 and data['grids'][2]['values'][0]==[None]*3
    assert data['native_export_error'] and data['wavelength_conditions']['wavelength_123_channels']['R']==3

def test_scalar_and_rgb_series(tmp_path):
    scalar=NS(XData=NS(Data=Vector([0,1])),YData=NS(Data=Array([[1],[float('nan')]])),SeriesLabels=['S'],Description='curve',XLabel='position')
    rgb=NS(XData=NS(Data=Vector([0,1])),NumberOfRows=2,NumSeries=1,SeriesLabels=['C'],GetYPoint=lambda row,col:NS(R=row,G=row+1,B=row+2),Description='rgb',XLabel='x')
    data=collect(tmp_path,results(NumberOfDataSeries=1,GetDataSeries=lambda i:scalar,NumberOfDataSeriesRgb=1,GetDataSeriesRgb=lambda i:rgb))
    assert len(data['series'])==4 and data['series'][0]['y']==[[1],[None]] and data['series'][3]['y']==[[2],[3]]

def test_scalar_series_without_native_labels(tmp_path):
    series=NS(XData=NS(Data=Vector([0,1])),YData=NS(Data=Array([[.1],[.2]])),SeriesLabels=None,Description='native S',XLabel='angle')
    data=collect(tmp_path,results(NumberOfDataSeries=1,GetDataSeries=lambda i:series))
    assert data['series'][0]['labels']==['column_1']
    assert data['series'][0]['y']==[[.1],[.2]]
    assert data['series'][0]['labels_source'].startswith('generated')

def test_scatter_rows_invalid_and_rgb(tmp_path):
    points=[NS(X=1,Y=2,Value=3),NS(X=math.nan,Y=2,Value=3)]
    s=NS(NumPoints=2,GetPoint=lambda i:points[i],Description='scatter',XLabel='x',YLabel='y',ValueLabel='intensity')
    rgb=NS(NumPoints=1,GetPoint=lambda i:NS(X=0,Y=1,Value=NS(R=1,G=2,B=3)),Description='rgb',XLabel='x',YLabel='y',ValueLabel='rgb')
    data=collect(tmp_path,results(NumberOfDataScatterPoints=1,GetDataScatterPoint=lambda i:s,NumberOfDataScatterPointsRgb=1,GetDataScatterPointRgb=lambda i:rgb))
    assert len(data['rows'])==5 and data['scatter'][0]['invalid_count']==1
    assert len(data['scatter'][0]['points'])==1 and data['scatter'][3]['points'][0]['value']==3

def test_text_error_does_not_drop_structured_results(tmp_path):
    def fail(path):raise RuntimeError('native text failure')
    r=results(GetTextFile=fail,NumberOfDataGrids=1,GetDataGrid=lambda i:grid([[1,2,3],[4,5,6]]))
    assert collect(tmp_path,r)['native_export_error']['message']=='native text failure'

def test_empty_results_preserve_native_error(tmp_path):
    with pytest.raises(ZemaxError)as exc:collect(tmp_path,results())
    assert exc.value.code=='NO_RESULT_DATA' and exc.value.details['native_header']==['unit definition']

def test_invalid_native_result(tmp_path):
    with pytest.raises(ZemaxError)as exc:collect(tmp_path,results(IsValid=False))
    assert exc.value.code=='ANALYSIS_FAILED'

@pytest.mark.parametrize('kind',KINDS)
def test_configure_failure_closes_analysis_once(monkeypatch,kind):
    tool=NS(GetSettings=lambda:None);closed=[]
    b=NS(system=NS(SystemData=NS(Fields=NS(NumberOfFields=3),Wavelengths=NS(NumberOfWavelengths=3)),Analyses=NS(New_Analysis=lambda _:tool)),
        native=NS(api=NS(Analysis=NS(AnalysisIDM=None)),enum=lambda *x:None),_require_sequential=lambda **k:None,_close_task_native=lambda t:closed.append(t['native']))
    monkeypatch.setattr(im,'configure',lambda *args:(_ for _ in ()).throw(RuntimeError('failure')))
    with pytest.raises(RuntimeError,match='failure'):im.run_imaging(b,RunAnalysis(request=payload(kind)).request)
    assert closed==[tool]

def test_native_grid_rows_and_curve_paging(tmp_path):
    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config
    from zemax_mcp.models import TaskResult
    b=Backend(Config(tmp_path,tmp_path/'out'))
    r=collect(tmp_path,results(NumberOfDataGrids=1,GetDataGrid=lambda i:grid([[1,2,3],[4,5,6]])))
    page=b._page_task_result(r,TaskResult(task_id='x',grid=0,x_start=1,width=2,height=1))
    assert page['grid']['values']==[[5,6]] and page['grid']['next_y']==1
    series=dict(series=[dict(series=0,x=[1,2,3],y=[[4],[5],[6]],labels=['C'])],rows=[dict(point=0)])
    page=b._page_task_result(series,TaskResult(task_id='x',series=0,start=1,count=1))
    assert page['series'][0]['x']==[2] and page['series'][0]['y']==[[5]] and page['next_start']==2
    with pytest.raises(ValidationError):TaskResult(task_id='x',series=0,grid=0)

def test_grid_plot_exports(tmp_path):
    from zemax_mcp.plotting import export_image
    q=NS(source='data',item=0,width=400,height=300)
    r=collect(tmp_path,results(NumberOfDataGrids=1,GetDataGrid=lambda i:grid([[1,2,3],[4,5,6]])))
    value=export_image(r,q,tmp_path/'grid.png')
    assert value['image_source']=='data_plot' and (tmp_path/'grid.png').is_file()

def test_extended_diffraction_condition():
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='extended_source_encircled_energy',image_name='point.IMA',data_type='X_Only',multiply_by_diffraction_limit=True))

def test_resource_query_closes_and_prefers_settings_first(monkeypatch):
    closed=[];calls=[]
    tool=NS(GetSettings=lambda:Settings('image_simulation'))
    analyses=NS(New_Analysis=lambda _:(_ for _ in ()).throw(AssertionError('unexpected auto-run')),New_Analysis_SettingsFirst=lambda _:calls.append('settings-first')or tool)
    b=NS(system=NS(Analyses=analyses),native=NS(api=NS(Analysis=NS(AnalysisIDM=None)),enum=lambda *x:None),_close_task_native=lambda t:closed.append(t['native'])or True)
    assert im.resource_names(b,'image_simulation_files')==['point.IMA','color.png']
    assert closed==[tool] and calls==['settings-first']

def test_original_enum_alias_uses_value_equality():
    class Enum:
        def Equals(self,other):return other==7
    setting=NS(GetType=lambda:NS(GetProperty=lambda _:NS(PropertyType=NS(IsEnum=True))),Type=Enum())
    im.check(NS(enum=lambda *args:7),setting,'Type','Alias')
    with pytest.raises(ZemaxError):im.check(NS(enum=lambda *args:8),setting,'Type','Alias')
