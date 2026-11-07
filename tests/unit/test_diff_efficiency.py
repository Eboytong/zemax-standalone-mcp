import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import configure_diff_efficiency


@pytest.mark.parametrize("kind", ["diff_efficiency_2d", "diff_efficiency_angular", "diff_efficiency_chromatic"])
def test_diff_efficiency_request_round_trip(kind):
    request=RunAnalysis(request={"kind":kind})
    assert RunAnalysis.model_validate(request.model_dump())==request
    assert request.request.field==1 and request.request.wavelength==1


@pytest.mark.parametrize("payload", [
    {"kind":"diff_efficiency_2d","sample_size":"S_65"},
    {"kind":"diff_efficiency_angular","sample_size":"S_64x64"},
    {"kind":"diff_efficiency_chromatic","min_angle":0,"max_angle":10},
    {"kind":"diff_efficiency_angular","min_angle":10},
    {"kind":"diff_efficiency_chromatic","min_wavelength":0.7,"max_wavelength":0.4},
    {"kind":"diff_efficiency_2d","min_angle":1,"max_angle":1},
    {"kind":"diff_efficiency_2d","source_position_x":float("nan")},
    {"kind":"diff_efficiency_2d","hologram_object":0},
    {"kind":"diff_efficiency_2d","min_wavelength":0,"max_wavelength":.7},
    {"kind":"diff_efficiency_chromatic","min_wavelength":-.5,"max_wavelength":.7},
])
def test_diff_efficiency_rejects_invalid_or_cross_type_settings(payload):
    with pytest.raises(ValidationError):
        RunAnalysis(request=payload)


def test_diff_efficiency_applies_only_requested_native_settings():
    request=RunAnalysis(request={
        "kind":"diff_efficiency_2d","sample_size":"S_128x128",
        "min_wavelength":0.4,"max_wavelength":0.7,"hologram_object":3,
        "source_position_x":1.25,"source_unpolarized":True,
    }).request
    actual={"MinAngle":2.0}

    def setv(name,value):
        actual[name]=value

    configure_diff_efficiency(request,setv)
    assert actual=={
        "MinAngle":2.0,"SampleSize":"S_128x128","MinWavelength":0.4,
        "MaxWavelength":0.7,"HologramObject":3,"srcPositionX":1.25,
        "srcUnpolarized":True,
    }


@pytest.mark.parametrize('kind,bounds,expected',[
    ('diff_efficiency_angular',dict(min_angle=-5,max_angle=5),dict(MinAngle=-5,MaxAngle=5)),
    ('diff_efficiency_chromatic',dict(min_wavelength=.4,max_wavelength=.7),dict(MinWavelength=.4,MaxWavelength=.7)),
])
def test_line_scans_configure_without_other_scan_fields(kind,bounds,expected):
    request=RunAnalysis(request=dict(kind=kind,**bounds)).request
    actual={}
    configure_diff_efficiency(request,lambda name,value:actual.update({name:value}))
    assert actual==dict(SampleSize='S_65',**expected)


@pytest.mark.parametrize('surface_type,filename,limited',[
    ('Hologram1',None,False),('UserDefined','us_hologram_kogelnik.dll',True),('UserDefined','other.dll',False),
])
def test_diff_efficiency_retains_surface_and_observed_dll_limit(surface_type,filename,limited):
    from types import SimpleNamespace as N
    from zemax_mcp.analyses import diff_efficiency_surface
    row=N(Type=surface_type,Material='',CurrentTypeSettings=N(Filename=filename),GetSurfaceTypeSettings=lambda t:N(Filename='unselected-default.dll'))
    result=diff_efficiency_surface(row)
    assert result['surface_type']==surface_type
    assert bool(result.get('numeric_limitations'))==limited
    if surface_type=='UserDefined':assert result['surface_file']==filename
    if limited:assert result['numeric_limitations'][0]['status']=='reference_deviation_observed'


@pytest.mark.parametrize('mode,code',[
    ('invalid','ANALYSIS_FAILED'),('invalid_no_header','ANALYSIS_FAILED'),('empty','NO_RESULT_DATA'),('empty_no_header','NO_RESULT_DATA'),('null_series','NO_RESULT_DATA'),
])
def test_native_result_failures_preserve_diagnostics(tmp_path,mode,code):
    from types import SimpleNamespace as N
    from zemax_mcp.analyses import AnalysesMixin
    from zemax_mcp.errors import ZemaxError

    def export(path):
        from pathlib import Path
        Path(path).write_text('Requires angular fields\n',encoding='utf-16')
        return True

    result=N(IsValid=not mode.startswith('invalid'),HeaderData=None if mode.endswith('no_header') else N(Lines=['hologram model']),
             NumberOfMessages=1,GetMessageAt=lambda i:N(ErrorCode='Success',Text='Requires angular fields'),
             GetTextFile=export,NumberOfDataSeries=int(mode=='null_series'),NumberOfDataGrids=0,
             GetDataSeries=lambda i:N(XData=None,YData=None))
    backend=AnalysesMixin();backend.directory=tmp_path
    task=dict(task_id='probe',native=N(GetResults=lambda:result),settings=dict(kind='diff_efficiency_2d'))
    with pytest.raises(ZemaxError) as error:
        backend._collect_general_analysis(task)
    assert error.value.code==code
    assert error.value.details['native_messages']==[dict(code='Success',text='Requires angular fields')]
    if not mode.startswith('invalid'):
        assert error.value.details['native_text']==str(tmp_path/'probe_native.txt')

