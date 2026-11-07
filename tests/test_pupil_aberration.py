import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.pupil_topics import configure


@pytest.mark.parametrize('extra',[dict(number_of_rays=2),dict(number_of_rays=10002),dict(number_of_rays=3.5),dict(plot_scale=-1),dict(plot_scale=float('nan')),dict(field=-1),dict(surface=1)])
def test_invalid_pupil_request(extra):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='pupil_aberration_fan',**extra))


def test_pupil_settings():
    q=RunAnalysis(request=dict(kind='pupil_aberration_fan',number_of_rays=21,check_apertures=False)).request
    writes={};values=configure(q,lambda n,v:writes.update({n:v}))
    assert values==writes
    assert values['NumberOfRays']==21 and values['CheckApertures']is False
    assert values['Tangential']=='Aberration_Y' and values['Sagittal']=='Aberration_X'
