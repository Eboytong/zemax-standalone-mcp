import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.biocular_fov import transition_edges,boundary_segments,stitch_segments

@pytest.mark.parametrize('patch',[dict(configurations=[0]),dict(x_points=1),dict(left=10,right=-10),dict(use_angles=False,left=-.9,right=.9,bottom=-.9,top=.9),dict(configurations=[1]*4,x_points=257,y_points=257)])
def test_invalid_fov_request(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='biocular_field_of_view')|patch)

@pytest.mark.parametrize('mask,expected',[
    ([[True]*5 for _ in range(5)],1),
    ([[True]*5,[True,False,False,False,True],[True,False,False,False,True],[True,False,False,False,True],[True]*5],2),
    ([[False]*5,[False,True,False,True,False],[False]*5],2)])
def test_sampled_closed_loops_preserve_holes_and_disconnected_islands(mask,expected):
    xs=list(range(len(mask[0])));ys=list(range(len(mask)))
    points={key:((a[0]+b[0])/2,(a[1]+b[1])/2)for key in transition_edges(mask)for a,b in [key]}
    curves=stitch_segments(boundary_segments(mask,xs,ys,points,{}))
    assert len(curves)==expected and all(c['closed']for c in curves)

def test_ambiguous_cell_uses_measured_center():
    mask=[[True,False],[False,True]]
    points={key:((a[0]+b[0])/2,(a[1]+b[1])/2)for key in transition_edges(mask)for a,b in [key]}
    for center,expected in [(True,1),(False,2)]:
        curves=stitch_segments(boundary_segments(mask,[0,1],[0,1],points,{(0,0):center}))
        assert len(curves)==expected and all(c['closed']for c in curves)


def test_fov_large_grid_is_chunked_to_native_request_limit(monkeypatch):
    from types import SimpleNamespace as NS
    import zemax_mcp.biocular_fov as module
    calls=[];task=dict(rows=[])
    def trace(b,parent,configuration,rows,q,right,configure=None):
        assert len(rows)<=10000;calls.append(len(rows))
        if False:yield
        return [dict(state='succeeded')for _ in rows]
    monkeypatch.setattr(module,'validation_rays',trace)
    def composite(kind,settings,factory):
        for _ in factory(task):pass
        return task
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,_cancel_boundary=lambda t:None,
        system=NS(MCE=NS(NumberOfConfigurations=1,CurrentConfiguration=1),SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1))),_composite=composite)
    q=RunAnalysis(request=dict(kind='biocular_field_of_view',x_points=101,y_points=101)).request
    module.run_fov(b,q)
    assert calls==[10000,201] and task['summary']['launched']==10201
    assert len(task['payload']['contours'])==1 and task['payload']['contours'][0]['closed']
