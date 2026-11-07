import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.nsc_analyses import configure_nsc_surface_sag


def request(**changes):
    return RunAnalysis(request={"kind":"nsc_surface_sag","object_number":3,"face_number":0,**changes}).request


def test_nsc_surface_sag_request_round_trip():
    value=request(sampling="S_129x129",show_as="FalseColor",remove_option="BestFitSphere")
    assert RunAnalysis.model_validate(RunAnalysis(request=value).model_dump()).request==value


@pytest.mark.parametrize("changes",[
    {"object_number":0},{"face_number":-1},{"sampling":"S_64x64"},{"show_as":"HeatMap"},
    {"remove_option":"Sphere"},{"width":0},{"rotation":float("nan")},
    {"keep_zrd":True},{"zrd_filename":"../outside.zrd"},{"zrd_filename":"out.zrd"},
    {"keep_zrd":True,"zrd_filename":"folder\\out.zrd"},{"keep_zrd":True,"zrd_filename":"out.txt"},
    {"contour_format":"one\ntwo"},
])
def test_nsc_surface_sag_rejects_invalid_settings(changes):
    with pytest.raises(ValidationError):request(**changes)


def test_nsc_surface_sag_maps_native_settings_and_output_path():
    q=request(sampling="S_257x257",show_as="Contour",offset=0.2,width=4.5,
              decenter_x=0.1,remove_option="BestFitSphere",best_fit_sphere_option="MinimumRMSWithOffset",
              keep_zrd=True,zrd_filename="surface.zrd")
    actual={}
    values=configure_nsc_surface_sag(q,lambda name,value:actual.__setitem__(name,value),r"C:\outputs\surface.zrd")
    assert actual==values
    assert actual["ObjectNumber"]==3 and actual["FaceNumber"]==0
    assert actual["Sampling"]=="S_257x257" and actual["ShowAs"]=="Contour"
    assert actual["BestFitSphereOption"]=="MinimumRMSWithOffset"
    assert actual["KeepZRD"] is True and actual["ZRDFilename"].endswith("surface.zrd")

@pytest.mark.parametrize('values,code',[([[None]],'NO_RESULT_DATA'),([], 'NO_RESULT_DATA'),([[0.]],None)])
def test_sag_collector_empty_and_finite_samples(tmp_path,monkeypatch,values,code):
    from types import SimpleNamespace as NS
    from zemax_mcp import nsc_analyses as na
    from zemax_mcp.errors import ZemaxError
    settings=NS()
    native=NS(GetSettings=lambda:settings)
    monkeypatch.setattr(na,'new_analysis',lambda *args:native)
    monkeypatch.setattr(na,'checked',lambda n,s,k,v:setattr(s,k,v))
    monkeypatch.setattr(na,'check',lambda *args:None)
    monkeypatch.setattr(na,'scalar_settings',lambda s:vars(s).copy())
    def start(kind,tool,actual,**kwargs):return dict(task_id='test',settings=actual,**kwargs)
    b=NS(directory=tmp_path,native=None,system=NS(SystemFile=str(tmp_path/'work.zos'),SystemData=NS(Units=NS(LensUnits='Millimeters'))),
         _require_nsc=lambda:None,_require_work=lambda:None,_object=lambda i:None,_start_task=start,
         _collect_general_analysis=lambda task:dict(grids=[dict(values=values)],artifacts=[dict(kind='native_text',path='report.txt')]))
    task=na.run_nsc_surface_sag(b,request(keep_zrd=True,zrd_filename='surface.zrd'))
    assert settings.ZRDFilename=='surface.zrd'
    if code:
        with pytest.raises(ZemaxError)as caught:task['collector'](task)
        assert caught.value.code==code and caught.value.details['artifacts'][0]['path']=='report.txt'
    else:
        result=task['collector'](task)
        assert result['sampling_summary']['valid_samples']==1
        assert result['grids'][0]['array_order']=='values[y][x]'

