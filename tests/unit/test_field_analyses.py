import math
import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.field_analyses import pupil_grid, normalized_field, footprint_visible


@pytest.mark.parametrize('payload',[
    dict(kind='relative_illumination',wavelength=0),
    dict(kind='relative_illumination',ray_density=4),
    dict(kind='fft_mtf_vs_field',frequencies=[10,10]),
    dict(kind='fft_mtf_vs_field',frequencies=[float('nan')]),
    dict(kind='fft_mtf_vs_field',field_density=101),
    dict(kind='footprint'),dict(kind='footprint',surface=1,method='guess'),
])
def test_invalid_field_requests(payload):
    with pytest.raises(ValidationError):RunAnalysis(request=payload)


def test_circular_aperture_area_reference():
    points=pupil_grid(40)
    fraction=sum(x*x+y*y<=.25 for x,y in points)/len(points)
    assert fraction==pytest.approx(.25,abs=.01)
    assert all(x*x+y*y<=1+1e-12 for x,y in points)


def test_field_normalization():
    fields=[dict(x=3,y=4),dict(x=-2,y=1)]
    assert normalized_field(fields,fields[0],'Radial')==(.6,.8)
    assert normalized_field(fields,fields[1],'Rectangular')==(-2/3,.25)
    assert normalized_field([dict(x=0,y=0)],dict(x=0,y=0),'Radial')==(0,0)


def test_footprint_previous_and_subsequent_clipping():
    def ray(code=0,error=0):return dict(position=[1,2,0],vignette_code=code,error_code=error)
    assert not footprint_visible(ray(1),ray(1),2,False)
    assert footprint_visible(ray(2),ray(2),2,False)
    assert footprint_visible(ray(),ray(3),2,False)
    assert not footprint_visible(ray(),ray(3),2,True)
    assert not footprint_visible(ray(),ray(error=3),2,True)
    assert footprint_visible(ray(),ray(),2,True)


def test_cancellation_restores_vignetting_factors():
    from types import SimpleNamespace
    from zemax_mcp.analysis_models import Vignetting
    from zemax_mcp.field_analyses import sampled_analysis
    from zemax_mcp.evaluation import Cancelled
    f=SimpleNamespace(VDX=.1,VDY=.2,VCX=.3,VCY=.4,VAN=5.)
    class Backend:
        requires_reconnect=False
        system=SimpleNamespace(SystemData=SimpleNamespace(Fields=SimpleNamespace(GetField=lambda i:f)),LDE=SimpleNamespace(NumberOfSurfaces=3))
        def _require_sequential(self):pass
        def get_system_settings(self,_):return dict(fields=[dict(x=0,y=1,vcx=.3,vcy=.4)],wavelengths=[dict(number=1,primary=True)],field_type='Angle',field_normalization='Radial',lens_units='Millimeters')
        def _composite(self,kind,settings,flow):
            self.task=dict(rows=[],summary={},cancel_requested=False)
            return flow(self.task)
        def _cancel_boundary(self,task):raise Cancelled()
    b=Backend();iterator=sampled_analysis(b,Vignetting(kind='vignetting'))
    with pytest.raises(Cancelled):next(iterator)
    assert (f.VDX,f.VDY,f.VCX,f.VCY,f.VAN)==(.1,.2,.3,.4,5.)
    assert b.task['restoration']['restored']
