import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.spot_topics import configure


@pytest.mark.parametrize('extra',[dict(exaggerate=0),dict(exaggerate=float('inf')),dict(plot_scale=-1),dict(ray_density=0),dict(surface=0),dict(color_rays_by='None'),dict(field=-1)])
def test_full_field_invalid(extra):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='full_field_spot',**extra))


def test_full_field_settings():
    q=RunAnalysis(request=dict(kind='full_field_spot',exaggerate=3,reference='ChiefRay')).request
    writes={};values=configure(q,lambda n,v:writes.update({n:v}))
    assert values==writes and values['Configuration']==1
    assert values['ReferTo']=='ChiefRay' and values['Exaggerate']==3
    assert values['DeltaFocus']==0


def native_result_backend(monkeypatch,radius=.1,spot_present=True):
    from types import SimpleNamespace as NS
    class Selection:
        def __init__(self):self.value=0
        def SetFieldNumber(self,value):self.value=value
        def SetWavelengthNumber(self,value):self.value=value
        def SetSurfaceNumber(self,value):self.value=value
        def GetFieldNumber(self):return self.value
        def GetWavelengthNumber(self):return self.value
        def GetSurfaceNumber(self):return self.value
    settings=NS(Field=Selection(),Wavelength=Selection(),Surface=Selection())
    spot=NS(NumberOfFields=1,GetRMSSpotSizeFor=lambda f,w:radius,
        GetGeoSpotSizeFor=lambda f,w:.2,GetReferenceCoordinate_X_For=lambda f,w:.03,
        GetReferenceCoordinate_Y_For=lambda f,w:-.04)
    native=NS(SpotData=spot if spot_present else None,NumberOfDataSeries=0,NumberOfDataSeriesRgb=0,NumberOfRayData=0,NumberOfMessages=0,NumberOfDataGrids=0,
        NumberOfDataScatterPoints=0,NumberOfDataScatterPointsRgb=0,NumberOfDataGridsRgb=0)
    tool=NS(GetSettings=lambda:settings,GetResults=lambda:native)
    monkeypatch.setattr('zemax_mcp.imaging.new_analysis',lambda b,name:tool)
    monkeypatch.setattr('zemax_mcp.imaging.checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr('zemax_mcp.imaging.check',lambda n,s,k,v:None)
    monkeypatch.setattr('zemax_mcp.analyses.scalar_settings',lambda s:{'DirectionCosines':s.DirectionCosines})
    def start(kind,tool,settings,analysis,collector):return collector(dict(native=tool))
    backend=NS(system=NS(SystemData=NS(Fields=NS(NumberOfFields=2),Wavelengths=NS(NumberOfWavelengths=3)),
        MCE=NS(CurrentConfiguration=1),LDE=NS(NumberOfSurfaces=8)),native=object(),
        _require_sequential=lambda **kw:None,_require_work=lambda:None,_row=lambda i:None,
        _start_task=start,_collect_general_analysis=lambda task:dict(artifacts=[],series=[]))
    return backend


@pytest.mark.parametrize('direction_cosines',[False,True])
def test_full_field_collected_native_metrics_have_matching_coordinate_units(monkeypatch,direction_cosines):
    from zemax_mcp.spot_topics import run_full_field
    q=RunAnalysis(request=dict(kind='full_field_spot',field=1,wavelength=2,
        direction_cosines=direction_cosines)).request
    result=run_full_field(native_result_backend(monkeypatch),q)
    assert result['metrics'][0]['wavelength_selection']==2
    assert result['metrics'][0]['reference_y']==-.04
    assert result['rows']==result['metrics']
    if direction_cosines:
        assert result['radius_unit']==result['reference_coordinate_unit']=='dimensionless'
        assert result['coordinate_quantity']=='direction_cosines'
    else:
        assert result['radius_unit']=='micrometers'and result['reference_coordinate_unit']=='lens units'


@pytest.mark.parametrize('radius',[-.1,float('nan')])
def test_full_field_collector_rejects_invalid_native_radius_with_original_row(monkeypatch,radius):
    import math
    from zemax_mcp.errors import ZemaxError
    from zemax_mcp.spot_topics import run_full_field
    q=RunAnalysis(request=dict(kind='full_field_spot',field=1)).request
    with pytest.raises(ZemaxError)as exc:
        run_full_field(native_result_backend(monkeypatch,radius),q)
    assert exc.value.code=='INVALID_RESULT_DATA'
    value=exc.value.details['row']['rms_radius']
    assert value==radius or math.isnan(value)


def test_full_field_unavailable_report_includes_all_formal_outlet_counts(monkeypatch):
    from zemax_mcp.spot_topics import run_full_field
    from zemax_mcp.errors import ZemaxError
    q=RunAnalysis(request=dict(kind='full_field_spot')).request
    with pytest.raises(ZemaxError)as error:
        run_full_field(native_result_backend(monkeypatch,spot_present=False),q)
    assert error.value.code=='RESULT_UNAVAILABLE'
    counts=error.value.details['native_report']['native_result_counts']
    assert set(counts)=={'NumberOfDataSeries','NumberOfDataSeriesRgb','NumberOfDataGrids','NumberOfDataGridsRgb',
        'NumberOfDataScatterPoints','NumberOfDataScatterPointsRgb','NumberOfRayData','NumberOfMessages'}
    assert set(counts.values())=={0}
