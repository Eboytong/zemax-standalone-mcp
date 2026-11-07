import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis

@pytest.mark.parametrize('patch',[dict(points=1),dict(offsets=[]),dict(offsets=[-99]),dict(offsets=[0]*7),dict(minimum=90),dict(use_angles=False,minimum=-.9,maximum=.9,offsets=[.9]),dict(wavelength=0)])
def test_biocular_boundaries(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='biocular_dipvergence_convergence')|patch)

def test_reverse_and_constant_scan_ranges():
    for a,b in [(5,-5),(0,0)]:
        q=RunAnalysis(request=dict(kind='biocular_dipvergence_convergence',minimum=a,maximum=b)).request
        assert q.minimum==a and q.maximum==b


@pytest.mark.parametrize('mode',['restore','reject','native_error_and_reject'])
def test_biocular_config_restoration_and_original_failure(monkeypatch,mode):
    from types import SimpleNamespace as NS
    import zemax_mcp.biocular as module
    from zemax_mcp.errors import ZemaxError
    mce=NS(NumberOfConfigurations=2,CurrentConfiguration=1)
    def select(number):
        if mode!='restore':return False
        mce.CurrentConfiguration=number;return True
    mce.SetCurrentConfiguration=select
    def query(b,code,args):
        mce.CurrentConfiguration=2
        if mode=='native_error_and_reject':raise ZemaxError('NATIVE_ERROR','original-native-query')
        return 0.
    def validate(b,parent,config,rows,q,right):
        if False:yield
        return [dict(state='succeeded',position=[0.,0.,0.])for row in rows]
    monkeypatch.setattr(module,'native_query',query);monkeypatch.setattr(module,'validation_rays',validate)
    task=dict(rows=[])
    def composite(kind,settings,factory):
        for _ in factory(task):pass
        return task
    b=NS(_require_sequential=lambda:None,_require_work=lambda:None,_cancel_boundary=lambda task:None,
        system=NS(MCE=mce,SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1))),
        native=NS(enum=lambda owner,name:name,api=NS(Editors=NS(MFE=NS(MeritOperandType=object())))),
        _composite=composite,_evaluation_error=lambda exc:exc.as_dict(),requires_reconnect=False)
    q=RunAnalysis(request=dict(kind='biocular_dipvergence_convergence',points=2)).request
    if mode=='restore':
        module.run_biocular(b,q);assert mce.CurrentConfiguration==1
    else:
        with pytest.raises(ZemaxError)as exc:module.run_biocular(b,q)
        assert exc.value.code=='RESTORE_FAILED' and b.requires_reconnect
        if mode=='native_error_and_reject':assert exc.value.details['original_error']['message']=='original-native-query'


@pytest.mark.parametrize('close_ok',[True,False])
def test_validation_copy_failure_preserves_native_error(monkeypatch,close_ok):
    from types import SimpleNamespace as NS,MethodType
    from zemax_mcp.biocular import validation_rays
    from zemax_mcp.errors import ZemaxError
    mce=NS(CurrentConfiguration=1)
    def select(c):mce.CurrentConfiguration=c;return True
    mce.SetCurrentConfiguration=select
    counts=dict(tool=0,copy=0)
    def copyclose(save):counts['copy']+=1;return close_ok
    copy=NS(MCE=mce,SystemID=2,LDE=NS(StopSurface=1,NumberOfSurfaces=3),Close=copyclose)
    def flow(owner,task,req,target):
        def close():counts['tool']+=1;return True
        owner._release_owned(NS(Close=close))
        raise ZemaxError('TASK_FAILED','original-native-ray')
        yield
    def composite(kind,settings,factory):
        for _ in factory({}):pass
    def child(parent,method,q):
        if False:yield
        return method(q)
    def release(obj):
        if not obj.Close():raise ZemaxError('CLEANUP_FAILED','copy-close-false')
    b=NS(system=NS(CopySystem=lambda:copy),native=NS(),_child_job=child,_composite=composite,
        _extended_trace_flow=MethodType(flow,NS()),_cancel_boundary=lambda t:None,_release_owned=release,requires_reconnect=False)
    parent=dict(payload={});q=RunAnalysis(request=dict(kind='biocular_dipvergence_convergence')).request
    with pytest.raises(ZemaxError)as exc:
        for _ in validation_rays(b,parent,2,[dict(x=0.,y=0.)],q,False):pass
    assert exc.value.code=='TASK_FAILED' and str(exc.value)=='original-native-ray'
    assert counts==dict(tool=1,copy=1)
    assert parent['payload']['validation_copies'][0]['closed']==close_ok
    if not close_ok:assert b.requires_reconnect and exc.value.details['cleanup_error']=='copy-close-false'
