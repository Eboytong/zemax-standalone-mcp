from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.errors import ZemaxError
from zemax_mcp import polarization as p


@pytest.mark.parametrize('patch',[dict(surface=0),dict(field=0),dict(wavelength=0),dict(sampling=4),dict(sampling=103),dict(sampling=True),dict(jx=0,jy=0),dict(jx=-1),dict(y_phase=float('nan')),dict(use_polarization=True)])
def test_pupil_request_rejects_invalid_parameters(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='polarization_pupil_map',**dict(dict(surface=1),**patch)))


def text():
    return '波长 : 0.5500\n视场Pos : 0.0000 (度)\nX-场 : 1.0000\nY-场 : 0.0000\nX-相位 : 0.00\nY-相位 : 0.00\n结构 : 1\n表面 : 1\n透射 : 95%\nPx Py Ex Ey 强度 相位 (Deg) Orientation\n-1 0 .9 0 .81 0 0\n0 0 1 0 1 0 0\n1 0 .9 0 .81 0 0\n'


def settings():
    q=RunAnalysis(request=dict(kind='polarization_pupil_map',surface=1,sampling=3)).request
    return dict(requested=q.model_dump(),configuration=1,wavelength_um=.55,field_position=dict(x=0,y=0))


def test_pupil_text_and_settings_readback():
    actual,rows=p.parse_pupil_text(text())
    result=p.verify_settings(actual,rows,settings())
    assert result['sampling']==3 and result['transmission_percent']==95
    assert rows[1]['intensity']==1
    actual['surface']=2
    with pytest.raises(ZemaxError)as caught:p.verify_settings(actual,rows,settings())
    assert caught.value.code=='SETTING_REJECTED'


@pytest.mark.parametrize('tail,code',[('', 'NO_RESULT_DATA'),('0 0 1 0 nan 0 0','INVALID_RESULT_DATA'),('0 0 1','INVALID_RESULT_DATA'),('native ray failed','INVALID_RESULT_DATA')])
def test_empty_or_malformed_native_table(tail,code):
    with pytest.raises(ZemaxError)as caught:p.parse_pupil_text('Px Py Ex Ey Intensity Phase Orientation\n'+tail)
    assert caught.value.code==code


def test_sampling_rejection_and_duplicate_points():
    actual,rows=p.parse_pupil_text(text())
    with pytest.raises(ZemaxError)as caught:p.verify_settings(actual,rows,dict(settings(),requested=dict(settings()['requested'],sampling=5)))
    assert caught.value.code=='SETTING_UNCONFIRMED'
    with pytest.raises(ZemaxError)as caught:p.parse_pupil_text(text()+'0 0 1 0 1 0 0\n')
    assert caught.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('failure',['save','modify','load','exception'])
def test_cfg_failure_closes_native_resource(tmp_path,monkeypatch,failure):
    events=[]
    def modify(*args):
        if failure=='exception':raise RuntimeError('native setup failure')
        return failure!='modify'
    native=N(GetType=lambda:N(FullName='AS_Default'),SaveTo=lambda _:failure!='save',ModifySettings=modify,LoadFrom=lambda _:failure!='load')
    backend=N(_require_sequential=lambda:None,_row=lambda _:None,directory=tmp_path,requires_reconnect=False,
        system=N(MCE=N(CurrentConfiguration=1),SystemData=N(Fields=N(NumberOfFields=1,GetFieldType=lambda:'Angle',GetField=lambda _:N(X=0,Y=0)),Wavelengths=N(NumberOfWavelengths=1,GetWavelength=lambda _:N(Wavelength=.55)))),
        _close_task_native=lambda _:events.append('close') or True)
    monkeypatch.setattr(p,'new_analysis',lambda *_:N(GetSettings=lambda:native))
    monkeypatch.setattr(p,'unwrap',lambda x:x)
    q=RunAnalysis(request=dict(kind='polarization_pupil_map',surface=1)).request
    with pytest.raises((ZemaxError,RuntimeError)):p.run_pupil_map(backend,q)
    assert events==['close']


@pytest.mark.parametrize('native,expected',[('0.0000, -5.0000',dict(x=0,y=-5)),('3.0000, 4.0000',dict(x=3,y=4)),('-5.0000',dict(x=0,y=-5))])
def test_native_field_coordinates(native,expected):
    actual,rows=p.parse_pupil_text(text().replace('0.0000 (度)',native+' (度)',1))
    result=p.verify_settings(actual,rows,dict(settings(),field_position=expected))
    assert result['field_position']==expected


def test_phase_readback_accepts_equivalent_period():
    actual,rows=p.parse_pupil_text(text().replace('Y-相位 : 0.00','Y-相位 : 90.00'))
    result=p.verify_settings(actual,rows,dict(settings(),requested=dict(settings()['requested'],y_phase=450)))
    assert result['y_phase']==90


def test_duplicate_field_coordinates_rejected_before_native_creation(monkeypatch):
    monkeypatch.setattr(p,'new_analysis',lambda *_:pytest.fail('ambiguous field must be rejected before resource creation'))
    backend=N(_require_sequential=lambda:None,_row=lambda _:None,
        system=N(SystemData=N(Fields=N(NumberOfFields=2,GetField=lambda _:N(X=0,Y=0)),
            Wavelengths=N(NumberOfWavelengths=1))))
    q=RunAnalysis(request=dict(kind='polarization_pupil_map',surface=1)).request
    with pytest.raises(ZemaxError)as caught:p.run_pupil_map(backend,q)
    assert caught.value.code=='SETTING_UNCONFIRMED'
    assert caught.value.details['matching_fields']==[1,2]
