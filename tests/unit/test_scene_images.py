from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.scene_images import ExtendedDiffractionImage, PartiallyCoherentImage, image_grid, verify_selection
from zemax_mcp.errors import ZemaxError


class Array:
    Rank=2
    def __init__(self,values):self.values=values
    def GetLength(self,i):return len(self.values) if i==0 else len(self.values[0])
    def __getitem__(self,indices):return self.values[indices[0]][indices[1]]


def test_scene_requests_are_registered_and_reject_unconfirmed_selectors():
    assert RunAnalysis(request=dict(kind='extended_diffraction_image',source_width=.1,display_width=.2)).request.field==1
    assert RunAnalysis(request=dict(kind='partially_coherent_image')).request.wavelength==1
    with pytest.raises(ValidationError):PartiallyCoherentImage(kind='partially_coherent_image',input_file='test.IMA')
    with pytest.raises(ValidationError):ExtendedDiffractionImage(kind='extended_diffraction_image',source_width=float('inf'),display_width=.2)
    with pytest.raises(ValidationError):PartiallyCoherentImage(kind='partially_coherent_image',wavelength=0)


def test_report_readback_checks_selected_identity_and_sizes():
    q=ExtendedDiffractionImage(kind='extended_diffraction_image',source_width=.1,display_width=.2)
    system=dict(fields=[dict(x=0,y=14)],wavelengths=[dict(wavelength_um=.48)])
    report=dict(field_deg=14,wavelength_um=.48,source_width=.1,display_width=.2)
    assert verify_selection(report,q,system)['source_width']==.1
    report['display_width']=.1
    with pytest.raises(ZemaxError) as caught:verify_selection(report,q,system)
    assert caught.value.code=='SETTING_REJECTED'
    assert caught.value.details['setting']=='display_width'


def test_non_square_grid_preserves_native_array_and_checks_reversed_text():
    values=[[.1,.2,.3],[.4,.5,1.]]
    native=SimpleNamespace(Nx=3,Ny=2,Values=Array(values),MinX=.4,MinY=.4,Dx=.1,Dy=.2,XLabel='',YLabel='')
    parsed=dict(kind='partially_coherent_image',grid=values[::-1])
    grid=image_grid(native,parsed)
    assert grid['values']==values and grid['array_order'].startswith('values[y][x]')
    assert grid['native_axes']['min_x']==.4 and grid['min_x']==0
    assert grid['physical_axes_verified'] is False
    parsed['grid']=values
    with pytest.raises(ZemaxError):image_grid(native,parsed)


def test_grid_rejects_size_and_nonfinite_native_data():
    native=SimpleNamespace(Nx=3,Ny=2,Values=Array([[1.,2.,3.]]))
    with pytest.raises(ZemaxError):image_grid(native,dict(grid=[[1,2,3],[4,5,6]]))
    native.Values=Array([[1.,2.,3.],[4.,5.,float('nan')]])
    with pytest.raises(ZemaxError):image_grid(native,dict(grid=[[1,2,3],[4,5,6]]))


@pytest.mark.parametrize('close_ok',[True,False])
def test_cfg_rejection_preserves_error_and_closes_analysis(tmp_path,monkeypatch,close_ok):
    from zemax_mcp.scene_images import run_scene_image
    settings=SimpleNamespace(GetType=lambda:SimpleNamespace(FullName='AS_Default'),
        SaveTo=lambda path:True,ModifySettings=lambda *args:False)
    tool=SimpleNamespace(GetSettings=lambda:settings)
    backend=SimpleNamespace(directory=tmp_path,requires_reconnect=False,
        _require_sequential=lambda **kwargs:None,
        get_system_settings=lambda _:dict(fields=[dict(x=0,y=0)],
            wavelengths=[dict(wavelength_um=.55)],field_type='Angle',lens_units='Millimeters'))
    closed=[]
    backend._close_task_native=lambda owner:closed.append(owner) or close_ok
    monkeypatch.setattr('zemax_mcp.imaging.new_analysis',lambda *args:tool)
    with pytest.raises(ZemaxError) as caught:
        run_scene_image(backend,PartiallyCoherentImage(kind='partially_coherent_image'))
    assert caught.value.code=='SETTING_REJECTED'
    assert caught.value.details['setting']=='PCI_FIELD'
    assert len(closed)==1 and closed[0]['native'] is tool
    assert backend.requires_reconnect is (not close_ok)


def test_duplicate_field_readback_is_rejected_before_analysis_creation(monkeypatch):
    from zemax_mcp.scene_images import run_scene_image
    backend=SimpleNamespace(_require_sequential=lambda **kwargs:None,
        get_system_settings=lambda _:dict(fields=[dict(x=0,y=14),dict(x=0,y=14)],
          wavelengths=[dict(wavelength_um=.48)],field_type='Angle',lens_units='Millimeters'))
    def unexpected(*args):raise AssertionError('must reject before creating analysis')
    monkeypatch.setattr('zemax_mcp.imaging.new_analysis',unexpected)
    with pytest.raises(ZemaxError) as caught:
        run_scene_image(backend,PartiallyCoherentImage(kind='partially_coherent_image'))
    assert caught.value.code=='SETTING_UNCONFIRMED'
