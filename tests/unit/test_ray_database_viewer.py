import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.ray_database import RayDatabaseViewer
from zemax_mcp.errors import ZemaxError

@pytest.mark.parametrize('extra',[{'path':'relative.zrd'},{'start_ray':-1},{'start_segment':-1},{'max_segments':0},{'max_segments':100001},{'filter':2}])
def test_viewer_request_contract(extra):
    with pytest.raises(ValidationError):RunAnalysis(request={'kind':'ray_database_viewer','path':'C:/owned.zrd',**extra})

def test_viewer_preserves_zrd_read_contract():
    q=RayDatabaseViewer(kind='ray_database_viewer',path='C:/owned.zrd',filter='H3',start_ray=2,start_segment=4,max_segments=99)
    from zemax_mcp.nsc_models import ZrdRead
    read=ZrdRead(**q.model_dump(exclude={'kind'}))
    assert read.model_dump()=={'path':'C:/owned.zrd','filter':'H3','start_ray':2,'start_segment':4,'max_segments':99}
