import pytest
from pydantic import ValidationError
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.analyses import configure_seidel_diagram


@pytest.mark.parametrize('patch', [{'plot_scale': -1}, {'plot_scale': float('nan')},
                                   {'plot_scale': float('inf')}, {'wavelength': 0}])
def test_seidel_diagram_invalid_request(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request={'kind': 'seidel_diagram', **patch})


def test_seidel_diagram_configuration_and_worker_roundtrip():
    req = RunAnalysis(request={'kind': 'seidel_diagram', 'ignore_chromatic': True,
                               'ignore_distortion': True, 'plot_scale': .25})
    assert RunAnalysis.model_validate(req.model_dump()) == req
    settings = {}
    configure_seidel_diagram(req.request, lambda k, v: settings.__setitem__(k, v))
    assert settings == dict(IgnoreChromatic=True, IgnoreDistortion=True,
                            SuppressFrame=False, PlotScale=.25)


@pytest.mark.parametrize('patch',[dict(first_surface=0),dict(first_surface=3,last_surface=2),dict(last_surface=0),dict(method='unknown')])
def test_seidel_range_contract(patch):
    with pytest.raises(ValidationError):RunAnalysis(request=dict(kind='seidel_diagram',**patch))


@pytest.mark.parametrize('chromatic,distortion',[(False,False),(True,False),(False,True),(True,True)])
def test_unconverted_surface_identity_subset_and_sum(chromatic,distortion):
    from zemax_mcp.seidel_diagram import diagram_data,COEFFICIENTS
    q=RunAnalysis(request=dict(kind='seidel_diagram',first_surface=2,last_surface=3,ignore_chromatic=chromatic,
        ignore_distortion=distortion,plot_scale=.5,suppress_frame=True)).request
    rows=[dict(row_label=label,section=0,coefficients={k:float(i) for k in COEFFICIENTS},unit='Millimeters')
        for i,label in enumerate(['1','光阑','3','像面','累计'],1)]
    result=diagram_data(dict(rows=rows),q,2,4,3)
    assert [r['surface'] for r in result['rows']]==[2,3,None]
    expected=[k for k in COEFFICIENTS if not(chromatic and k in {'CLA','CTR'}) and not(distortion and k=='DIST')]
    assert result['coefficient_order']==expected
    assert list(result['rows'][-1]['coefficients'].values())==[5.]*len(expected)
    assert result['series'][0]['y_limits']==[-.5,.5] and result['series'][0]['suppress_frame']
    assert len(result['native_totals'])==1


@pytest.mark.parametrize('labels,code',[([], 'NO_RESULT_DATA'),(['unknown'],'UNRECOGNIZED_RESULT_FORMAT'),
    (['1','1'],'INVALID_RESULT_DATA'),(['1'],'NO_RESULT_DATA')])
def test_invalid_seidel_coefficient_outlets(labels,code):
    from zemax_mcp.seidel_diagram import diagram_data,COEFFICIENTS
    from zemax_mcp.errors import ZemaxError
    q=RunAnalysis(request=dict(kind='seidel_diagram')).request
    rows=[dict(row_label=label,section=0,coefficients={k:0. for k in COEFFICIENTS},unit='Millimeters') for label in labels]
    with pytest.raises(ZemaxError) as error:diagram_data(dict(rows=rows),q,2,3,2)
    assert error.value.code==code


def test_native_chart_rejects_unavailable_selector_before_opening_tool():
    from types import SimpleNamespace as NS
    from zemax_mcp.seidel_diagram import run_seidel_diagram
    from zemax_mcp.errors import ZemaxError
    q=RunAnalysis(request=dict(kind='seidel_diagram',method='native',wavelength=2)).request
    backend=NS(_require_sequential=lambda:None)
    with pytest.raises(ZemaxError) as error:run_seidel_diagram(backend,q)
    assert error.value.code=='UNSUPPORTED_SETTING'


def test_coefficient_child_failure_is_preserved():
    from types import SimpleNamespace as NS
    from zemax_mcp.seidel_diagram import run_seidel_diagram
    from zemax_mcp.errors import ZemaxError
    def child(*args):
        raise ZemaxError('CHILD_TASK_FAILED','controlled native coefficient error',native='original')
        yield
    backend=NS(_require_sequential=lambda:None,
        system=NS(LDE=NS(NumberOfSurfaces=4,StopSurface=1),SystemData=NS(Wavelengths=NS(NumberOfWavelengths=1))),
        _composite=lambda kind,settings,flow:flow(dict(rows=[])),_run_general_analysis=lambda q:None,_child_job=child)
    with pytest.raises(ZemaxError) as error:list(run_seidel_diagram(backend,RunAnalysis(request=dict(kind='seidel_diagram')).request))
    assert error.value.code=='CHILD_TASK_FAILED' and error.value.details['native']=='original'


def test_default_native_chart_route_uses_only_explicit_selector_fields():
    q=RunAnalysis(request=dict(kind='seidel_diagram',method='native'))
    restored=RunAnalysis.model_validate(dict(request=q.request.model_dump(exclude_unset=True))).request
    assert not(restored.model_fields_set & {'wavelength','first_surface','last_surface'})
